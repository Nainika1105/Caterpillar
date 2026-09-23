"""Member 2 imports this module only. Load trusted local artifacts at startup."""

import os
from datetime import date
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from ml.features.build import SHIFT_FEATURES, operator_analytics, shift_features
from shared.constants import (
    EV_CERTIFICATION,
    AnomalyType,
    EnergyAction,
    MachineClass,
    Powertrain,
)
from shared.schemas.prediction import (
    AnomalyPrediction,
    AssignmentCandidate,
    ChargeAdvisory,
    ChargeInput,
    ChargePoint,
    EnergyForecastInput,
    EnergyForecastPrediction,
    EnergyInput,
    EnergyPrediction,
    FuelAnomalyPrediction,
    TaskDurationInput,
    TaskDurationPrediction,
)


class ModelService:
    def __init__(self, model_dir: Path | None = None) -> None:
        root = model_dir or Path(os.getenv("CAT_MODEL_DIR", "ml/models/v1"))
        # joblib is pickle-based: never load uploaded/untrusted model artifacts.
        self.duration = joblib.load(root / "duration.joblib")
        self.anomaly = joblib.load(root / "anomaly.joblib")

    def predict_task_duration(
        self, request: TaskDurationInput
    ) -> TaskDurationPrediction:
        frame = pd.DataFrame([request.model_dump(mode="json")])
        value = float(
            self.duration["pipeline"].predict(frame[self.duration["features"]])[0]
        )
        return TaskDurationPrediction(
            estimated_duration_min=max(1, value),
            model_version=self.duration["model_version"],
        )

    def detect_anomalies(
        self, normalized_telemetry: pd.DataFrame
    ) -> list[AnomalyPrediction]:
        """Retrospective completed-shift scoring, not an edge alert replacement."""
        required = {
            "machine_id",
            "operator_id",
            "machine_class",
            "recorded_at",
            "state",
            "seatbelt_status",
            "ground_speed_kmh",
            "is_power_on",
            "is_operator_present",
            "proximity_min_m",
            "coolant_temp_c",
            "harsh_events",
            "fuel_rate_lph",
            "power_kw",
            "fuel_used_l",
            "energy_used_kwh",
            "load_cycles",
        }
        missing = sorted(required - set(normalized_telemetry.columns))
        if missing:
            raise ValueError(
                f"Missing required anomaly telemetry columns: {', '.join(missing)}"
            )
        shifts = shift_features(normalized_telemetry)
        if shifts.empty:
            return []
        scores = self.score_shift_features(shifts)
        return [
            AnomalyPrediction(
                machine_id=row.machine_id,
                operator_id=row.operator_id,
                date=row.date,
                anomaly_score=float(score),
                is_anomaly=bool(score >= self.anomaly["threshold"]),
                model_version=self.anomaly["model_version"],
            )
            for row, score in zip(shifts.itertuples(), scores)
        ]

    def score_shift_features(self, shifts: pd.DataFrame) -> np.ndarray:
        """Validate engineered shift inputs before applying the saved model."""
        required = set(self.anomaly["features"])
        missing = sorted(required - set(shifts.columns))
        if missing:
            raise ValueError(f"Missing required anomaly features: {', '.join(missing)}")
        numeric = shifts[SHIFT_FEATURES].apply(pd.to_numeric, errors="coerce")
        invalid_types = numeric.isna() & shifts[SHIFT_FEATURES].notna()
        if invalid_types.any().any():
            raise ValueError(
                f"Non-numeric anomaly features: {', '.join(invalid_types.columns[invalid_types.any()])}"
            )
        if np.isinf(numeric.to_numpy(dtype=float)).any():
            raise ValueError("Infinite anomaly feature values are invalid")
        nonnegative = [name for name in SHIFT_FEATURES if name != "coolant_temp_c"]
        if (
            numeric[nonnegative].lt(0).any().any()
            or numeric[["idle_pct", "unbelted_moving_pct", "unattended_pct"]]
            .gt(100)
            .any()
            .any()
        ):
            raise ValueError("Anomaly features contain invalid physical values")
        scaler = (
            self.anomaly["pipeline"]
            .named_steps["features"]
            .named_transformers_["numeric"]
            .named_steps["scale"]
        )
        standardized = (numeric.to_numpy(dtype=float) - scaler.mean_) / scaler.scale_
        extreme = np.isfinite(standardized) & (np.abs(standardized) > 50)
        if extreme.any():
            names = sorted(
                {SHIFT_FEATURES[index] for index in np.flatnonzero(extreme.any(axis=0))}
            )
            raise ValueError(
                f"Anomaly features outside the supported training range: {', '.join(names)}"
            )
        return -self.anomaly["pipeline"].score_samples(shifts[self.anomaly["features"]])


