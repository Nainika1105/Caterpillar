"""
Edge Rule Engine - Phase 2 Member 1 deliverable

Evaluates safety rules locally on the machine with millisecond latency.
No network dependency for critical safety rules.
"""

import time
import logging
from datetime import datetime
from typing import Dict, List, Callable
from dataclasses import dataclass
import threading
import yaml

logger = logging.getLogger(__name__)


@dataclass
class RuleAlert:
    """Alert fired by rule engine"""
    alert_id: str
    timestamp: str
    machine_id: str
    operator_id: str
    site_id: str
    rule: str
    severity: str  # critical, warning, info
    message: str
    voice_alert: bool
    should_log_incident: bool


class RuleEngine:
    """Evaluates telemetry against safety rules"""

    def __init__(self, rules_file: str, machine_id: str, site_id: str):
        self.machine_id = machine_id
        self.site_id = site_id
        self.rules = self._load_rules(rules_file)
        self.alert_callbacks: List[Callable[[RuleAlert], None]] = []
        self.voice_callback: Callable[[str], None] = None
        self.last_alert_time: Dict[str, float] = {}  # Prevent alert spam
        self.alert_counter = 0

        logger.info(f"Rule engine initialized for {machine_id} with {len(self.rules)} rules")

    def _load_rules(self, rules_file: str) -> Dict:
        """Load rules from YAML configuration"""
        with open(rules_file, 'r') as f:
            config = yaml.safe_load(f)
        return config['rules']

    def register_alert_callback(self, callback: Callable[[RuleAlert], None]):
        """Register callback for alerts"""
        self.alert_callbacks.append(callback)

    def register_voice_callback(self, callback: Callable[[str], None]):
        """Register callback for voice alerts"""
        self.voice_callback = callback

    def evaluate(self, telemetry: Dict, operator_id: str) -> List[RuleAlert]:
        """
        Evaluate telemetry against all rules
        Returns list of fired alerts
        """
        alerts = []
        current_time = datetime.utcnow().isoformat() + 'Z'

        for rule in self.rules:
            if self._check_conditions(rule['condition'], telemetry):
                # Rule fired - check if we should throttle (prevent spam)
                rule_name = rule['name']
                last_time = self.last_alert_time.get(rule_name, 0)

                # Throttle: don't alert more than once per 30 seconds for same rule
                if time.time() - last_time < 30:
                    continue

                self.last_alert_time[rule_name] = time.time()
                self.alert_counter += 1

                # Create alert
                alert = RuleAlert(
                    alert_id=f"AL{self.alert_counter:05d}",
                    timestamp=current_time,
                    machine_id=self.machine_id,
                    operator_id=operator_id,
                    site_id=self.site_id,
                    rule=rule_name,
                    severity=rule['severity'],
                    message=rule['action'][0]['alert'],  # First action is the message
                    voice_alert=rule['action'][1]['voice'],
                    should_log_incident=any(
                        a.get('log_incident') for a in rule['action']
                    )
                )

                alerts.append(alert)
                logger.warning(f"RULE FIRED: {rule_name} - {alert.message}")

                # Trigger callbacks
                for callback in self.alert_callbacks:
                    callback(alert)

                # Voice alert
                if alert.voice_alert and self.voice_callback:
                    self.voice_callback(alert.message)

        return alerts

    def _check_conditions(self, conditions: List[Dict], telemetry: Dict) -> bool:
        """Check if all conditions are met"""
        for condition in conditions:
            for key, value in condition.items():
                tel_value = telemetry.get(key)

                if not self._compare_condition(tel_value, value):
                    return False

        return True

    def _compare_condition(self, telemetry_value, condition_value) -> bool:
        """Compare a single condition"""
        if isinstance(condition_value, str):
            if condition_value == "is not null":
                return telemetry_value is not None
            elif condition_value.startswith(">"):
                threshold = float(condition_value[1:].strip())
                return telemetry_value > threshold if telemetry_value else False
            elif condition_value.startswith("<"):
                threshold = float(condition_value[1:].strip())
                return telemetry_value < threshold if telemetry_value else False
            elif condition_value.startswith("=="):
                expected = condition_value[2:].strip()
                return str(telemetry_value) == expected
            else:
                # Exact match
                return telemetry_value == condition_value

        elif isinstance(condition_value, list):
            # Any match in list (OR)
            return telemetry_value in condition_value

        else:
            return telemetry_value == condition_value

    def get_stats(self) -> Dict:
        """Get rule engine statistics"""
        return {
            "rules_loaded": len(self.rules),
            "alerts_fired": self.alert_counter,
            "last_alert_times": self.last_alert_time.copy()
        }


class RuleEvaluator(threading.Thread):
    """
    Runs rule engine in background thread
    Evaluates telemetry at configured intervals
    """

    def __init__(self, rule_engine: RuleEngine, telemetry_queue, operator_id: str):
        super().__init__(daemon=True)
        self.rule_engine = rule_engine
        self.telemetry_queue = telemetry_queue
        self.operator_id = operator_id
        self.running = True

    def run(self):
        """Main evaluation loop"""
        logger.info("Rule evaluator started")

        while self.running:
            try:
                # Get latest telemetry (non-blocking)
                telemetry = self.telemetry_queue.get_nowait()

                # Evaluate rules
                alerts = self.rule_engine.evaluate(telemetry, self.operator_id)

                # Process alerts (publish to MQTT, log, etc.)
                for alert in alerts:
                    self._handle_alert(alert)

            except Exception as e:
                logger.error(f"Error evaluating rules: {e}")

            # Sleep based on rule severity (100ms for critical rules)
            time.sleep(0.1)

    def _handle_alert(self, alert: RuleAlert):
        """Handle fired alert"""
        logger.warning(f"Alert: {alert.rule} - {alert.message}")
        # TODO: Publish to MQTT alerts topic

    def stop(self):
        """Stop evaluation loop"""
        self.running = False


if __name__ == "__main__":
    # Test the rule engine
    logging.basicConfig(level=logging.INFO)

    engine = RuleEngine(
        rules_file="rules.yaml",
        machine_id="BH001",
        site_id="S01"
    )

    # Test telemetry
    test_telemetry = {
        "seatbelt_status": "Unfastened",
        "ground_speed_kmh": 10.0,
        "proximity_min_m": 5.0,
        "power_on": True,
        "operator_present": True,
        "coolant_temp_c": 80.0,
        "fuel_level_pct": 50.0,
        "harsh_events": 2
    }

    alerts = engine.evaluate(test_telemetry, "OP1011")
    print(f"Fired {len(alerts)} alerts")
    for alert in alerts:
        print(f"  - {alert.rule}: {alert.message}")
