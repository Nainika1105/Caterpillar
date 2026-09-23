"""Read legacy synthetic CSVs without changing the source dataset."""

import os
from pathlib import Path

import pandas as pd

from shared.constants import (
    AlertCode,
    AnomalyType,
    MachineClass,
    MachineState,
    Powertrain,
    SeatbeltStatus,
    TaskStatus,
)


def utc(series: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(series, errors="raise")
    if parsed.dt.tz is None:
        parsed = parsed.dt.tz_localize(os.getenv("CAT_SOURCE_TIMEZONE", "Asia/Kolkata"))
    return parsed.dt.tz_convert("UTC")


def load_data(root: Path) -> dict[str, pd.DataFrame]:
    names = [
        "telemetry_1min",
        "tasks",
        "machines",
        "operators",
        "safety_alerts",
        "anomalies_ground_truth",
    ]
    data = {name: pd.read_csv(root / f"{name}.csv") for name in names}
    tel = (
        data["telemetry_1min"]
        .rename(
            columns={
                "timestamp": "recorded_at",
                "power_on": "is_power_on",
                "operator_present": "is_operator_present",
            }
        )
        .copy()
    )
    tel["recorded_at"] = utc(tel["recorded_at"])
    if tel.recorded_at.isna().any():
        raise ValueError("Missing telemetry recorded_at")
    if tel.duplicated(["machine_id", "recorded_at"]).any():
        raise ValueError("Duplicate machine telemetry timestamps")
    for name, key in [
        ("machines", "machine_id"),
        ("operators", "operator_id"),
        ("tasks", "task_id"),
    ]:
        if data[name][key].isna().any() or data[name][key].duplicated().any():
            raise ValueError(f"Invalid or duplicate {key}")
    if not tel.machine_id.isin(data["machines"].machine_id).all():
        raise ValueError("Unknown telemetry machine_id")
    if not tel.operator_id.isin(data["operators"].operator_id).all():
        raise ValueError("Unknown telemetry operator_id")
    if not tel.task_id.dropna().isin(data["tasks"].task_id).all():
        raise ValueError("Unknown telemetry task_id")
    linked = tel.loc[
        tel.task_id.notna(), ["task_id", "machine_id", "operator_id", "site_id"]
    ].merge(
        data["tasks"][["task_id", "machine_id", "operator_id", "site_id"]],
        on="task_id",
        suffixes=("", "_task"),
        validate="many_to_one",
    )
    inconsistent = (
        linked.machine_id.ne(linked.machine_id_task)
        | linked.operator_id.ne(linked.operator_id_task)
        | linked.site_id.ne(linked.site_id_task)
    )
    if inconsistent.any():
        bad_ids = sorted(linked.loc[inconsistent, "task_id"].unique())
        raise ValueError(
            f"Telemetry task links contradict assigned machine/operator/site: {', '.join(bad_ids[:5])}"
        )
    if not data["machines"].powertrain.isin(list(Powertrain)).all():
        raise ValueError("Unknown machine powertrain")
    if not data["machines"].machine_class.isin(list(MachineClass)).all():
        raise ValueError("Unknown machine_class")
    for field in ["is_power_on", "is_operator_present"]:
        if not tel[field].isin([0, 1]).all():
            raise ValueError(f"Invalid boolean: {field}")
        tel[field] = tel[field].astype(bool)
    tel["seatbelt_status"] = tel.seatbelt_status.str.lower()
    if (
        not tel.seatbelt_status.isin(list(SeatbeltStatus)).all()
        or not tel.state.isin(list(MachineState)).all()
    ):
        raise ValueError("Unknown telemetry enum")
    for field in ["fuel_level_pct", "battery_soc_pct"]:
        if not tel[field].dropna().between(0, 100).all():
            raise ValueError(f"Out-of-range percentage: {field}")
    tel = tel.merge(
        data["machines"][["machine_id", "powertrain", "machine_class"]],
        on="machine_id",
        validate="many_to_one",
    )
    tel["fuel_used_l"] = tel.energy_used.where(tel.powertrain == Powertrain.DIESEL)
    tel["energy_used_kwh"] = tel.energy_used.where(
        tel.powertrain == Powertrain.ELECTRIC
    )
    tel = tel.drop(columns=["energy_used", "anomaly_id", "anomaly_type"])
    data["telemetry_1min"] = tel.sort_values(["machine_id", "recorded_at"])
    tasks = data["tasks"].rename(
        columns={
            "status": "task_status",
            "planned_start": "planned_start_at",
            "actual_start": "actual_start_at",
            "actual_end": "actual_end_at",
        }
    )
    tasks["task_status"] = tasks.task_status.replace(
        {"not_started": TaskStatus.SCHEDULED}
    )
    if not tasks.task_status.isin(list(TaskStatus)).all():
        raise ValueError("Unknown task_status")
    for field in ["planned_start_at", "actual_start_at", "actual_end_at"]:
        tasks[field] = utc(tasks[field])
    data["tasks"] = tasks
    for name in ["safety_alerts", "anomalies_ground_truth"]:
        data[name] = data[name].rename(
            columns={"start": "started_at", "end": "ended_at", "rule": "alert_code"}
        )
        for field in ["started_at", "ended_at"]:
            data[name][field] = utc(data[name][field])
    data["safety_alerts"]["alert_code"] = data["safety_alerts"].alert_code.str.lower()
    if not data["safety_alerts"].alert_code.isin(list(AlertCode)).all():
        raise ValueError("Unknown alert_code")
    if not data["anomalies_ground_truth"].anomaly_type.isin(list(AnomalyType)).all():
        raise ValueError("Unknown anomaly_type")
    return data
