# MQTT Message Contract

**Status**: Interface contract for Phase 1+  
**Owner**: Member 1 (Edge & Data)  
**Agreed**: [To be dated on day 1 when team signs off]

## Overview

This document defines the MQTT message format and topic structure that flows from the edge gateway and simulator to the ingestion service. All downstream systems (Members 2, 3, 4) depend on this contract.

## Topics

### Telemetry Topic
**Topic**: `site/{site_id}/machine/{machine_id}/telemetry`

**Message Format**: JSON, one message per minute per machine  
**Frequency**: 1 Hz during Phase 0/1 testing (simulator can be faster for demo)  
**Schema**: See `telemetry_message.json`

**Example**:
```
Topic: site/S01/machine/BH001/telemetry
{
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
  "engine_hours": 2210.52,
  "anomaly_id": null,
  "anomaly_type": null
}
```

### Alert Topic
**Topic**: `site/{site_id}/machine/{machine_id}/alerts`

**Message Format**: JSON, one message per alert event  
**Schema**: See `alert_message.json`

**Example**:
```
Topic: site/S01/machine/BH001/alerts
{
  "alert_id": "AL00042",
  "timestamp": "2025-05-01T12:35:15Z",
  "machine_id": "BH001",
  "operator_id": "OP1011",
  "site_id": "S01",
  "rule": "UNBELTED_WHILE_MOVING",
  "severity": "critical",
  "message": "Seatbelt unfastened while moving at 25 km/h",
  "data": {
    "speed_kmh": 25.0
  }
}
```

## Data Flow

1. **Simulator** (Phase 1):
   - Replays `telemetry_1min.csv` to telemetry topic
   - Can accelerate playback for demos (e.g., 1 day per second)
   - Publishes to Mosquitto broker on `localhost:1883` during dev

2. **Edge Gateway** (Phase 2):
   - Runs locally in-cab (simulated as a service during Phase 1/2)
   - Evaluates rules engine on each telemetry message
   - Publishes alerts to alerts topic
   - Maintains offline buffer of telemetry when network drops

3. **Ingestion Service** (Phase 1, Member 2):
   - Subscribes to `site/+/machine/+/telemetry`
   - Subscribes to `site/+/machine/+/alerts`
   - Validates against JSON schemas
   - Writes to TimescaleDB and Redis queue
   - **Must not modify message content**

## Guarantees

- **At-least-once delivery**: Ingestion service handles duplicate messages (use alert_id + timestamp for dedup)
- **Order within a machine**: Telemetry messages for a single machine are ordered by timestamp
- **JSON strict**: All strings are UTF-8, numbers use standard JSON format
- **Null handling**: Missing sensor values are `null`, not omitted fields
- **Timestamps**: ISO 8601 UTC, millisecond precision where available

## Validation Rules

The ingestion service **must** validate:
- Schema conformance (JSON Schema v7)
- Required fields present
- Enum values are in allowed set
- Numeric ranges (e.g., fuel_level_pct: 0-100)
- Timestamp is ISO 8601 UTC
- Machine/operator/site IDs match master data

Invalid messages are:
- **Logged with full context**
- **Not written to database**
- **Counted in metrics** (invalid_message_count)

## Phase Progression

| Phase | Capability | Status |
|-------|-----------|--------|
| 0 | Contract defined ✓ | This document |
| 1 | Simulator publishes to MQTT | Member 1 |
| 1 | Ingestion validates and stores | Member 2 |
| 2 | Edge rules evaluate and publish alerts | Member 1 |
| 2 | Alert feed visible to admin | Member 2 |
| 3 | ML models read from TimescaleDB | Member 3 |

## Sign-off Checklist

- [ ] Member 1: Schema files created and reviewed
- [ ] Member 2: Confirms schemas are parseable, ingestion handler designed
- [ ] Member 3: Confirms feature engineering can start from this schema
- [ ] Member 4: Confirms WebSocket feed can handle this message structure
- [ ] Team: Merge to main before Phase 1 starts

---

**Questions or changes?** Update this document and bump the version before Phase 1 starts. No changes to the schema after Phase 1 begins without team agreement.
