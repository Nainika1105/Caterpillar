from __future__ import annotations

import csv
import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from shared.constants import Role, Severity, TaskStatus
from backend.app.auth import current_user, get_user, pwd_context, require_roles
from backend.app.events import broker, connection_manager
from backend.app.scheduler import WeatherScheduler
from backend.app.db import AlertRecord, Incident, MachineRecord, OperatorRecord, SessionLocal, SiteRecord, Task, TelemetryRecord, TrainingRecord, User, WeatherReading, get_db, init_db
from backend.app.mqtt import MQTTIngestService
from backend.app.schemas import (AlertIngest, AnomalyRequest, AnomalyResponse, AssignmentRequest, AssignmentResponse, AssignmentSuggestion, CertificationRead, EnergyRunoutRequest, EnergyRunoutResponse, EstimateRequest, EstimateResponse, IncidentCreate, IncidentRead, MachineRead, OperatorRead, Page, SiteRead, TaskCreate, TaskRead, TaskUpdate, Token, TrainingCreate, TrainingRead, WeatherCreate, WeatherRead)
from backend.app.routers.auth import router as auth_router
from backend.app.routers.resources import router as resources_router
from backend.app.routers.tasks import router as tasks_router
from backend.app.routers.predictions import router as predictions_router
from backend.app.weather import weather_service


manager = connection_manager
weather_scheduler = WeatherScheduler(lambda: refresh_all_weather())
mqtt_service = MQTTIngestService(lambda topic, payload: handle_mqtt_message(topic, payload))
event_loop: asyncio.AbstractEventLoop | None = None
app = FastAPI(title="CAT Smart Operator Assistant API", version="0.1.0")
API_PREFIX = "/api/v1"
app.include_router(auth_router)
app.include_router(tasks_router)
app.include_router(resources_router)
app.include_router(predictions_router)


@app.exception_handler(HTTPException)
async def http_error(_: Request, exc: HTTPException) -> Any:
    code = "request_error"
    if exc.status_code == 404:
        code = "resource_not_found"
    elif exc.status_code == 401:
        code = "unauthorized"
    elif exc.status_code == 403:
        code = "forbidden"
    return JSONResponse(status_code=exc.status_code, content={"error": {"code": code, "message": str(exc.detail)}})


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError) -> Any:
    return JSONResponse(status_code=422, content={"error": {"code": "validation_error", "message": str(exc.errors())}})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "api"}


@app.websocket("/ws")
async def alerts(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.on_event("startup")
def seed_demo_admin() -> None:
    init_db()
    with SessionLocal() as db:
        if get_user("admin", db) is None:
            db.add(User(username="admin", password_hash=pwd_context.hash("admin"), role=Role.ADMIN))
        seed_reference_data(db)
        db.commit()


@app.on_event("startup")
async def start_event_subscriber() -> None:
    global event_loop
    event_loop = asyncio.get_running_loop()
    await broker.start_subscriber(connection_manager.broadcast)
    if os.getenv("WEATHER_API_KEY"):
        weather_scheduler.start()
    if os.getenv("ENABLE_MQTT", "false").lower() == "true":
        mqtt_service.start()


@app.on_event("shutdown")
async def stop_event_subscriber() -> None:
    await broker.close()
    await weather_scheduler.stop()
    if os.getenv("ENABLE_MQTT", "false").lower() == "true":
        mqtt_service.stop()


async def refresh_all_weather() -> None:
    with SessionLocal() as db:
        sites = list(db.scalars(select(SiteRecord)))
        for site in sites:
            try:
                reading_data = await weather_service.fetch(site.latitude, site.longitude)
            except Exception:
                continue
            db.add(WeatherReading(site_id=site.site_id, **reading_data))
        db.commit()


def handle_mqtt_message(topic: str, payload: dict[str, Any]) -> None:
    with SessionLocal() as db:
        db.add(TelemetryRecord(topic=topic, schema_version=str(payload["schema_version"]), payload_json=json.dumps(payload)))
        db.commit()
    if topic.endswith("/alerts"):
        event = {"type": "alert.received", "data": payload}
        if event_loop is not None:
            asyncio.run_coroutine_threadsafe(broker.publish(event), event_loop)
            if not broker.redis_url:
                asyncio.run_coroutine_threadsafe(connection_manager.broadcast(event), event_loop)


def seed_reference_data(db: Session) -> None:
    data_root = Path(__file__).resolve().parents[2] / "data"
    if db.scalar(select(SiteRecord).limit(1)) is None:
        with (data_root / "sites.csv").open(newline="", encoding="utf-8") as source:
            for row in csv.DictReader(source):
                db.add(SiteRecord(site_id=row["site_id"], name=row["name"], city=row["city"], latitude=float(row["lat"]), longitude=float(row["lon"])))
    if db.scalar(select(MachineRecord).limit(1)) is None:
        with (data_root / "machines.csv").open(newline="", encoding="utf-8") as source:
            for row in csv.DictReader(source):
                db.add(MachineRecord(machine_id=row["machine_id"], machine_class=row["machine_class"], powertrain=row["powertrain"], site_id=row["site_id"], primary_operator_id=row.get("primary_operator_id") or None))
    if db.scalar(select(OperatorRecord).limit(1)) is None:
        with (data_root / "operators.csv").open(newline="", encoding="utf-8") as source:
            for row in csv.DictReader(source):
                db.add(OperatorRecord(operator_id=row["operator_id"], name=row["name"], home_site_id=row["home_site_id"], experience_years=float(row["experience_years"]), certifications=row.get("certifications", "")))
    if db.scalar(select(TrainingRecord).limit(1)) is None:
        training_path = data_root / "training_records.csv"
        if training_path.exists():
            with training_path.open(newline="", encoding="utf-8") as source:
                for row in csv.DictReader(source):
                    expires = row.get("valid_until") or None
                    expires_at = datetime.fromisoformat(expires).replace(tzinfo=timezone.utc) if expires else None
                    db.add(TrainingRecord(operator_id=row["operator_id"], course_name=row.get("course_name") or row.get("course", ""), expires_at=expires_at, completed=True))
