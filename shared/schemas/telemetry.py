from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from shared.constants import MachineState, ProximityZone, SeatbeltStatus


class Telemetry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0"
    timestamp: datetime
    site_id: str = Field(pattern=r"^S\d{2}$")
    machine_id: str = Field(pattern=r"^[A-Z]{2,3}\d{3}$")
    operator_id: str | None = Field(default=None, pattern=r"^OP\d{4}$")
    task_id: str | None = Field(default=None, pattern=r"^T\d{5}$")
    state: MachineState
    is_power_on: bool
    is_operator_present: bool
    seatbelt_status: SeatbeltStatus
    ground_speed_kmh: float = Field(ge=0)
    fuel_level_pct: float | None = Field(default=None, ge=0, le=100)
    battery_soc_pct: float | None = Field(default=None, ge=0, le=100)
    fuel_rate_lph: float | None = Field(default=None, ge=0)
    power_kw: float | None = None
    fuel_used_l: float | None = Field(default=None, ge=0)
    energy_used_kwh: float | None = Field(default=None, ge=0)
    proximity_min_m: float = Field(ge=0)
    proximity_zone: ProximityZone
    coolant_temp_c: float | None = None
    load_cycles: int = Field(default=0, ge=0)
    harsh_events: int = Field(default=0, ge=0)
