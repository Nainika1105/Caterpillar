"""
Ingest Service — Phase 1 Member 1 deliverable

Subscribes to MQTT topics (telemetry + alerts), validates, writes to database.
"""

import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime

import paho.mqtt.client as mqtt
import psycopg2
import psycopg2.extensions
import redis
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

load_dotenv()

# Configuration
MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_NAME = os.getenv("DB_NAME", "caterpillar")
DB_USER = os.getenv("DB_USER", "admin")
DB_PASSWORD = os.getenv("DB_PASSWORD", "admin123")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Logging
logging.basicConfig(level=getattr(logging, LOG_LEVEL))
logger = logging.getLogger(__name__)

# Global state
mqtt_client = None
db_conn = None
redis_conn = None
stats = {
    "telemetry_received": 0,
    "alerts_received": 0,
    "telemetry_stored": 0,
    "alerts_stored": 0,
    "validation_errors": 0,
    "db_errors": 0,
}


class HealthResponse(BaseModel):
    status: str
    mqtt_connected: bool
    db_connected: bool
    redis_connected: bool
    stats: dict


def on_mqtt_connect(client, userdata, flags, rc):
    """MQTT connect callback"""
    if rc == 0:
        logger.info("✓ Connected to MQTT broker")
        client.subscribe("site/+/machine/+/telemetry")
        client.subscribe("site/+/machine/+/alerts")
    else:
        logger.error(f"✗ MQTT connection failed with code {rc}")


def on_mqtt_message(client, userdata, msg):
    """MQTT message callback"""
    with open('/tmp/mqtt_debug.txt', 'a') as f:
        f.write(f"MQTT: {msg.topic}\n")
    try:
        topic = msg.topic
        payload = json.loads(msg.payload.decode('utf-8'))

        if "telemetry" in topic:
            handle_telemetry(payload)
        elif "alerts" in topic:
            logger.info(f"[ALERT] Received: {payload.get('rule')}")
            handle_alert(payload)

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON from {msg.topic}: {e}")
        stats["validation_errors"] += 1
    except Exception as e:
        logger.error(f"Error processing message from {msg.topic}: {e}")
        stats["db_errors"] += 1


def handle_telemetry(payload: dict):
    """Write telemetry to TimescaleDB"""
    stats["telemetry_received"] += 1
    # DEBUG: Write to file to prove function is called
    with open('/tmp/telemetry_debug.txt', 'a') as f:
        f.write(f"{payload.get('machine_id')} @ {payload.get('timestamp')}\n")

    required_fields = [
        "timestamp", "site_id", "machine_id", "state",
        "engine_rpm", "ground_speed_kmh", "fuel_level_pct"
    ]

    if not all(field in payload for field in required_fields):
        logger.warning(f"Missing fields: {payload.get('machine_id')}")
        stats["validation_errors"] += 1
        return

    try:
        logger.info(f"[TELEMETRY] Inserting for {payload.get('machine_id')}")
        # Fresh connection for thread safety (MQTT callbacks run in separate thread)
        conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT, database=DB_NAME,
            user=DB_USER, password=DB_PASSWORD, connect_timeout=5
        )
        conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO telemetry (
                timestamp, site_id, machine_id, operator_id, task_id, state,
                power_on, operator_present, seatbelt_status, engine_rpm,
                ground_speed_kmh, fuel_level_pct, battery_soc_pct, fuel_rate_lph,
                power_kw, energy_used, hydraulic_pressure_bar, hydraulic_oil_temp_c,
                coolant_temp_c, load_cycles, proximity_min_m, proximity_zone,
                harsh_events, ambient_temp_c, rain_mm_hr, engine_hours,
                anomaly_id, anomaly_type
            ) VALUES (
                %(timestamp)s, %(site_id)s, %(machine_id)s, %(operator_id)s,
                %(task_id)s, %(state)s, %(power_on)s, %(operator_present)s,
                %(seatbelt_status)s, %(engine_rpm)s, %(ground_speed_kmh)s,
                %(fuel_level_pct)s, %(battery_soc_pct)s, %(fuel_rate_lph)s,
                %(power_kw)s, %(energy_used)s, %(hydraulic_pressure_bar)s,
                %(hydraulic_oil_temp_c)s, %(coolant_temp_c)s, %(load_cycles)s,
                %(proximity_min_m)s, %(proximity_zone)s, %(harsh_events)s,
                %(ambient_temp_c)s, %(rain_mm_hr)s, %(engine_hours)s,
                %(anomaly_id)s, %(anomaly_type)s
            )
        """, payload)
        cursor.close()
        conn.close()
        stats["telemetry_stored"] += 1
        if stats["telemetry_stored"] % 50 == 0:
            logger.info(f"✓ {stats['telemetry_stored']} rows")
    except Exception as e:
        logger.error(f"DB error: {e}", exc_info=True)
        stats["db_errors"] += 1


def handle_alert(payload: dict):
    """Write alert to PostgreSQL"""
    stats["alerts_received"] += 1

    required_fields = ["alert_id", "timestamp", "machine_id", "rule", "severity"]

    if not all(field in payload for field in required_fields):
        logger.warning(f"Missing fields in alert")
        stats["validation_errors"] += 1
        return

    try:
        conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT, database=DB_NAME,
            user=DB_USER, password=DB_PASSWORD, connect_timeout=5
        )
        conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        # Convert data dict to JSON string for JSONB column
        data_json = json.dumps(payload.get('data', {}))

        cursor.execute("""
            INSERT INTO alerts (
                alert_id, timestamp, machine_id, operator_id, site_id,
                rule, severity, message, data, acknowledged
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, FALSE)
        """, (
            payload.get('alert_id'),
            payload.get('timestamp'),
            payload.get('machine_id'),
            payload.get('operator_id'),
            payload.get('site_id'),
            payload.get('rule'),
            payload.get('severity'),
            payload.get('message'),
            data_json
        ))
        cursor.close()
        conn.close()
        stats["alerts_stored"] += 1
        logger.info(f"Alert: {payload['rule']}")
    except Exception as e:
        logger.error(f"DB error: {e}", exc_info=True)
        stats["db_errors"] += 1


def connect_db():
    """Connect to PostgreSQL"""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            connect_timeout=5
        )
        conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        logger.info("✓ Connected to PostgreSQL")
        return conn
    except Exception as e:
        logger.error(f"✗ Database connection failed: {e}")
        return None


def connect_redis():
    """Connect to Redis"""
    try:
        conn = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            decode_responses=True,
            socket_connect_timeout=5
        )
        conn.ping()
        logger.info("✓ Connected to Redis")
        return conn
    except Exception as e:
        logger.error(f"✗ Redis connection failed: {e}")
        return None


def connect_mqtt():
    """Connect to MQTT broker"""
    try:
        client = mqtt.Client()
        client.on_connect = on_mqtt_connect
        client.on_message = on_mqtt_message
        client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
        client.loop_start()
        logger.info("✓ MQTT client started")
        return client
    except Exception as e:
        logger.error(f"✗ MQTT connection failed: {e}")
        return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global mqtt_client, db_conn, redis_conn

    # Startup
    logger.info("Ingest service starting...")
    mqtt_client = connect_mqtt()
    db_conn = connect_db()
    redis_conn = connect_redis()

    yield

    # Shutdown
    logger.info("Ingest service shutting down...")
    if mqtt_client:
        mqtt_client.loop_stop()
    if db_conn:
        db_conn.close()
    if redis_conn:
        redis_conn.close()


# FastAPI app
app = FastAPI(
    title="Caterpillar Ingest Service",
    description="Consumes telemetry and alerts from MQTT, stores in database",
    version="0.1.0",
    lifespan=lifespan
)


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy" if all([mqtt_client, db_conn, redis_conn]) else "degraded",
        mqtt_connected=mqtt_client is not None,
        db_connected=db_conn is not None,
        redis_connected=redis_conn is not None,
        stats=stats
    )


@app.get("/telemetry/latest")
async def latest_telemetry(machine_id: str):
    """Return the newest stored telemetry row using the shared frontend field names."""
    conn = connect_db()
    if conn is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT timestamp, site_id, machine_id, operator_id, task_id, state,
                   power_on, operator_present, seatbelt_status, engine_rpm,
                   ground_speed_kmh, fuel_level_pct, battery_soc_pct, fuel_rate_lph,
                   power_kw, energy_used, hydraulic_pressure_bar, hydraulic_oil_temp_c,
                   coolant_temp_c, load_cycles, proximity_min_m, proximity_zone,
                   harsh_events, ambient_temp_c, rain_mm_hr, engine_hours
            FROM telemetry
            WHERE machine_id = %s
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            (machine_id,),
        )
        row = cursor.fetchone()
        columns = [description[0] for description in cursor.description] if cursor.description else []
        cursor.close()
        if row is None:
            raise HTTPException(status_code=404, detail="Telemetry not found")
        payload = dict(zip(columns, row))
        payload["is_power_on"] = payload.pop("power_on")
        payload["is_operator_present"] = payload.pop("operator_present")
        payload["seatbelt_status"] = str(payload["seatbelt_status"]).lower()
        energy_used = payload.pop("energy_used")
        payload["fuel_used_l"] = energy_used if payload.get("fuel_level_pct") is not None else None
        payload["energy_used_kwh"] = energy_used if payload.get("battery_soc_pct") is not None else None
        payload["timestamp"] = payload["timestamp"].isoformat() + "Z" if hasattr(payload["timestamp"], "isoformat") else payload["timestamp"]
        return payload
    finally:
        conn.close()


@app.get("/stats")
async def get_stats():
    """Get ingest statistics"""
    return stats


@app.post("/test/publish-telemetry")
async def test_publish_telemetry(payload: dict):
    """Test endpoint: simulate a telemetry message"""
    handle_telemetry(payload)
    return {"status": "processed", "stats": stats}


@app.post("/test/publish-alert")
async def test_publish_alert(payload: dict):
    """Test endpoint: simulate an alert message"""
    handle_alert(payload)
    return {"status": "processed", "stats": stats}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
