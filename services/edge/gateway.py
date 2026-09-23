"""
Edge Gateway — Phase 2 Member 1 deliverable

Subscribes to MQTT telemetry, evaluates rules locally, publishes alerts.
Stores offline when disconnected. Voice alerts on critical events.
"""

import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import Dict, Optional

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

from rule_engine import RuleEngine, RuleAlert
from offline_buffer import OfflineBuffer
from voice_alerts import VoiceAlertSystem

load_dotenv()

# Configuration
MQTT_HOST = os.getenv("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MACHINE_ID = os.getenv("MACHINE_ID", "BH001")
SITE_ID = os.getenv("SITE_ID", "S01")
OPERATOR_ID = os.getenv("OPERATOR_ID", "OP1011")
RULES_FILE = os.getenv("RULES_FILE", "rules.yaml")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Logging
logging.basicConfig(level=getattr(logging, LOG_LEVEL))
logger = logging.getLogger(__name__)

# Global state
mqtt_client = None
rule_engine = None
offline_buffer = None
voice_system = None
stats = {
    "telemetry_received": 0,
    "rules_evaluated": 0,
    "alerts_fired": 0,
    "alerts_published": 0,
    "alerts_buffered": 0,
    "voice_alerts": 0,
}


def on_mqtt_connect(client, userdata, flags, rc):
    """MQTT connect callback"""
    if rc == 0:
        logger.info(f"✓ Edge gateway connected to {MQTT_HOST}:{MQTT_PORT}")
        # Subscribe to telemetry for this machine
        topic = f"site/{SITE_ID}/machine/{MACHINE_ID}/telemetry"
        client.subscribe(topic)
        logger.info(f"Subscribed to {topic}")
    else:
        logger.error(f"✗ MQTT connection failed with code {rc}")


def on_mqtt_disconnect(client, userdata, rc):
    """MQTT disconnect callback"""
    if rc != 0:
        logger.warning(f"Unexpected MQTT disconnect: {rc}")
    else:
        logger.info("Disconnected from MQTT")


def on_mqtt_message(client, userdata, msg):
    """MQTT message callback - handle incoming telemetry"""
    try:
        topic = msg.topic
        payload = json.loads(msg.payload.decode('utf-8'))

        if "telemetry" in topic:
            handle_telemetry(payload, client)

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON: {e}")
    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)


def handle_telemetry(telemetry: Dict, mqtt_client):
    """
    Evaluate telemetry against rules.
    Publish alerts if rules fire.
    Store locally if disconnected.
    """
    stats["telemetry_received"] += 1

    try:
        # Evaluate rules
        alerts = rule_engine.evaluate(telemetry, OPERATOR_ID)
        stats["rules_evaluated"] += 1

        if alerts:
            stats["alerts_fired"] += len(alerts)

            for alert in alerts:
                handle_alert(alert, mqtt_client)

    except Exception as e:
        logger.error(f"Error evaluating rules: {e}", exc_info=True)


def handle_alert(alert: RuleAlert, mqtt_client):
    """
    Publish alert to MQTT.
    Store locally if disconnected.
    Play voice alert if configured.
    """
    alert_dict = {
        "alert_id": alert.alert_id,
        "timestamp": alert.timestamp,
        "machine_id": alert.machine_id,
        "operator_id": alert.operator_id,
        "site_id": alert.site_id,
        "rule": alert.rule,
        "severity": alert.severity,
        "message": alert.message,
        "data": {}
    }

    try:
        # Try to publish to MQTT
        topic = f"site/{SITE_ID}/machine/{MACHINE_ID}/alerts"
        payload = json.dumps(alert_dict)

        result = mqtt_client.publish(topic, payload, qos=1, retain=False)

        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            stats["alerts_published"] += 1
            logger.warning(f"ALERT PUBLISHED: {alert.rule} - {alert.message}")
        else:
            # Store locally if publish failed
            offline_buffer.store_alert(alert_dict)
            stats["alerts_buffered"] += 1
            logger.warning(f"ALERT BUFFERED (offline): {alert.rule}")

    except Exception as e:
        logger.error(f"Error publishing alert: {e}")
        offline_buffer.store_alert(alert_dict)
        stats["alerts_buffered"] += 1

    # Voice alert for critical rules
    if alert.voice_alert:
        try:
            voice_system.play_alert(alert.message)
            stats["voice_alerts"] += 1
            logger.info(f"🔊 Voice alert: {alert.message}")
        except Exception as e:
            logger.error(f"Voice alert failed: {e}")


def alert_callback(alert: RuleAlert):
    """Called when rule engine fires an alert"""
    logger.warning(f"Rule callback: {alert.rule}")
    # Alerts are handled via MQTT publish in handle_alert


def voice_callback(message: str):
    """Called when rule engine wants voice alert"""
    try:
        voice_system.play_alert(message)
        stats["voice_alerts"] += 1
    except Exception as e:
        logger.error(f"Voice callback failed: {e}")


def connect_mqtt():
    """Connect to MQTT broker"""
    try:
        client = mqtt.Client()
        client.on_connect = on_mqtt_connect
        client.on_disconnect = on_mqtt_disconnect
        client.on_message = on_mqtt_message

        client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
        client.loop_start()

        logger.info("✓ MQTT client started")
        return client
    except Exception as e:
        logger.error(f"✗ MQTT connection failed: {e}")
        return None


def get_stats() -> Dict:
    """Get gateway statistics"""
    return {
        "status": "running",
        "machine_id": MACHINE_ID,
        "site_id": SITE_ID,
        "operator_id": OPERATOR_ID,
        "stats": stats,
        "buffer_stats": offline_buffer.get_stats() if offline_buffer else {},
        "rule_engine_stats": rule_engine.get_stats() if rule_engine else {}
    }


def main():
    """Main edge gateway loop"""
    global mqtt_client, rule_engine, offline_buffer, voice_system

    logger.info("=" * 60)
    logger.info("Edge Gateway Starting")
    logger.info(f"Machine: {MACHINE_ID}, Site: {SITE_ID}, Operator: {OPERATOR_ID}")
    logger.info("=" * 60)

    try:
        # Initialize components
        offline_buffer = OfflineBuffer(db_path=f"/tmp/{MACHINE_ID}_buffer.db")
        logger.info(f"✓ Offline buffer initialized")

        rule_engine = RuleEngine(RULES_FILE, MACHINE_ID, SITE_ID)
        rule_engine.register_alert_callback(alert_callback)
        rule_engine.register_voice_callback(voice_callback)
        logger.info(f"✓ Rule engine initialized with {len(rule_engine.rules)} rules")

        voice_system = VoiceAlertSystem()
        logger.info(f"✓ Voice system initialized")

        mqtt_client = connect_mqtt()
        if not mqtt_client:
            logger.error("Failed to connect to MQTT")
            return False

        # Wait for connection
        time.sleep(1)

        # Main loop
        logger.info("Edge gateway running. Press Ctrl+C to stop.")
        while True:
            time.sleep(5)

            # Periodically print stats
            stats_snapshot = get_stats()
            logger.info(f"Stats: {stats_snapshot['stats']}")

    except KeyboardInterrupt:
        logger.info("Shutdown signal received")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return False
    finally:
        if mqtt_client:
            mqtt_client.loop_stop()
            mqtt_client.disconnect()
        logger.info("Edge gateway stopped")

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
