"""Causal one-hour energy forecast with censored drawdown replay evaluation."""

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error
from sklearn.pipeline import Pipeline
from xgboost import XGBRegressor

from ml.training.train import preprocessing
from shared.constants import (
    ENERGY_FORECAST_MIN,
    ENERGY_HISTORY_MIN,
    ENERGY_REPLAY_BUDGET_PCT,
    ENERGY_REPLAY_MAX_MIN,
    SEED,
    MachineState,
    Powertrain,
)

ENERGY_NUMERIC = [
    "recent_used_pct",
    "recent_15min_used_pct",
    "working_pct",
    "idle_pct",
    "utc_minute",
]
ENERGY_CATEGORY = ["machine_class", "machine_state"]
ENERGY_FEATURES = ENERGY_NUMERIC + ENERGY_CATEGORY
HISTORY_MIN = ENERGY_HISTORY_MIN
FORECAST_MIN = ENERGY_FORECAST_MIN
REPLAY_MAX_MIN = ENERGY_REPLAY_MAX_MIN
REPLAY_BUDGET_PCT = ENERGY_REPLAY_BUDGET_PCT


def history_features(history: pd.DataFrame, machine: pd.Series) -> dict:
    h = history.sort_values("recorded_at").tail(HISTORY_MIN)
    if h.recorded_at.dt.tz is None:
        raise ValueError("Energy history timestamps must include a timezone")
    h = h.copy()
    h["recorded_at"] = h.recorded_at.dt.tz_convert("UTC")
    if (
        len(h) != HISTORY_MIN
        or not h.recorded_at.diff().iloc[1:].dt.total_seconds().eq(60).all()
    ):
        raise ValueError("Exactly 60 consecutive one-minute samples are required")
    if h.machine_id.nunique() != 1 or h.machine_id.iloc[0] != machine.machine_id:
        raise ValueError("History must belong to the requested machine")
    diesel = machine.powertrain == Powertrain.DIESEL
    capacity = float(machine.fuel_tank_l if diesel else machine.battery_kwh)
    if not np.isfinite(capacity) or capacity <= 0:
        raise ValueError("A positive fuel tank or battery capacity is required")
    usage = h.fuel_used_l if diesel else h.energy_used_kwh
    if usage.isna().any() or not np.isfinite(usage).all():
        raise ValueError("Missing or non-finite energy measurements")
    usage = usage.clip(lower=0) / capacity * 100
    at = h.recorded_at.iloc[-1]
    return {
        "recent_used_pct": float(usage.sum()),
        "recent_15min_used_pct": float(usage.tail(15).sum()),
        "working_pct": float((h.state == MachineState.WORKING).mean() * 100),
        "idle_pct": float((h.state == MachineState.IDLE).mean() * 100),
        "utc_minute": float(at.hour * 60 + at.minute),
        "machine_class": machine.machine_class,
        "machine_state": h.state.iloc[-1],
    }


def energy_examples(telemetry: pd.DataFrame, machines: pd.DataFrame) -> pd.DataFrame:
    records = []
    lookup = machines.set_index("machine_id", drop=False)
    t = telemetry.copy()
    t["date"] = t.recorded_at.dt.strftime("%Y-%m-%d")
    for (machine_id, day), group in t.groupby(["machine_id", "date"]):
        group = group.sort_values("recorded_at").reset_index(drop=True)
        machine = lookup.loc[machine_id]
        diesel = machine.powertrain == Powertrain.DIESEL
        capacity = float(machine.fuel_tank_l if diesel else machine.battery_kwh)
        measurements = group.fuel_used_l if diesel else group.energy_used_kwh
        if (
            not np.isfinite(capacity)
            or capacity <= 0
            or not np.isfinite(measurements).all()
        ):
            raise ValueError(
                "Energy examples require finite measurements and positive capacity"
            )
        usage = (
            (group.fuel_used_l if diesel else group.energy_used_kwh)
            .clip(lower=0)
            .to_numpy()
            / capacity
            * 100
        )
        replenishing = group.state.isin(
            [MachineState.REFUELING, MachineState.CHARGING]
        ).to_numpy()
        for index in range(HISTORY_MIN - 1, len(group) - FORECAST_MIN, 30):
            # No target crosses a missing minute, day, refuel or recharge.
            end = min(len(group), index + 1 + REPLAY_MAX_MIN)
            future = group.iloc[index + 1 : end]
            stop = np.flatnonzero(replenishing[index + 1 : end])
            if len(stop):
                future = future.iloc[: stop[0]]
            deltas = (
                group.recorded_at.iloc[index:end]
                .diff()
                .iloc[1:]
                .dt.total_seconds()
                .to_numpy()
            )
            gaps = np.flatnonzero(deltas != 60)
            if len(gaps):
                future = future.iloc[: gaps[0]]
            if len(future) < FORECAST_MIN or replenishing[index]:
                continue
            feature = history_features(
                group.iloc[index + 1 - HISTORY_MIN : index + 1], machine
            )
            used = usage[index + 1 : index + 1 + len(future)]
            reached = np.flatnonzero(np.cumsum(used) >= REPLAY_BUDGET_PCT)
            drawdown = np.nan
            if len(reached):
                j = reached[0]
                previous = used[:j].sum()
                drawdown = float(j + (REPLAY_BUDGET_PCT - previous) / used[j])
            records.append(
                {
                    **feature,
                    "machine_id": machine_id,
                    "date": day,
                    "powertrain": machine.powertrain,
                    "observed_at": group.recorded_at.iloc[index],
                    "future_used_pct": float(used[:FORECAST_MIN].sum()),
                    "drawdown_min": drawdown,
                    "replay_observed_min": len(future),
                }
            )
    return pd.DataFrame(records)


