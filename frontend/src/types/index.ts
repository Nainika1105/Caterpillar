export type Role = 'admin' | 'operator' | 'trainer';

export type MachineClass = 
  | 'excavator' 
  | 'mini_excavator' 
  | 'electric_excavator' 
  | 'electric_mini_excavator' 
  | 'wheel_loader' 
  | 'dozer' 
  | 'backhoe_loader';

export type Powertrain = 'diesel' | 'electric';

export type MachineState = 'working' | 'idle' | 'travel' | 'off' | 'charging' | 'refueling' | 'weather_hold' | 'heat_rest';

export type Severity = 'critical' | 'high' | 'medium' | 'low';

export type ProximityZone = 'clear' | 'caution' | 'danger';

export type TaskStatus = 'pending' | 'in_progress' | 'completed' | 'paused' | 'blocked';

export interface Machine {
  machine_id: string;
  machine_class: MachineClass;
  powertrain: Powertrain;
  reference_model: string;
  site_id: string;
  primary_operator_id?: string;
  engine_hours_at_start: number;
  fuel_tank_l?: number;
  battery_kwh?: number;
  max_charge_kw?: number;
  commission_year: number;
}

export interface Operator {
  operator_id: string;
  name: string;
  experience_years: number;
  home_site_id: string;
  shift: string;
  certifications: string[];
}

export interface Site {
  site_id: string;
  name: string;
  city: string;
  lat: number;
  lon: number;
  soil_type: string;
  speed_limit_kmh: number;
}

export interface Task {
  task_id: string;
  task_type: string;
  site_id: string;
  machine_id: string;
  operator_id: string;
  start_time: string;
  end_time?: string;
  planned_duration_min: number;
  actual_duration_min?: number;
  quantity: number;
  quantity_unit: string;
  status: TaskStatus;
  notes?: string;
}

export interface TelemetryPoint {
  timestamp: string;
  site_id: string;
  machine_id: string;
  operator_id?: string;
  task_id?: string;
  state: MachineState;
  is_power_on: boolean;
  is_operator_present: boolean;
  seatbelt_status: 'fastened' | 'unfastened';
  engine_rpm: number;
  ground_speed_kmh: number;
  fuel_level_pct?: number;
  battery_soc_pct?: number;
  fuel_rate_lph?: number;
  power_kw?: number;
  fuel_used_l?: number;
  energy_used_kwh?: number;
  hydraulic_pressure_bar: number;
  hydraulic_oil_temp_c: number;
  coolant_temp_c: number;
  load_cycles: number;
  proximity_min_m: number;
  proximity_zone: ProximityZone;
  harsh_events: number;
  ambient_temp_c: number;
  rain_mm_hr: number;
  engine_hours: number;
  anomaly_id?: string;
  anomaly_type?: string;
}

export interface SafetyAlert {
  alert_id: string;
  machine_id: string;
  operator_id: string;
  site_id: string;
  alert_code: string;
  severity: Severity;
  message: string;
  start: string;
  end?: string;
  duration_min?: number;
  acknowledged?: boolean;
}

export interface Incident {
  incident_id: string;
  site_id: string;
  machine_id: string;
  operator_id: string;
  task_id?: string;
  incident_type: string;
  severity: Severity;
  description: string;
  timestamp: string;
  status: 'reported' | 'investigating' | 'resolved';
}

export interface EnergyPoint {
  point_id: string;
  site_id: string;
  type: 'fuel_bowser' | 'dc_fast_charger' | 'ac_charger';
  name: string;
  max_rate: number; // kW or L/min
  status: 'available' | 'in_use' | 'offline';
  lat: number;
  lon: number;
}

export interface TrainingRecord {
  record_id: string;
  operator_id: string;
  course_name: string;
  valid_from: string;
  valid_until?: string;
  completed: boolean;
  score_pct: number;
  is_expired?: boolean;
}

export interface TwoHourSummary {
  machine_id: string;
  machine_class: string;
  powertrain: Powertrain;
  operating_hours_2h: number;
  idle_hours_2h: number;
  fuel_or_kwh_consumed: number;
  unit: string;
  load_cycles: number;
  harsh_events: number;
  avg_coolant_temp: number;
  active_alerts: number;
  seatbelt_compliance_pct: number;
}

export interface AssignmentSuggestion {
  operator_id: string;
  operator_name: string;
  machine_id: string;
  machine_model: string;
  is_certified: boolean;
  missing_certifications: string[];
  estimated_duration_min: number;
  confidence_score: number;
  energy_sufficient: boolean;
  ranking_score: number;
}
