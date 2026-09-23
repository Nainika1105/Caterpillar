from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from shared.constants import AnomalyType, EnergyAction, MachineClass, Powertrain


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class TaskDurationInput(Contract):
    machine_class: MachineClass
    task_type: str
    ground_condition: str
    quantity: float = Field(gt=0)
    unit: str
    planned_duration_min: float = Field(gt=0)
    rain_prev_24h_mm: float = Field(ge=0)
    experience_years: float = Field(ge=0)


class TaskDurationPrediction(Contract):
    estimated_duration_min: float
    model_version: str


class EnergyInput(Contract):
    powertrain: Powertrain
    remaining_task_min: float = Field(ge=0)
    fuel_remaining_l: float | None = Field(default=None, ge=0)
    fuel_rate_lph: float | None = Field(default=None, ge=0)
    energy_remaining_kwh: float | None = Field(default=None, ge=0)
    power_kw: float | None = Field(default=None, ge=0)


class EnergyPrediction(Contract):
    estimated_remaining_min: float | None
    has_sufficient_energy: bool | None
    recommended_action: EnergyAction
    method: str = "linear_consumption_baseline"


class AssignmentCandidate(Contract):
    machine_id: str
    operator_id: str
    site_id: str
    machine_class: MachineClass
    certifications: set[str]
    certification_valid_until: dict[str, date]
    is_machine_available: bool
    is_operator_available: bool
    estimated_duration_min: float = Field(gt=0)
    estimated_remaining_min: float = Field(ge=0)


class AnomalyPrediction(Contract):
    machine_id: str
    operator_id: str
    date: date
    anomaly_score: float
    is_anomaly: bool
    model_version: str


class ChargePoint(Contract):
    energy_point_id: str
    site_id: str
    power_kw: float = Field(gt=0)
    is_available: bool
    is_compatible: bool


class ChargeInput(Contract):
    site_id: str
    battery_capacity_kwh: float = Field(gt=0)
    energy_remaining_kwh: float = Field(ge=0)
    target_soc_pct: float = Field(gt=0, le=100)
    max_charge_kw: float = Field(gt=0)
    charging_efficiency_pct: float = Field(default=90, gt=0, le=100)


class ChargeAdvisory(Contract):
    energy_point_id: str
    estimated_charge_min: float = Field(ge=0)
    energy_required_kwh: float = Field(ge=0)
    method: str = "constant_power_estimate"


class FuelAnomalyPrediction(Contract):
    machine_id: str
    operator_id: str
    date: date
    anomaly_types: list[AnomalyType]
    fuel_burn_score: float
    fuel_burn_ratio: float | None
    parked_fuel_drop_pct: float
    has_sufficient_fuel_observations: bool
    model_version: str


class EnergyForecastInput(Contract):
    machine_id: str
    machine_class: MachineClass
    powertrain: Powertrain
    remaining_task_min: float = Field(ge=0)
    fuel_remaining_l: float | None = Field(default=None, ge=0)
    energy_remaining_kwh: float | None = Field(default=None, ge=0)
    fuel_tank_l: float | None = Field(default=None, gt=0)
    battery_kwh: float | None = Field(default=None, gt=0)


class EnergyForecastPrediction(EnergyPrediction):
    forecast_used_pct: float = Field(ge=0)
    forecast_horizon_min: int = Field(gt=0)
    is_extrapolation: bool
    model_version: str
    method: str = "learned_one_hour_consumption"