def _energy_action(powertrain: Powertrain, sufficient: bool | None) -> EnergyAction:
    if sufficient is None:
        return EnergyAction.UNKNOWN
    if sufficient:
        return EnergyAction.NONE
    return (
        EnergyAction.REFUEL
        if powertrain == Powertrain.DIESEL
        else EnergyAction.RECHARGE
    )


def predict_energy_runout(request: EnergyInput) -> EnergyPrediction:
    if request.powertrain == Powertrain.DIESEL:
        remaining, rate = request.fuel_remaining_l, request.fuel_rate_lph
    else:
        remaining, rate = request.energy_remaining_kwh, request.power_kw
    if remaining is None or rate is None:
        raise ValueError(
            "Remaining energy and consumption rate are required for this powertrain"
        )
    if remaining == 0:
        minutes = 0.0
    elif rate == 0:
        return EnergyPrediction(
            estimated_remaining_min=None,
            has_sufficient_energy=None,
            recommended_action=EnergyAction.UNKNOWN,
        )
    else:
        minutes = remaining / rate * 60
    sufficient = minutes >= request.remaining_task_min
    return EnergyPrediction(
        estimated_remaining_min=minutes,
        has_sufficient_energy=sufficient,
        recommended_action=_energy_action(request.powertrain, sufficient),
    )


def rank_assignments(
    candidates: list[AssignmentCandidate],
    *,
    site_id: str,
    machine_class: MachineClass,
    on_date: date,
) -> list[AssignmentCandidate]:
    """Return alternatives for ONE task; backend reserves the confirmed pair."""
    required = {machine_class.value.removeprefix("electric_")}
    if machine_class in {
        MachineClass.ELECTRIC_EXCAVATOR,
        MachineClass.ELECTRIC_MINI_EXCAVATOR,
    }:
        required.add(EV_CERTIFICATION)
    eligible = [
        candidate
        for candidate in candidates
        if (
            candidate.site_id == site_id
            and candidate.machine_class == machine_class
            and candidate.is_machine_available
            and candidate.is_operator_available
            and required <= candidate.certifications
            and all(
                candidate.certification_valid_until.get(cert, date.min) >= on_date
                for cert in required
            )
            and candidate.estimated_remaining_min >= candidate.estimated_duration_min
        )
    ]
    return sorted(
        eligible,
        key=lambda candidate: (
            candidate.estimated_duration_min,
            candidate.machine_id,
            candidate.operator_id,
        ),
    )


def suggest_charger(
    request: ChargeInput, points: list[ChargePoint]
) -> ChargeAdvisory | None:
    """Idealized charge timing; excludes taper, travel and queue time."""
    if request.energy_remaining_kwh > request.battery_capacity_kwh:
        raise ValueError("Remaining energy exceeds battery capacity")
    required = max(
        0,
        request.battery_capacity_kwh * request.target_soc_pct / 100
        - request.energy_remaining_kwh,
    )
    choices = []
    for point in points:
        if (
            point.site_id != request.site_id
            or not point.is_available
            or not point.is_compatible
        ):
            continue
        effective_kw = (
            min(point.power_kw, request.max_charge_kw)
            * request.charging_efficiency_pct
            / 100
        )
        choices.append(
            ChargeAdvisory(
                energy_point_id=point.energy_point_id,
                estimated_charge_min=required / effective_kw * 60,
                energy_required_kwh=required,
            )
        )
    return (
        min(
            choices,
            key=lambda choice: (choice.estimated_charge_min, choice.energy_point_id),
        )
        if choices
        else None
    )


