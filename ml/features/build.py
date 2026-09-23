import pandas as pd

from shared.constants import MachineState, SeatbeltStatus, TaskStatus

TASK_FEATURES = [
    "machine_class",
    "task_type",
    "ground_condition",
    "quantity",
    "unit",
    "planned_duration_min",
    "rain_prev_24h_mm",
    "experience_years",
]
TASK_CATEGORICAL = ["machine_class", "task_type", "ground_condition", "unit"]
SHIFT_FEATURES = [
    "idle_pct",
    "unbelted_moving_pct",
    "unattended_pct",
    "proximity_min_m",
    "ground_speed_kmh",
    "coolant_temp_c",
    "harsh_events_count",
    "fuel_rate_lph",
    "power_kw",
    "fuel_per_load_cycle_l",
    "energy_per_load_cycle_kwh",
]


def task_features(tasks: pd.DataFrame, operators: pd.DataFrame) -> pd.DataFrame:
    rows = tasks.loc[
        (tasks.task_status == TaskStatus.COMPLETED) & tasks.actual_duration_min.gt(0)
    ].copy()
    return rows.merge(
        operators[["operator_id", "experience_years"]],
        on="operator_id",
        validate="many_to_one",
    )


def shift_features(telemetry: pd.DataFrame) -> pd.DataFrame:
    if telemetry.duplicated(["machine_id", "recorded_at"]).any():
        raise ValueError("Duplicate machine telemetry timestamps")
    t = telemetry.copy()
    # Supplied generator has one daytime shift per UTC date.
    t["date"] = t.recorded_at.dt.strftime("%Y-%m-%d")
    t["idle_pct"] = (t.state == MachineState.IDLE).astype(float) * 100
    t["unbelted_moving_pct"] = (
        (t.seatbelt_status == SeatbeltStatus.UNFASTENED) & t.ground_speed_kmh.gt(0)
    ).astype(float) * 100
    t["seatbelt_violations"] = t["unbelted_moving_pct"] / 100
    t["unattended_pct"] = (t.is_power_on & ~t.is_operator_present).astype(float) * 100
    rows = t.groupby(
        ["machine_id", "operator_id", "machine_class", "date"], as_index=False
    ).agg(
        started_at=("recorded_at", "min"),
        ended_at=("recorded_at", "max"),
        observed_min=("recorded_at", "size"),
        idle_pct=("idle_pct", "mean"),
        unbelted_moving_pct=("unbelted_moving_pct", "mean"),
        seatbelt_violations=("seatbelt_violations", "sum"),
        unattended_pct=("unattended_pct", "mean"),
        proximity_min_m=("proximity_min_m", "min"),
        ground_speed_kmh=("ground_speed_kmh", "max"),
        coolant_temp_c=("coolant_temp_c", "max"),
        harsh_events_count=("harsh_events", "sum"),
        fuel_rate_lph=("fuel_rate_lph", "mean"),
        power_kw=("power_kw", "mean"),
        fuel_used_l=("fuel_used_l", "sum"),
        energy_used_kwh=("energy_used_kwh", "sum"),
        load_cycles_count=("load_cycles", "sum"),
    )
    denominator = rows.load_cycles_count.replace(0, float("nan"))
    rows["fuel_per_load_cycle_l"] = rows.fuel_used_l / denominator
    rows["energy_per_load_cycle_kwh"] = rows.energy_used_kwh / denominator
    return rows


def operator_analytics(
    telemetry: pd.DataFrame, tasks: pd.DataFrame | None = None
) -> pd.DataFrame:
    shifts = shift_features(telemetry)
    for col in ["idle_pct", "unbelted_moving_pct", "unattended_pct"]:
        shifts[col] *= shifts.observed_min / 100
    result = shifts.groupby(["operator_id", "machine_class"], as_index=False)[
        [
            "observed_min",
            "idle_pct",
            "unbelted_moving_pct",
            "unattended_pct",
            "seatbelt_violations",
            "harsh_events_count",
            "fuel_used_l",
            "energy_used_kwh",
            "load_cycles_count",
        ]
    ].sum()
    for col in ["idle_pct", "unbelted_moving_pct", "unattended_pct"]:
        result[col] = result[col] / result.observed_min * 100
    result["seatbelt_violations"] = result["seatbelt_violations"].astype(int)
    result["harsh_events_count"] = result["harsh_events_count"].astype(int)
    if tasks is None:
        result["completed_tasks"] = None
    else:
        required = {"operator_id", "machine_class", "task_id", "task_status"}
        missing = sorted(required - set(tasks.columns))
        if missing:
            raise ValueError(
                f"Missing required task analytics columns: {', '.join(missing)}"
            )
        completed = (
            tasks.loc[tasks.task_status == TaskStatus.COMPLETED]
            .groupby(["operator_id", "machine_class"], as_index=False)
            .task_id.nunique()
            .rename(columns={"task_id": "completed_tasks"})
        )
        result = result.merge(
            completed,
            on=["operator_id", "machine_class"],
            how="left",
            validate="one_to_one",
        )
        result["completed_tasks"] = result.completed_tasks.fillna(0).astype(int)
    return result
