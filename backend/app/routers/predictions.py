from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.auth import current_user
from backend.app.db import MachineRecord, OperatorRecord, TrainingRecord, User, get_db
from backend.app.schemas import AnomalyRequest, AnomalyResponse, AssignmentRequest, AssignmentResponse, AssignmentSuggestion, EnergyRunoutRequest, EnergyRunoutResponse, EstimateRequest, EstimateResponse

router = APIRouter(prefix="/api/v1/predict", tags=["predictions"])


@router.post("/task-duration", response_model=EstimateResponse)
def estimate_time(payload: EstimateRequest, _: User = Depends(current_user)) -> EstimateResponse:
    multiplier = 1.15 if payload.ground_condition.lower() in {"wet", "rocky"} else 1.0
    multiplier += min(payload.rain_mm / 100, 0.25)
    estimate = max(1.0, payload.quantity * multiplier)
    return EstimateResponse(estimated_duration_min=round(estimate, 2), model_version="baseline-v1", source="backend-fallback")


@router.post("/anomaly", response_model=AnomalyResponse)
def score_anomaly(payload: AnomalyRequest, _: User = Depends(current_user)) -> AnomalyResponse:
    idle_ratio = payload.features.get("idle_ratio", 0)
    harsh_events = payload.features.get("harsh_events", 0)
    score = min(1.0, idle_ratio * 0.6 + harsh_events / 20 * 0.4)
    return AnomalyResponse(is_anomaly=score >= 0.7, score=round(score, 4), model_version="baseline-v1", source="backend-fallback")


@router.post("/energy-runout", response_model=EnergyRunoutResponse)
def predict_energy_runout(payload: EnergyRunoutRequest, _: User = Depends(current_user)) -> EnergyRunoutResponse:
    minutes_until_empty = payload.energy_remaining_pct / payload.burn_rate_per_hour * 60
    completes = minutes_until_empty >= payload.remaining_task_min
    advisory = "Energy is sufficient for the remaining task" if completes else "Charge or refuel before continuing; replacement machine may be required"
    return EnergyRunoutResponse(will_complete_task=completes, estimated_minutes_until_empty=round(minutes_until_empty, 2), advisory=advisory, model_version="baseline-v1", source="backend-fallback")


@router.post("/assignment", response_model=AssignmentResponse)
def suggest_assignment(payload: AssignmentRequest, db: Session = Depends(get_db), _: User = Depends(current_user)) -> AssignmentResponse:
    machines_query = select(MachineRecord).where(MachineRecord.site_id == payload.site_id)
    if payload.machine_class:
        machines_query = machines_query.where(MachineRecord.machine_class == payload.machine_class)
    machines = list(db.scalars(machines_query))
    suggestions: list[AssignmentSuggestion] = []
    operators = list(db.scalars(select(OperatorRecord).where(OperatorRecord.home_site_id == payload.site_id)))
    for machine in machines:
        for operator in operators:
            record = None
            if payload.required_course:
                record = db.scalar(select(TrainingRecord).where(TrainingRecord.operator_id == operator.operator_id, TrainingRecord.course_name == payload.required_course).order_by(TrainingRecord.expires_at.desc()))
            certified = not payload.required_course or bool(record and record.completed and (record.expires_at is None or record.expires_at.replace(tzinfo=timezone.utc) >= datetime.now(timezone.utc)))
            if not certified:
                continue
            score = round(1 / max(payload.task_duration_min, 1) + operator.experience_years / 100, 4)
            suggestions.append(AssignmentSuggestion(operator_id=operator.operator_id, machine_id=machine.machine_id, estimated_duration_min=payload.task_duration_min, is_certified=True, score=score, reason="certified operator and matching site"))
    suggestions.sort(key=lambda suggestion: suggestion.score, reverse=True)
    return AssignmentResponse(suggestions=suggestions[:10], model_version="baseline-v1", source="backend-fallback")
