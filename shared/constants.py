"""Canonical values for the Member 3 integration contract."""

from enum import StrEnum


class Role(StrEnum):
    ADMIN = "admin"
    OPERATOR = "operator"
    TRAINER = "trainer"


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Powertrain(StrEnum):
    DIESEL = "diesel"
    ELECTRIC = "electric"


class EnergyAction(StrEnum):
    NONE = "none"
    REFUEL = "refuel"
    RECHARGE = "recharge"
    UNKNOWN = "unknown"


class MachineClass(StrEnum):
    EXCAVATOR = "excavator"
    MINI_EXCAVATOR = "mini_excavator"
    WHEEL_LOADER = "wheel_loader"
    DOZER = "dozer"
    BACKHOE_LOADER = "backhoe_loader"
    ELECTRIC_EXCAVATOR = "electric_excavator"
    ELECTRIC_MINI_EXCAVATOR = "electric_mini_excavator"


class MachineState(StrEnum):
    WORKING = "working"
    IDLE = "idle"
    TRAVEL = "travel"
    OFF = "off"
    CHARGING = "charging"
    REFUELING = "refueling"
    WEATHER_HOLD = "weather_hold"
    HEAT_REST = "heat_rest"


class TaskStatus(StrEnum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    PARTIAL = "partial"
    CANCELLED = "cancelled"


class SeatbeltStatus(StrEnum):
    FASTENED = "fastened"
    UNFASTENED = "unfastened"


class ProximityZone(StrEnum):
    CLEAR = "clear"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertCode(StrEnum):
    SEATBELT_UNFASTENED_MOVING = "seatbelt_unfastened_moving"
    UNATTENDED_RUNNING = "unattended_running"
    PROXIMITY_DANGER = "proximity_danger"
    OVERSPEED = "overspeed"
    COOLANT_HIGH = "coolant_high"
    EXCESSIVE_IDLE = "excessive_idle"
    HARSH_OPERATION = "harsh_operation"


class AnomalyType(StrEnum):
    EXCESSIVE_IDLING = "excessive_idling"
    UNATTENDED_RUNNING = "unattended_running"
    UNBELTED_OPERATION = "unbelted_operation"
    PROXIMITY_BREACH = "proximity_breach"
    OVERSPEED_TRAVEL = "overspeed_travel"
    HARSH_OPERATION = "harsh_operation"
    OVERHEATING = "overheating"
    ABNORMAL_FUEL_BURN = "abnormal_fuel_burn"
    FUEL_LOSS = "fuel_loss"


EV_CERTIFICATION = "ev_high_voltage"
SEED = 42
FUEL_BURN_MIN_RATIO = 1.05
FUEL_MIN_POWERED_SAMPLE_COUNT = 30
FUEL_FOREST_MIN_SCORE = 0.5
FUEL_LOSS_MIN_DROP_PCT = 0.2
ENERGY_HISTORY_MIN = 60
ENERGY_FORECAST_MIN = 60
ENERGY_REPLAY_MAX_MIN = 240
ENERGY_REPLAY_BUDGET_PCT = 5.0
