-- Create extensions
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Master tables (normalized data)
CREATE TABLE IF NOT EXISTS sites (
  site_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  latitude FLOAT,
  longitude FLOAT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS machines (
  machine_id TEXT PRIMARY KEY,
  site_id TEXT NOT NULL REFERENCES sites(site_id),
  name TEXT,
  machine_type TEXT,
  fuel_type TEXT CHECK (fuel_type IN ('diesel', 'electric', 'hybrid')),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS operators (
  operator_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  site_id TEXT REFERENCES sites(site_id),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tasks (
  task_id TEXT PRIMARY KEY,
  site_id TEXT NOT NULL REFERENCES sites(site_id),
  machine_id TEXT REFERENCES machines(machine_id),
  operator_id TEXT REFERENCES operators(operator_id),
  task_type TEXT,
  status TEXT DEFAULT 'pending',
  start_time TIMESTAMP,
  end_time TIMESTAMP,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Telemetry hypertable (time-series, ~162K rows for 30 days x 12 machines)
CREATE TABLE IF NOT EXISTS telemetry (
  timestamp TIMESTAMP NOT NULL,
  site_id TEXT NOT NULL,
  machine_id TEXT NOT NULL,
  operator_id TEXT,
  task_id TEXT,
  state TEXT,
  power_on BOOLEAN,
  operator_present BOOLEAN,
  seatbelt_status TEXT,
  engine_rpm FLOAT,
  ground_speed_kmh FLOAT,
  fuel_level_pct FLOAT,
  battery_soc_pct FLOAT,
  fuel_rate_lph FLOAT,
  power_kw FLOAT,
  energy_used FLOAT,
  hydraulic_pressure_bar FLOAT,
  hydraulic_oil_temp_c FLOAT,
  coolant_temp_c FLOAT,
  load_cycles INTEGER,
  proximity_min_m FLOAT,
  proximity_zone TEXT,
  harsh_events INTEGER,
  ambient_temp_c FLOAT,
  rain_mm_hr FLOAT,
  engine_hours FLOAT,
  anomaly_id TEXT,
  anomaly_type TEXT
);

-- Convert to hypertable (1-hour chunks for 30 days of data)
SELECT create_hypertable('telemetry', 'timestamp', if_not_exists => TRUE, chunk_time_interval => INTERVAL '1 hour');

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_telemetry_machine_time ON telemetry (machine_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_telemetry_site_time ON telemetry (site_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_telemetry_task ON telemetry (task_id);

-- Alerts table
CREATE TABLE IF NOT EXISTS alerts (
  alert_id TEXT PRIMARY KEY,
  timestamp TIMESTAMP NOT NULL,
  machine_id TEXT NOT NULL REFERENCES machines(machine_id),
  operator_id TEXT REFERENCES operators(operator_id),
  site_id TEXT NOT NULL REFERENCES sites(site_id),
  rule TEXT NOT NULL,
  severity TEXT NOT NULL CHECK (severity IN ('info', 'warning', 'critical')),
  message TEXT,
  data JSONB,
  acknowledged BOOLEAN DEFAULT FALSE,
  acknowledged_at TIMESTAMP,
  acknowledged_by TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_alerts_machine_time ON alerts (machine_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts (severity);
CREATE INDEX IF NOT EXISTS idx_alerts_rule ON alerts (rule);

-- Incidents (incidents linked to alerts)
CREATE TABLE IF NOT EXISTS incidents (
  incident_id TEXT PRIMARY KEY,
  alert_id TEXT REFERENCES alerts(alert_id),
  machine_id TEXT NOT NULL REFERENCES machines(machine_id),
  operator_id TEXT REFERENCES operators(operator_id),
  site_id TEXT NOT NULL REFERENCES sites(site_id),
  description TEXT,
  severity TEXT CHECK (severity IN ('minor', 'moderate', 'severe')),
  status TEXT DEFAULT 'open' CHECK (status IN ('open', 'investigating', 'resolved')),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  resolved_at TIMESTAMP
);

-- Weather data (per site, hourly)
CREATE TABLE IF NOT EXISTS weather (
  timestamp TIMESTAMP NOT NULL,
  site_id TEXT NOT NULL REFERENCES sites(site_id),
  temperature_c FLOAT,
  humidity_pct FLOAT,
  wind_speed_kmh FLOAT,
  wind_direction_deg FLOAT,
  rain_mm_hr FLOAT,
  severe_weather_alert TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

SELECT create_hypertable('weather', 'timestamp', if_not_exists => TRUE, chunk_time_interval => INTERVAL '1 day');
CREATE INDEX IF NOT EXISTS idx_weather_site_time ON weather (site_id, timestamp DESC);

-- Energy events (refueling/charging)
CREATE TABLE IF NOT EXISTS energy_events (
  event_id TEXT PRIMARY KEY,
  machine_id TEXT NOT NULL REFERENCES machines(machine_id),
  site_id TEXT NOT NULL REFERENCES sites(site_id),
  event_type TEXT CHECK (event_type IN ('refuel', 'charge')),
  amount FLOAT NOT NULL,
  duration_min FLOAT,
  timestamp TIMESTAMP NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_energy_events_machine_time ON energy_events (machine_id, timestamp DESC);

-- 2-hour aggregate (continuous aggregate)
-- This will be populated by Member 1 as continuous aggregate from telemetry
CREATE TABLE IF NOT EXISTS machine_summary_2h (
  time_bucket TIMESTAMP NOT NULL,
  site_id TEXT NOT NULL,
  machine_id TEXT NOT NULL,
  idle_time_min FLOAT,
  working_time_min FLOAT,
  fuel_used_l FLOAT,
  avg_fuel_level_pct FLOAT,
  avg_battery_soc_pct FLOAT,
  harsh_events_count INTEGER,
  load_cycles_count INTEGER,
  avg_proximity_m FLOAT,
  seatbelt_violations INTEGER,
  alert_count INTEGER,
  PRIMARY KEY (time_bucket, site_id, machine_id)
);

CREATE INDEX IF NOT EXISTS idx_machine_summary_2h_site_time ON machine_summary_2h (site_id, time_bucket DESC);
CREATE INDEX IF NOT EXISTS idx_machine_summary_2h_machine_time ON machine_summary_2h (machine_id, time_bucket DESC);

-- Certifications & Training
CREATE TABLE IF NOT EXISTS certifications (
  certification_id TEXT PRIMARY KEY,
  operator_id TEXT NOT NULL REFERENCES operators(operator_id),
  machine_type TEXT NOT NULL,
  issued_at TIMESTAMP NOT NULL,
  expires_at TIMESTAMP NOT NULL,
  status TEXT DEFAULT 'active' CHECK (status IN ('active', 'expired', 'revoked')),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_certifications_operator ON certifications (operator_id);
CREATE INDEX IF NOT EXISTS idx_certifications_machine_type ON certifications (machine_type);

-- Load sample data (sites, machines, operators)
INSERT INTO sites (site_id, name, latitude, longitude) VALUES
  ('S01', 'North Quarry', -25.2744, 133.7751),
  ('S02', 'East Pit', -25.2845, 133.7952),
  ('S03', 'West Yard', -25.2545, 133.7451)
ON CONFLICT DO NOTHING;

-- Machines (12 total, mix of types and fuel types)
INSERT INTO machines (machine_id, site_id, name, machine_type, fuel_type) VALUES
  ('BH001', 'S01', 'Backhoe 1', 'Backhoe', 'diesel'),
  ('BH002', 'S02', 'Backhoe 2', 'Backhoe', 'diesel'),
  ('EXC003', 'S01', 'Excavator 3', 'Excavator', 'diesel'),
  ('EXC004', 'S02', 'Excavator 4', 'Excavator', 'diesel'),
  ('EXC005', 'S03', 'Excavator 5', 'Excavator', 'diesel'),
  ('EXC006', 'S03', 'Excavator 6', 'Excavator', 'diesel'),
  ('LD007', 'S01', 'Loader 7', 'Loader', 'diesel'),
  ('LD008', 'S02', 'Loader 8', 'Loader', 'diesel'),
  ('LD009', 'S03', 'Loader 9', 'Loader', 'diesel'),
  ('EV010', 'S01', 'EV Loader 10', 'Loader', 'electric'),
  ('EV011', 'S02', 'EV Loader 11', 'Loader', 'electric'),
  ('GR012', 'S03', 'Grader 12', 'Grader', 'diesel')
ON CONFLICT DO NOTHING;

-- Operators (sample)
INSERT INTO operators (operator_id, name, site_id) VALUES
  ('OP1011', 'John Smith', 'S01'),
  ('OP1012', 'Maria Garcia', 'S02'),
  ('OP1013', 'Ahmed Hassan', 'S01'),
  ('OP1014', 'Lisa Chen', 'S03'),
  ('OP1015', 'Robert Wilson', 'S02'),
  ('OP1016', 'Elena Rossi', 'S03'),
  ('OP1017', 'Carlos Rodriguez', 'S01'),
  ('OP1018', 'Sophie Martin', 'S02'),
  ('OP1019', 'David Kim', 'S03'),
  ('OP1020', 'Anna Kowalski', 'S01')
ON CONFLICT DO NOTHING;
