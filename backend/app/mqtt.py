from __future__ import annotations

import json
import os
from collections.abc import Callable
from typing import Any

import paho.mqtt.client as mqtt


class MQTTIngestService:
    telemetry_pattern = "site/+/machine/+/telemetry"
    alert_pattern = "site/+/machine/+/alerts"

    def __init__(self, on_message: Callable[[str, dict[str, Any]], None]) -> None:
        self.host = os.getenv("MQTT_HOST", "localhost")
        self.port = int(os.getenv("MQTT_PORT", "1883"))
        self.on_message = on_message
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

    def _on_connect(self, client: mqtt.Client, userdata: Any, flags: dict[str, Any], reason_code: Any, properties: Any = None) -> None:
        if reason_code == 0:
            client.subscribe([(self.telemetry_pattern, 1), (self.alert_pattern, 1)])

    def _on_message(self, client: mqtt.Client, userdata: Any, message: mqtt.MQTTMessage) -> None:
        try:
            payload = json.loads(message.payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return
        if isinstance(payload, dict) and payload.get("schema_version"):
            self.on_message(message.topic, payload)

    def start(self) -> None:
        self.client.connect_async(self.host, self.port)
        self.client.loop_start()

    def stop(self) -> None:
        self.client.loop_stop()
        self.client.disconnect()
