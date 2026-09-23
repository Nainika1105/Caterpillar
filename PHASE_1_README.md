# Phase 1: Data Pipeline (Member 1 Focus)

**Status**: Scaffolded, ready for implementation  
**Duration**: 15% of total time  
**Owner**: Member 1 (Edge & Data)  
**Dependencies**: Phase 0 complete (MQTT contract signed)

## Deliverables

1. **Simulator** ✓ Scaffolded
   - Load `telemetry_1min.csv`
   - Publish to MQTT at configurable speed
   - Support acceleration for demos (1 day per second)

2. **Ingest Service** ✓ Scaffolded
   - Subscribe to telemetry and alert topics
   - Validate against JSON schemas
   - Write to TimescaleDB
   - Publish events to Redis queue

3. **Database Schema** ✓ Created
   - TimescaleDB hypertable for telemetry (162K rows)
   - PostgreSQL master tables (sites, machines, operators, tasks)
   - Continuous aggregate for 2-hour rollups

4. **Infrastructure** ✓ Created
   - Docker Compose stack
   - Mosquitto MQTT broker
   - TimescaleDB
   - Redis

## Exit Criterion

**Admin logs in and sees live telemetry for 12 machines**

This means:
- [ ] Simulator publishes telemetry to MQTT continuously
- [ ] Ingest service reads and validates messages
- [ ] Data arrives in TimescaleDB
- [ ] API (Member 2) can query live telemetry
- [ ] Admin dashboard (Member 4) shows 12 machines with real-time data

## Quick Start

### 1. Start the Docker stack

```bash
docker-compose up -d
```

This starts:
- `timescaledb` (PostgreSQL + TimescaleDB) on port 5432
- `mosquitto` (MQTT broker) on port 1883
- `redis` (event queue) on port 6379
- `simulator` (publishes telemetry)
- `ingest` (subscribes and stores)

Check status:
```bash
docker-compose ps
docker-compose logs -f
```

### 2. Verify database is ready

```bash
# Wait for TimescaleDB to be healthy
docker-compose logs timescaledb

# Connect and test
psql postgres://admin:admin123@localhost:5432/caterpillar
```

Inside psql:
```sql
\dt  -- list tables
SELECT COUNT(*) FROM sites;  -- should be 3
SELECT COUNT(*) FROM machines;  -- should be 12
```

### 3. Monitor the simulator

```bash
docker-compose logs -f simulator
```

Expected output:
```
2025-05-01 08:00:00 - simulator - INFO - ✓ Connected to MQTT broker
2025-05-01 08:00:00 - simulator - INFO - Starting replay at 1.0x speed
2025-05-01 08:00:01 - simulator - INFO - Published 100 messages (2025-05-01 08:00:00)
```

### 4. Monitor the ingest service

```bash
docker-compose logs -f ingest
```

Expected output:
```
2025-05-01 08:00:00 - ingest - INFO - ✓ Connected to PostgreSQL
2025-05-01 08:00:00 - ingest - INFO - ✓ Connected to Redis
```

### 5. Test the ingest service

Check health:
```bash
curl http://localhost:8002/health
```

Response:
```json
{
  "status": "healthy",
  "mqtt_connected": true,
  "db_connected": true,
  "redis_connected": true,
  "stats": {
    "telemetry_received": 1234,
    "alerts_received": 0,
    "telemetry_stored": 1234,
    "alerts_stored": 0,
    "validation_errors": 0,
    "db_errors": 0
  }
}
```

## Implementation Checklist for Member 1

### Simulator (services/simulator/simulator.py)

- [x] Load telemetry CSV
- [x] Validate messages against schema
- [x] Publish to MQTT at configurable speed
- [ ] **TODO**: Add graceful shutdown
- [ ] **TODO**: Add resume capability (start from specific timestamp)
- [ ] **TODO**: Add metrics/logging for published messages
- [ ] **TODO**: Test with different playback speeds

### Ingest Service (services/ingest/app.py)

- [x] FastAPI scaffold
- [x] MQTT subscription
- [x] Message validation
- [x] Health endpoint
- [ ] **TODO**: Implement telemetry write to TimescaleDB
- [ ] **TODO**: Implement alert write to PostgreSQL
- [ ] **TODO**: Implement deduplication (use alert_id + timestamp)
- [ ] **TODO**: Implement metrics tracking
- [ ] **TODO**: Add error recovery

