#!/usr/bin/env python3
"""
Telemetry Simulator — Phase 1 Member 1 deliverable

Replays telemetry_1min.csv to MQTT at configurable speed.
Publishes to: site/{site_id}/machine/{machine_id}/telemetry
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import paho.mqtt.client as mqtt
from dotenv import load_dotenv
from pydantic import BaseModel, field_validator

load_dotenv()

# Configuration
MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
DATA_DIR = Path(os.getenv("DATA_DIR", "./data"))
PLAYBACK_SPEED = float(os.getenv("PLAYBACK_SPEED", "1.0"))  # 1.0 = real-time, 60 = 60x faster
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Log configuration
logger.info(f"Configuration: MQTT_HOST={MQTT_HOST}, PLAYBACK_SPEED={PLAYBACK_SPEED}x")


class TelemetryMessage(BaseModel):
    """Validates against telemetry_message.json schema"""
    timestamp: str
    site_id: str
    machine_id: str
    operator_id: str | None
    task_id: str | None
    state: str
    power_on: bool
    operator_present: bool
    seatbelt_status: str
    engine_rpm: float | None
    ground_speed_kmh: float | None
    fuel_level_pct: float | None
    battery_soc_pct: float | None
    fuel_rate_lph: float | None
    power_kw: float | None
    energy_used: float | None
    hydraulic_pressure_bar: float | None
    hydraulic_oil_temp_c: float | None
    coolant_temp_c: float | None
    load_cycles: int | None
    proximity_min_m: float | None
    proximity_zone: str
    harsh_events: int | None
    ambient_temp_c: float | None
    rain_mm_hr: float | None
    engine_hours: float | None
    anomaly_id: str | None = None
    anomaly_type: str | None = None

    @field_validator('timestamp', mode='before')
    @classmethod
    def validate_timestamp(cls, v):
        if isinstance(v, str):
            # Convert "2025-05-01 08:00:00" to ISO format
            return datetime.fromisoformat(v.replace(' ', 'T')).isoformat() + 'Z'
        return v

    def dict(self, **kwargs):
        """Override to handle datetime serialization"""
        data = super().model_dump(**kwargs)
        # Handle None values - keep them as null in JSON
        return data


class SimulatorMQTT:
    def __init__(self):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_publish = self.on_publish
        self.connected = False
        self.published_count = 0
        self.skipped_count = 0
        self.error_count = 0

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("✓ Connected to MQTT broker")
            self.connected = True
        else:
            logger.error(f"✗ Connection failed with code {rc}")
            self.connected = False

    def on_disconnect(self, client, userdata, rc):
        self.connected = False
        if rc != 0:
            logger.warning(f"Disconnected with code {rc}")

    def on_publish(self, client, userdata, mid):
        pass

    def connect(self):
        try:
            self.client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
            self.client.loop_start()
            # Wait for connection (up to 3 seconds)
            import time
            for _ in range(30):
                if self.connected:
                    return True
                time.sleep(0.1)
            logger.error("Failed to connect to MQTT after 3 seconds")
            return False
        except Exception as e:
            logger.error(f"Connection error: {e}")
            return False

    def publish_telemetry(self, row: pd.Series) -> bool:
        """Publish one telemetry row to MQTT"""
        try:
            site_id = str(row['site_id'])
            machine_id = str(row['machine_id'])
            topic = f"site/{site_id}/machine/{machine_id}/telemetry"

            # Convert row to dict, handling NaN values
            data = {}
            for key, val in row.items():
                if pd.isna(val):
                    data[key] = None
                elif isinstance(val, (int, float)):
                    data[key] = float(val) if not isinstance(val, int) else int(val)
                else:
                    data[key] = str(val)

            # Validate against schema
            msg = TelemetryMessage(**data)
            payload = json.dumps(msg.model_dump(exclude_none=False))

            result = self.client.publish(topic, payload, qos=1)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                self.published_count += 1
                return True
            else:
                logger.warning(f"Publish failed for {machine_id}: {result.rc}")
                self.error_count += 1
                return False

        except Exception as e:
            logger.error(f"Error publishing row: {e}")
            self.error_count += 1
            return False

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()


def load_telemetry_data(csv_path: Path) -> pd.DataFrame:
    """Load telemetry CSV with proper dtypes"""
    logger.info(f"Loading telemetry from {csv_path}")
    df = pd.read_csv(csv_path)
    logger.info(f"Loaded {len(df)} rows, {len(df.groupby('machine_id'))} machines")
    return df


async def replay_telemetry(sim: SimulatorMQTT, df: pd.DataFrame):
    """
    Replay telemetry at PLAYBACK_SPEED
    PLAYBACK_SPEED = 1.0 means real-time (1 minute per message takes 1 minute)
    PLAYBACK_SPEED = 60 means 60x faster (1 minute per message takes 1 second)
    """
    logger.info(f"Starting replay at {PLAYBACK_SPEED}x speed")

    if df.empty:
        logger.error("No data to replay")
        return

    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp')

    start_time = df['timestamp'].iloc[0]
    end_time = df['timestamp'].iloc[-1]
    total_duration = end_time - start_time

    logger.info(f"Replay window: {start_time} to {end_time}")
    logger.info(f"Total duration: {total_duration}")

    replay_start = datetime.now()
    message_count = 0

    for idx, row in df.iterrows():
        # Calculate expected elapsed time
        elapsed = row['timestamp'] - start_time
        expected_elapsed = elapsed.total_seconds() / PLAYBACK_SPEED

        # Sleep until we're at the right time
        actual_elapsed = (datetime.now() - replay_start).total_seconds()
        if expected_elapsed > actual_elapsed:
            await asyncio.sleep(expected_elapsed - actual_elapsed)

        # Publish
        if sim.publish_telemetry(row):
            message_count += 1

            if message_count % 100 == 0:
                logger.info(f"Published {message_count} messages ({row['timestamp']})")

    logger.info(f"✓ Replay complete: {message_count} published, {sim.error_count} errors")


async def main():
    """Main entry point"""
    logger.info("Caterpillar Telemetry Simulator starting...")

    # Connect to MQTT
    sim = SimulatorMQTT()
    if not sim.connect():
        logger.error("Failed to connect to MQTT broker")
        return

    # Load data
    csv_path = DATA_DIR / "telemetry_1min.csv"
    if not csv_path.exists():
        logger.error(f"Data file not found: {csv_path}")
        sim.disconnect()
        return

    df = load_telemetry_data(csv_path)

    # Run replay
    try:
        await replay_telemetry(sim, df)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        sim.disconnect()
        logger.info("Simulator stopped")


if __name__ == "__main__":
    asyncio.run(main())
