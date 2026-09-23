from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Generator

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from shared.constants import Role, Severity, TaskStatus

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./backend.db")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default=Role.OPERATOR)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[str] = mapped_column(String(6), primary_key=True)
    task_type: Mapped[str] = mapped_column(String(80))
    site_id: Mapped[str] = mapped_column(String(20))
    machine_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    operator_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=TaskStatus.SCHEDULED)
    planned_duration_min: Mapped[float] = mapped_column(Float)
    estimated_duration_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)


class Incident(Base):
    __tablename__ = "incidents"
    id: Mapped[str] = mapped_column(String(6), primary_key=True)
    site_id: Mapped[str] = mapped_column(String(20))
    machine_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    operator_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    category: Mapped[str] = mapped_column(String(80))
    severity: Mapped[str] = mapped_column(String(20), default=Severity.MEDIUM)
    description: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)


class WeatherReading(Base):
    __tablename__ = "weather_readings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    site_id: Mapped[str] = mapped_column(String(20), index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime)
    temperature_c: Mapped[float] = mapped_column(Float)
    rain_mm: Mapped[float] = mapped_column(Float, default=0)
    alert: Mapped[str | None] = mapped_column(String(120), nullable=True)


class TrainingRecord(Base):
    __tablename__ = "training_records"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    operator_id: Mapped[str] = mapped_column(String(20), index=True)
    course_name: Mapped[str] = mapped_column(String(120))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed: Mapped[bool] = mapped_column(Boolean, default=True)


class SiteRecord(Base):
    __tablename__ = "sites"
    site_id: Mapped[str] = mapped_column(String(3), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    city: Mapped[str] = mapped_column(String(80))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)


class MachineRecord(Base):
    __tablename__ = "machines"
    machine_id: Mapped[str] = mapped_column(String(6), primary_key=True)
    machine_class: Mapped[str] = mapped_column(String(40))
    powertrain: Mapped[str] = mapped_column(String(20))
    site_id: Mapped[str] = mapped_column(String(3), index=True)
    primary_operator_id: Mapped[str | None] = mapped_column(String(6), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)


class OperatorRecord(Base):
    __tablename__ = "operators"
    operator_id: Mapped[str] = mapped_column(String(6), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    home_site_id: Mapped[str] = mapped_column(String(3))
    experience_years: Mapped[float] = mapped_column(Float, default=0)
    certifications: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)


class AlertRecord(Base):
    __tablename__ = "alerts"
    alert_id: Mapped[str] = mapped_column(String(7), primary_key=True)
    alert_code: Mapped[str] = mapped_column(String(60), index=True)
    severity: Mapped[str] = mapped_column(String(20))
    site_id: Mapped[str] = mapped_column(String(3), index=True)
    machine_id: Mapped[str] = mapped_column(String(6), index=True)
    operator_id: Mapped[str | None] = mapped_column(String(6), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_min: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)


class TelemetryRecord(Base):
    __tablename__ = "telemetry"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic: Mapped[str] = mapped_column(String(160), index=True)
    schema_version: Mapped[str] = mapped_column(String(20))
    payload_json: Mapped[str] = mapped_column(Text)
    received_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, index=True)


def init_db() -> None:
    if os.getenv("AUTO_CREATE_SCHEMA", "true").lower() == "true":
        Base.metadata.create_all(engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
