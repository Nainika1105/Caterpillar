from __future__ import annotations

from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from shared.constants import Role
from backend.app.auth import current_user, require_roles
from backend.app.db import AlertRecord, Incident, MachineRecord, OperatorRecord, SiteRecord, TrainingRecord, User, WeatherReading, get_db
from backend.app.events import broker, connection_manager
from backend.app.schemas import AlertIngest, CertificationRead, IncidentCreate, IncidentRead, MachineRead, OperatorRead, Page, SiteRead, TrainingCreate, TrainingRead, WeatherCreate, WeatherRead
from backend.app.weather import weather_service

router = APIRouter(prefix="/api/v1", tags=["resources"])


@router.get("/sites", response_model=Page[SiteRead])
def list_sites(limit: int = Query(default=50, ge=1, le=100), db: Session = Depends(get_db), _: User = Depends(current_user)) -> Page[SiteRead]:
    sites = list(db.scalars(select(SiteRecord).order_by(SiteRecord.site_id).limit(limit + 1)))
    next_cursor = sites.pop().site_id if len(sites) > limit else None
    return Page[SiteRead](items=sites, next_cursor=next_cursor)


@router.get("/machines", response_model=Page[MachineRead])
def list_machines(site_id: str | None = None, limit: int = Query(default=50, ge=1, le=100), db: Session = Depends(get_db), _: User = Depends(current_user)) -> Page[MachineRead]:
    query = select(MachineRecord).order_by(MachineRecord.machine_id)
    if site_id:
        query = query.where(MachineRecord.site_id == site_id)
    machines = list(db.scalars(query.limit(limit + 1)))
    next_cursor = machines.pop().machine_id if len(machines) > limit else None
    return Page[MachineRead](items=machines, next_cursor=next_cursor)


@router.get("/operators", response_model=Page[OperatorRead])
def list_operators(limit: int = Query(default=50, ge=1, le=100), db: Session = Depends(get_db), _: User = Depends(current_user)) -> Page[OperatorRead]:
    operators = list(db.scalars(select(OperatorRecord).order_by(OperatorRecord.operator_id).limit(limit + 1)))
    next_cursor = operators.pop().operator_id if len(operators) > limit else None
    result = [OperatorRead.model_validate({**operator.__dict__, "certifications": operator.certifications.split(";") if operator.certifications else []}) for operator in operators]
    return Page[OperatorRead](items=result, next_cursor=next_cursor)


@router.post("/alerts/ingest", response_model=AlertIngest, status_code=201)
async def ingest_alert(payload: AlertIngest, db: Session = Depends(get_db), _: User = Depends(current_user)) -> AlertIngest:
    alert = AlertRecord(alert_id=f"AL{db.query(AlertRecord).count() + 1:05d}", **payload.model_dump())
    db.add(alert)
    db.commit()
    event = {"type": "alert.created", "data": payload.model_dump(mode="json") | {"alert_id": alert.alert_id}}
    await broker.publish(event)
    if not broker.redis_url:
        await connection_manager.broadcast(event)
    return payload


@router.get("/alerts", response_model=Page[AlertIngest])
def list_alerts(limit: int = Query(default=50, ge=1, le=100), db: Session = Depends(get_db), _: User = Depends(current_user)) -> Page[AlertIngest]:
    alerts = list(db.scalars(select(AlertRecord).order_by(AlertRecord.created_at.desc()).limit(limit + 1)))
    next_cursor = alerts.pop().alert_id if len(alerts) > limit else None
    return Page[AlertIngest](items=[AlertIngest.model_validate(alert) for alert in alerts], next_cursor=next_cursor)


@router.post("/incidents", response_model=IncidentRead, status_code=201)
async def create_incident(payload: IncidentCreate, db: Session = Depends(get_db), _: User = Depends(current_user)) -> Incident:
    incident = Incident(id=f"IN{db.query(Incident).count() + 1:04d}", **payload.model_dump())
    db.add(incident)
    db.commit()
    db.refresh(incident)
    event = {"type": "incident.created", "data": IncidentRead.model_validate(incident).model_dump(mode="json")}
    await broker.publish(event)
    if not broker.redis_url:
        await connection_manager.broadcast(event)
    return incident


@router.get("/incidents", response_model=Page[IncidentRead])
def list_incidents(limit: int = Query(default=50, ge=1, le=100), db: Session = Depends(get_db), _: User = Depends(current_user)) -> Page[IncidentRead]:
    incidents = list(db.scalars(select(Incident).order_by(Incident.created_at.desc()).limit(limit + 1)))
    next_cursor = incidents.pop().id if len(incidents) > limit else None
    return Page[IncidentRead](items=incidents, next_cursor=next_cursor)


@router.get("/incidents/{incident_id}", response_model=IncidentRead)
def get_incident(incident_id: str, db: Session = Depends(get_db), _: User = Depends(current_user)) -> Incident:
    incident = db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@router.get("/weather/{site_id}", response_model=WeatherRead | None)
def latest_weather(site_id: str, db: Session = Depends(get_db), _: User = Depends(current_user)) -> WeatherReading | None:
    return db.scalar(select(WeatherReading).where(WeatherReading.site_id == site_id).order_by(WeatherReading.observed_at.desc()).limit(1))


@router.post("/weather/{site_id}/refresh", response_model=WeatherRead)
async def refresh_weather(site_id: str, db: Session = Depends(get_db), _: User = Depends(require_roles(Role.ADMIN, Role.TRAINER))) -> WeatherReading:
    site = db.get(SiteRecord, site_id)
    if site is None:
        raise HTTPException(status_code=404, detail="Site not found")
    try:
        reading_data = await weather_service.fetch(site.latitude, site.longitude)
    except (RuntimeError, httpx.HTTPError) as exc:
        raise HTTPException(status_code=503, detail="Weather provider unavailable") from exc
    reading = WeatherReading(site_id=site_id, **reading_data)
    db.add(reading)
    db.commit()
    db.refresh(reading)
    return reading


@router.post("/weather", response_model=WeatherRead, status_code=201)
def ingest_weather(payload: WeatherCreate, db: Session = Depends(get_db), _: User = Depends(require_roles(Role.ADMIN, Role.TRAINER))) -> WeatherReading:
    reading = WeatherReading(**payload.model_dump())
    db.add(reading)
    db.commit()
    db.refresh(reading)
    return reading


@router.get("/operators/{operator_id}/training", response_model=list[TrainingRead])
def operator_training(operator_id: str, db: Session = Depends(get_db), _: User = Depends(current_user)) -> list[TrainingRecord]:
    return list(db.scalars(select(TrainingRecord).where(TrainingRecord.operator_id == operator_id)))


@router.post("/training", response_model=TrainingRead, status_code=201)
def create_training(payload: TrainingCreate, db: Session = Depends(get_db), _: User = Depends(require_roles(Role.ADMIN, Role.TRAINER))) -> TrainingRecord:
    record = TrainingRecord(**payload.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/operators/{operator_id}/certifications/{course_name}", response_model=CertificationRead)
def certification_status(operator_id: str, course_name: str, db: Session = Depends(get_db), _: User = Depends(current_user)) -> CertificationRead:
    record = db.scalar(select(TrainingRecord).where(TrainingRecord.operator_id == operator_id, TrainingRecord.course_name == course_name).order_by(TrainingRecord.expires_at.desc()))
    now = datetime.now(timezone.utc)
    certified = bool(record and record.completed and (record.expires_at is None or record.expires_at.replace(tzinfo=timezone.utc) >= now))
    return CertificationRead(operator_id=operator_id, course_name=course_name, is_certified=certified, expires_at=record.expires_at if record else None)