def fit_energy(train: pd.DataFrame, validation: pd.DataFrame) -> dict:
    bundles = {}
    for powertrain in Powertrain:
        tr = train.loc[train.powertrain == powertrain]
        val = validation.loc[validation.powertrain == powertrain]
        if len(tr) < 20 or len(val) < 10:
            raise ValueError(f"Insufficient energy examples for {powertrain}")
        choices = []
        for depth in [2, 3, 4]:
            model = Pipeline(
                [
                    ("features", preprocessing(ENERGY_NUMERIC, ENERGY_CATEGORY)),
                    (
                        "model",
                        XGBRegressor(
                            n_estimators=200,
                            max_depth=depth,
                            learning_rate=0.04,
                            objective="reg:squarederror",
                            random_state=SEED,
                            n_jobs=1,
                        ),
                    ),
                ]
            )
            model.fit(tr[ENERGY_FEATURES], tr.future_used_pct)
            predicted = np.maximum(0, model.predict(val[ENERGY_FEATURES]))
            choices.append((mean_absolute_error(val.future_used_pct, predicted), model))
        score, model = min(choices, key=lambda pair: pair[0])
        bundles[powertrain.value] = {
            "pipeline": model,
            "validation_mae_pct": float(score),
        }
    return {
        "models": bundles,
        "features": ENERGY_FEATURES,
        "forecast_min": FORECAST_MIN,
        "replay_budget_pct": REPLAY_BUDGET_PCT,
    }


def evaluate_energy(bundle: dict, examples: pd.DataFrame) -> dict:
    report = {}
    for powertrain in Powertrain:
        frame = examples.loc[examples.powertrain == powertrain]
        if frame.empty:
            raise ValueError(f"No evaluation examples for {powertrain}")
        predicted = np.maximum(
            0,
            bundle["models"][powertrain.value]["pipeline"].predict(
                frame[ENERGY_FEATURES]
            ),
        )
        baseline = frame.recent_used_pct.to_numpy()
        reached = frame.drawdown_min.notna().to_numpy()
        comparable = reached & (predicted > 0) & (baseline > 0)

        def drawdown_error(rate, frame=frame, comparable=comparable):
            return (
                float(
                    mean_absolute_error(
                        frame.drawdown_min.to_numpy()[comparable],
                        REPLAY_BUDGET_PCT / rate[comparable] * FORECAST_MIN,
                    )
                )
                if comparable.any()
                else None
            )

        report[powertrain.value] = {
            "forecast_sample_count": len(frame),
            "model_consumption_mae_pct": float(
                mean_absolute_error(frame.future_used_pct, predicted)
            ),
            "baseline_consumption_mae_pct": float(
                mean_absolute_error(frame.future_used_pct, baseline)
            ),
            "drawdown_reached_count": int(reached.sum()),
            "drawdown_censored_count": int((~reached).sum()),
            "drawdown_comparable_count": int(comparable.sum()),
            "model_zero_rate_count": int((predicted <= 0).sum()),
            "baseline_zero_rate_count": int((baseline <= 0).sum()),
            "model_drawdown_mae_min": drawdown_error(predicted),
            "baseline_drawdown_mae_min": drawdown_error(baseline),
        }
    return {
        "by_powertrain": report,
        "forecast_min": FORECAST_MIN,
        "drawdown_budget_pct": REPLAY_BUDGET_PCT,
        "replay_max_min": REPLAY_MAX_MIN,
        "limitation": "Drawdown replay measures time to consume a fixed 5% capacity budget, not actual time until the machine is empty. Censored intervals stop at replenishment, missing data, shift end, or 240 minutes. MAE uses reached cases where both forecasts have positive rates; counts disclose exclusions. Forecast MAE includes all eligible one-hour targets.",
    }