def summarize_operators(
    normalized_telemetry: pd.DataFrame,
    *,
    tasks: pd.DataFrame | None = None,
    operator_id: str | None = None,
    start_at: pd.Timestamp | None = None,
    end_at: pd.Timestamp | None = None,
    shift_date: date | None = None,
) -> list[dict]:
    """Return operator/class metrics over a half-open UTC interval or shift date.

    Seatbelt violations count unfastened moving minutes, not distinct events.
    Completed-task counts are unavailable (None) unless tasks are supplied.
    """
    if normalized_telemetry.empty:
        return []
    start = pd.Timestamp(start_at) if start_at is not None else None
    end = pd.Timestamp(end_at) if end_at is not None else None
    for bound in (start, end):
        if bound is not None and (bound.tzinfo is None or pd.isna(bound)):
            raise ValueError("Analytics time bounds must be timezone-aware")
    if start is not None and end is not None and start >= end:
        raise ValueError("Analytics start_at must precede end_at")
    rows = normalized_telemetry
    if operator_id is not None:
        rows = rows.loc[rows.operator_id == operator_id]
    if start is not None:
        rows = rows.loc[rows.recorded_at >= start]
    if end is not None:
        rows = rows.loc[rows.recorded_at < end]
    if shift_date is not None:
        rows = rows.loc[rows.recorded_at.dt.date == shift_date]
    if rows.empty:
        return []
    scoped_tasks = tasks
    if tasks is not None:
        scoped_tasks = tasks
        if operator_id is not None:
            scoped_tasks = scoped_tasks.loc[scoped_tasks.operator_id == operator_id]
        if start is not None or end is not None:
            if "actual_end_at" not in scoped_tasks.columns:
                raise ValueError(
                    "Task analytics require actual_end_at for time filtering"
                )
            if start is not None:
                scoped_tasks = scoped_tasks.loc[scoped_tasks.actual_end_at >= start]
            if end is not None:
                scoped_tasks = scoped_tasks.loc[scoped_tasks.actual_end_at < end]
        if shift_date is not None:
            if "date" not in scoped_tasks.columns:
                raise ValueError("Task analytics require date for shift filtering")
            scoped_tasks = scoped_tasks.loc[scoped_tasks.date == shift_date.isoformat()]
    return operator_analytics(rows, scoped_tasks).to_dict(orient="records")


class AdvancedModelService:
    """Version 2 fuel anomalies and learned energy forecasting; duration stays v1."""

    def __init__(self, model_dir: Path | None = None) -> None:
        root = model_dir or Path(os.getenv("CAT_MODEL_DIR", "ml/models/v2"))
        self.anomaly = joblib.load(root / "anomaly.joblib")
        self.energy = joblib.load(root / "energy.joblib")
        if self.anomaly.get("kind") != "fuel_residual_v2":
            raise ValueError("AdvancedModelService requires v2 artifacts")
        if self.anomaly["model_version"] != self.energy["model_version"]:
            raise ValueError("Anomaly and energy artifact versions do not match")

    def detect_fuel_anomalies(
        self, normalized_telemetry: pd.DataFrame
    ) -> list[FuelAnomalyPrediction]:
        from ml.anomaly import predict_fuel

        if normalized_telemetry.empty:
            return []
        rows = predict_fuel(self.anomaly, normalized_telemetry)
        result = []
        for row in rows.itertuples():
            types = []
            if row.is_abnormal_fuel_burn:
                types.append(AnomalyType.ABNORMAL_FUEL_BURN)
            if row.is_fuel_loss:
                types.append(AnomalyType.FUEL_LOSS)
            result.append(
                FuelAnomalyPrediction(
                    machine_id=row.machine_id,
                    operator_id=row.operator_id,
                    date=row.date,
                    anomaly_types=types,
                    fuel_burn_score=row.burn_score,
                    fuel_burn_ratio=(
                        float(row.fuel_burn_ratio)
                        if np.isfinite(row.fuel_burn_ratio)
                        else None
                    ),
                    parked_fuel_drop_pct=row.parked_fuel_drop_pct,
                    has_sufficient_fuel_observations=row.powered_sample_count
                    >= self.anomaly["min_powered_sample_count"],
                    model_version=self.anomaly["model_version"],
                )
            )
        return result

    def predict_energy_runout(
        self, request: EnergyForecastInput, normalized_history: pd.DataFrame
    ) -> EnergyForecastPrediction:
        from ml.energy import ENERGY_FEATURES, history_features

        diesel = request.powertrain == Powertrain.DIESEL
        capacity = request.fuel_tank_l if diesel else request.battery_kwh
        remaining = request.fuel_remaining_l if diesel else request.energy_remaining_kwh
        if capacity is None or remaining is None or remaining > capacity:
            raise ValueError(
                "Valid capacity and remaining energy are required for the powertrain"
            )
        machine = pd.Series(request.model_dump(mode="json"))
        features = pd.DataFrame([history_features(normalized_history, machine)])
        forecast = max(
            0.0,
            float(
                self.energy["models"][request.powertrain.value]["pipeline"].predict(
                    features[ENERGY_FEATURES]
                )[0]
            ),
        )
        horizon = self.energy["forecast_min"]
        minutes = (
            0.0
            if remaining == 0
            else (
                remaining / capacity * 100 / forecast * horizon
                if forecast > 0
                else None
            )
        )
        return EnergyForecastPrediction(
            estimated_remaining_min=minutes,
            has_sufficient_energy=(
                minutes >= request.remaining_task_min if minutes is not None else None
            ),
            recommended_action=_energy_action(
                request.powertrain,
                minutes >= request.remaining_task_min if minutes is not None else None,
            ),
            forecast_used_pct=forecast,
            forecast_horizon_min=horizon,
            is_extrapolation=minutes > horizon if minutes is not None else False,
            model_version=self.energy["model_version"],
        )
