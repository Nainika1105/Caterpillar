from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from shared.constants import TaskStatus


class TaskCreate(BaseModel):
    task_type: str = Field(min_length=1)
    site_id: str = Field(pattern=r"^S\d{2}$")
    machine_id: str | None = Field(default=None, pattern=r"^[A-Z]{2,3}\d{3}$")
    operator_id: str | None = Field(default=None, pattern=r"^OP\d{4}$")
    planned_duration_min: float = Field(gt=0)
    quantity: float | None = Field(default=None, gt=0)
    notes: str | None = None


class Task(TaskCreate):
    model_config = ConfigDict(from_attributes=True)
    task_id: str = Field(pattern=r"^T\d{5}$")
    status: TaskStatus
    estimated_duration_min: float | None
    created_at: datetime
    updated_at: datetime