### Database (services/db/init.sql)

- [x] Create hypertable for telemetry
- [x] Create alerts table
- [x] Create incidents table
- [x] Create weather table
- [x] Create energy_events table
- [x] Create 2-hour aggregate table (machine_summary_2h)
- [x] Load master data (sites, machines, operators)
- [ ] **TODO**: Create continuous aggregate for machine_summary_2h
- [ ] **TODO**: Create retention policies (e.g., delete raw telemetry older than 30 days)

## Data Flow

```
CSV (telemetry_1min.csv)
  ↓
Simulator (publishes)
  ↓
MQTT Broker (mosquitto)
  ↓
Ingest Service (subscribes, validates)
  ↓
TimescaleDB (hypertable)
  ↓
Continuous Aggregate (machine_summary_2h every 2h)
  ↓
API (Member 2 queries)
  ↓
Admin Dashboard (Member 4 displays)
```

## Interface Contracts (Agreed in Phase 0)

### Member 1 → Member 2: MQTT Messages

**Telemetry Topic**: `site/{site_id}/machine/{machine_id}/telemetry`
- Schema: `config/schemas/telemetry_message.json`
- Frequency: 1 message per minute per machine

**Alert Topic**: `site/{site_id}/machine/{machine_id}/alerts`
- Schema: `config/schemas/alert_message.json`

### Member 1 ↔ Member 2: Database

Member 2 will query:
- `SELECT * FROM telemetry WHERE machine_id = ? AND timestamp BETWEEN ? AND ?`
- `SELECT * FROM alerts WHERE machine_id = ? ORDER BY timestamp DESC LIMIT 100`

Member 1 must ensure:
- Telemetry rows have `timestamp` indexed
- Alerts have `alert_id` as primary key (no duplicates)

## Troubleshooting

### Simulator not connecting to MQTT
```bash
# Check Mosquitto is running
docker-compose ps mosquitto

# Check network
docker network inspect caterpillar_default
```

### Ingest service not receiving messages
```bash
# Check MQTT broker logs
docker-compose logs mosquitto

# Test MQTT connectivity
docker-compose exec mosquitto mosquitto_sub -t "site/+/machine/+/telemetry" | head -10
```

### Database connection errors
```bash
# Check TimescaleDB is ready
docker-compose logs timescaledb | grep "PostgreSQL"

# Test connection
psql postgres://admin:admin123@localhost:5432/caterpillar -c "SELECT 1"
```

### Messages being validated but not stored
- Check `stats` endpoint: `curl http://localhost:8002/stats`
- Look for `validation_errors` or `db_errors`
- Check logs: `docker-compose logs ingest | grep ERROR`

## Performance Notes

**Playback Speed Environment Variable**:
- `PLAYBACK_SPEED=1.0`: Real-time (30 days takes 30 days)
- `PLAYBACK_SPEED=60`: 60x faster (30 days takes 12 hours)
- `PLAYBACK_SPEED=1440`: Very fast (30 days takes 30 minutes, for testing)

Set in docker-compose or `.env`:
```bash
PLAYBACK_SPEED=60 docker-compose up simulator
```

**Expected throughput**:
- 162,000 telemetry rows over 30 days
- At 60x: ~93 messages/second through MQTT
- At real-time: ~0.06 messages/second

## Next Phase

Once telemetry flows end-to-end:
1. Member 2 builds API endpoints to query the data
2. Member 4 builds admin dashboard to visualize it
3. Member 1 starts Phase 2: Edge rules and offline buffer

## Files

```
services/
├── simulator/
│   ├── Dockerfile          # Build container
│   ├── requirements.txt     # Dependencies (paho-mqtt, pandas)
│   └── simulator.py         # Main replay service
├── ingest/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app.py              # FastAPI service (Member 2 builds on this)
├── mqtt/
│   └── mosquitto.conf      # MQTT broker config
├── edge/                   # Phase 2 (stub for now)
└── db/
    └── init.sql            # Database schema
```

---

**Questions?** Check the MQTT_CONTRACT.md for detailed message formats, or ask the team in standup.
