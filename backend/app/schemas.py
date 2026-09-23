from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from shared.constants import Severity, TaskStatus


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


class TaskCreate(BaseModel):
    task_type: str = Field(min_length=1)
    site_id: str = Field(min_length=1)
    machine_id: str | None = None
    operator_id: str | None = None
    planned_duration_min: float = Field(gt=0)
    notes: str | None = None


class TaskRead(TaskCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    status: TaskStatus
    estimated_duration_min: float | None
    created_at: datetime


class TaskUpdate(BaseModel):
    machine_id: str | None = None
    operator_id: str | None = None
    planned_duration_min: float | None = Field(default=None, gt=0)
    notes: str | None = None


class IncidentCreate(BaseModel):
    site_id: str = Field(min_length=1)
    machine_id: str | None = None
    operator_id: str | None = None
    category: str = Field(min_length=1)
    severity: Severity = Severity.MEDIUM
    description: str = Field(min_length=1)


class IncidentRead(IncidentCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime


class WeatherRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    site_id: str
    observed_at: datetime
    temperature_c: float
    rain_mm: float
    alert: str | None


class WeatherCreate(BaseModel):
    site_id: str = Field(pattern=r"^S\d{2}$")
    observed_at: datetime
    temperature_c: float
    rain_mm: float = Field(default=0, ge=0)
    alert: str | None = None


class TrainingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    operator_id: str
    course_name: str
    expires_at: datetime | None
    completed: bool


class TrainingCreate(BaseModel):
    operator_id: str = Field(pattern=r"^OP\d{4}$")
    course_name: str = Field(min_length=1)
    expires_at: datetime | None = None
    completed: bool = True


class SiteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    site_id: str
    name: str
    city: str
    latitude: float
    longitude: float


class MachineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    machine_id: str
    machine_class: str
    powertrain: str
    site_id: str
    primary_operator_id: str | None


class OperatorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    operator_id: str
    name: str
    home_site_id: str
    experience_years: float
    certifications: list[str]


class CertificationRead(BaseModel):
    operator_id: str
    course_name: str
    is_certified: bool
    expires_at: datetime | None


class AlertIngest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    alert_code: str
    severity: Severity
    site_id: str = Field(pattern=r"^S\d{2}$")
    machine_id: str = Field(pattern=r"^[A-Z]{2,3}\d{3}$")
    operator_id: str | None = None
    started_at: datetime
    ended_at: datetime | None = None
    duration_min: int = Field(default=1, ge=1)


class EstimateRequest(BaseModel):
    task_type: str
    quantity: float = Field(gt=0)
    machine_class: str
    operator_id: str | None = None
    rain_mm: float = 0
    ground_condition: str = "normal"


class EstimateResponse(BaseModel):
    estimated_duration_min: float
    model_version: str
    source: str


class AnomalyRequest(BaseModel):
    features: dict[str, float]


class AnomalyResponse(BaseModel):
    is_anomaly: bool
    score: float
    model_version: str
    source: str


class EnergyRunoutRequest(BaseModel):
    machine_id: str = Field(pattern=r"^[A-Z]{2,3}\d{3}$")
    energy_remaining_pct: float = Field(ge=0, le=100)
    burn_rate_per_hour: float = Field(gt=0)
    remaining_task_min: float = Field(gt=0)


class EnergyRunoutResponse(BaseModel):
    will_complete_task: bool
    estimated_minutes_until_empty: float
    advisory: str
    model_version: str
    source: str


class AssignmentRequest(BaseModel):
    site_id: str = Field(pattern=r"^S\d{2}$")
    machine_class: str | None = None
    required_course: str | None = None
    task_duration_min: float = Field(gt=0)


class AssignmentSuggestion(BaseModel):
    operator_id: str
    machine_id: str
    estimated_duration_min: float
    is_certified: bool
    score: float
    reason: str


class AssignmentResponse(BaseModel):
    suggestions: list[AssignmentSuggestion]
    model_version: str
    source: str


PageItem = TypeVar("PageItem")


class Page(BaseModel, Generic[PageItem]):
    items: list[PageItem]
    next_cursor: str | None = None


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorBody
