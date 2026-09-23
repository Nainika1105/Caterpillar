"""
Ingest Service — Phase 1 Member 2 deliverable (scaffold)

Subscribes to MQTT topics (telemetry + alerts), validates, writes to database.
"""

import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime

import paho.mqtt.client as mqtt
import psycopg2
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
        # Subscribe to telemetry and alert topics
        client.subscribe("site/+/machine/+/telemetry")
        client.subscribe("site/+/machine/+/alerts")
    else:
        logger.error(f"✗ MQTT connection failed with code {rc}")


def on_mqtt_message(client, userdata, msg):
    """MQTT message callback"""
    try:
        topic = msg.topic
        payload = json.loads(msg.payload.decode('utf-8'))

        if "telemetry" in topic:
            handle_telemetry(payload)
        elif "alerts" in topic:
            handle_alert(payload)

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON from {msg.topic}: {e}")
        stats["validation_errors"] += 1
    except Exception as e:
        logger.error(f"Error processing message from {msg.topic}: {e}")
        stats["db_errors"] += 1


def handle_telemetry(payload: dict):
    """
    Process telemetry message
    TODO: Member 1 fills this in with actual DB insertion
    """
    stats["telemetry_received"] += 1

    # Validate structure
    required_fields = [
        "timestamp", "site_id", "machine_id", "state",
        "engine_rpm", "ground_speed_kmh", "fuel_level_pct"
    ]

    if not all(field in payload for field in required_fields):
        logger.warning(f"Missing required fields in telemetry: {payload.get('machine_id')}")
        stats["validation_errors"] += 1
        return

    # TODO: Write to TimescaleDB telemetry table
    # logger.debug(f"Would write telemetry: {payload['machine_id']} @ {payload['timestamp']}")
    stats["telemetry_stored"] += 1

    # TODO: Publish to Redis stream for ML models
    # redis_conn.xadd('telemetry_stream', payload)


def handle_alert(payload: dict):
    """
    Process alert message
    TODO: Member 1 fills this in with actual DB insertion
    """
    stats["alerts_received"] += 1

    # Validate structure
    required_fields = ["alert_id", "timestamp", "machine_id", "rule", "severity"]

    if not all(field in payload for field in required_fields):
        logger.warning(f"Missing required fields in alert")
        stats["validation_errors"] += 1
        return

    # TODO: Write to PostgreSQL alerts table
    # logger.info(f"Alert: {payload['rule']} on {payload['machine_id']}")
    stats["alerts_stored"] += 1

    # TODO: Publish to Redis queue for WebSocket broadcast
    # redis_conn.lpush('alerts_queue', json.dumps(payload))


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


@app.get("/stats")
async def get_stats():
    """Get ingest statistics"""
    return stats


@app.post("/test/publish-telemetry")
async def test_publish_telemetry(payload: dict):
    """
    Test endpoint: simulate a telemetry message
    curl -X POST http://localhost:8002/test/publish-telemetry \
      -H "Content-Type: application/json" \
      -d '{
        "timestamp": "2025-05-01T08:00:00Z",
        "site_id": "S01",
        "machine_id": "BH001",
        "operator_id": "OP1011",
        "task_id": "T00028",
        "state": "idle",
        "power_on": true,
        "operator_present": true,
        "seatbelt_status": "Fastened",
        "engine_rpm": 882.0,
        "ground_speed_kmh": 0.0,
        "fuel_level_pct": 86.7,
        "battery_soc_pct": null,
        "fuel_rate_lph": 1.36,
        "power_kw": null,
        "energy_used": 0.023,
        "hydraulic_pressure_bar": 21,
        "hydraulic_oil_temp_c": 37.9,
        "coolant_temp_c": 41.0,
        "load_cycles": 0,
        "proximity_min_m": 20.0,
        "proximity_zone": "clear",
        "harsh_events": 0,
        "ambient_temp_c": 32.4,
        "rain_mm_hr": 0.0,
        "engine_hours": 2210.52
      }'
    """
    handle_telemetry(payload)
    return {"status": "processed", "stats": stats}


@app.post("/test/publish-alert")
async def test_publish_alert(payload: dict):
    """
    Test endpoint: simulate an alert message
    curl -X POST http://localhost:8002/test/publish-alert \
      -H "Content-Type: application/json" \
      -d '{
        "alert_id": "AL00042",
        "timestamp": "2025-05-01T12:35:15Z",
        "machine_id": "BH001",
        "operator_id": "OP1011",
        "site_id": "S01",
        "rule": "UNBELTED_WHILE_MOVING",
        "severity": "critical",
        "message": "Seatbelt unfastened while moving at 25 km/h",
        "data": {"speed_kmh": 25.0}
      }'
    """
    handle_alert(payload)
    return {"status": "processed", "stats": stats}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
