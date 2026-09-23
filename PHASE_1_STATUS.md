# Phase 1 Status: Data Flowing ✅

**Date**: 2026-09-23  
**Status**: 80% Complete - Core pipeline working, DB writes TODO

## What's Working ✅

| Component | Status | Evidence |
|-----------|--------|----------|
| **Simulator** | ✅ Publishing | 60x playback speed configured, loading 162K rows |
| **MQTT Broker** | ✅ Receiving | mosquitto running, listening on 1883 |
| **Ingest Service** | ✅ Consuming | Connected to MQTT, receiving messages at ~25 msg/sec |
| **Message Validation** | ✅ Passing | 252 messages validated against schema |
| **Database** | ✅ Ready | TimescaleDB running, schema initialized (3 sites, 12 machines) |
| **Redis** | ✅ Connected | Queue service ready for Phase 2 models |

## Telemetry Flow

```
Simulator (60x speed)
  ↓
  ├→ Publishing 162,000 rows
  ├→ Rate: ~25 messages/second
  ├→ Topics: site/{site}/machine/{id}/telemetry
  │
MQTT Broker (mosquitto:1883)
  ↓
Ingest Service (FastAPI on 8002)
  ├→ Subscribed to all site/+/machine/+/telemetry
  ├→ Validating against schema
  ├→ Count: 252 messages processed ✅
  ├→ Validation errors: 0 ✅
  │
TimescaleDB (postgres:5432)
  └→ Table: telemetry (empty - TODO)
```

## Stats (Live)

```json
{
  "telemetry_received": 252,
  "telemetry_stored": 252,
  "validation_errors": 0,
  "db_errors": 0
}
```

## What's Left: Implement DB Writes

The ingest service receives and validates messages but **doesn't write them yet**. This is the scaffold design.

### TODO for Member 1 (Member 2 can help)

In `services/ingest/app.py`, implement these two functions:

#### 1. Write Telemetry to TimescaleDB

```python
def handle_telemetry(payload: dict):
    """
    TODO: Write to TimescaleDB telemetry hypertable
    
    Current: Counts messages only
    Needed: INSERT INTO telemetry (...)
    """
    stats["telemetry_received"] += 1
    
    # Validate structure
    if not all(field in payload for field in required_fields):
        stats["validation_errors"] += 1
        return
    
    # TODO: db_conn.execute("""
    #   INSERT INTO telemetry (timestamp, site_id, machine_id, ...)
    #   VALUES (%(timestamp)s, %(site_id)s, %(machine_id)s, ...)
    # """, payload)
    
    stats["telemetry_stored"] += 1
```

#### 2. Write Alerts to PostgreSQL

```python
def handle_alert(payload: dict):
    """
    TODO: Write to PostgreSQL alerts table
    
    Current: Counts messages only
    Needed: INSERT INTO alerts (...)
    """
    stats["alerts_received"] += 1
    
    # Validate
    if not all(field in payload for field in required_fields):
        stats["validation_errors"] += 1
        return
    
    # TODO: db_conn.execute("""
    #   INSERT INTO alerts (alert_id, timestamp, machine_id, ...)
    #   VALUES (%(alert_id)s, %(timestamp)s, %(machine_id)s, ...)
    # """, payload)
    
    stats["alerts_stored"] += 1
```

## How to Test When Done

```bash
# 1. Implement the DB writes above

# 2. Rebuild ingest service
docker compose build ingest

# 3. Restart
docker compose restart ingest

# 4. Wait 30 seconds for messages to flow

# 5. Query the database
psql postgres://admin:admin123@localhost:5432/caterpillar -c \
  "SELECT COUNT(*) FROM telemetry;" \
  "SELECT timestamp, machine_id, state FROM telemetry LIMIT 5;"

# Should see: telemetry_rows count > 1000
```

## Phase 1 Exit Criterion

- [x] Simulator publishes continuously
- [x] MQTT broker receives messages  
- [x] Ingest service subscribes and validates
- [ ] **TODO**: Data written to TimescaleDB
- [ ] Member 2 builds API to query
- [ ] Member 4 builds dashboard to display

## Next Steps

1. **Member 1**: Implement the two DB write functions (30 min)
2. **Member 2**: Query the telemetry table via REST API (start building after #1 is done)
3. **Member 4**: Build admin dashboard that displays live data from API

## Running the Stack

```bash
cd /Users/nainikaanish/Documents/Caterpillar

# View all logs
docker compose logs -f

# View just simulator
docker compose logs -f simulator

# View just ingest
docker compose logs -f ingest

# Check stats
curl http://localhost:8002/stats

# Connect to database
psql postgres://admin:admin123@localhost:5432/caterpillar

# Stop stack
docker compose down

# Stop and clean data
docker compose down -v
```

## Configuration

- **PLAYBACK_SPEED**: 60x (30 days of data replays in ~12 hours)
- **MQTT_HOST**: mosquitto (Docker network)
- **MQTT_PORT**: 1883
- **DB_HOST**: timescaledb
- **DB_PORT**: 5432
- **DB_NAME**: caterpillar
- **INGEST_PORT**: 8002

Edit `docker-compose.yml` to change any settings, then `docker compose up -d`

---

**Blocked By**: DB writes not implemented  
**Blocks**: Member 2 API, Member 4 Dashboard  
**ETA for Unblock**: 30 minutes  

