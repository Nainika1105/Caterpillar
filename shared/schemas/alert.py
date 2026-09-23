from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from shared.constants import AlertCode, Severity


class AlertCreate(BaseModel):
    schema_version: str = "1.0"
    alert_code: AlertCode
    severity: Severity
    site_id: str = Field(pattern=r"^S\d{2}$")
    machine_id: str = Field(pattern=r"^[A-Z]{2,3}\d{3}$")
    operator_id: str | None = Field(default=None, pattern=r"^OP\d{4}$")
    started_at: datetime
    ended_at: datetime | None = None
    duration_min: int = Field(default=1, ge=1)


class Alert(AlertCreate):
    model_config = ConfigDict(from_attributes=True)
    alert_id: str = Field(pattern=r"^AL\d{5}$")
    created_at: datetime
