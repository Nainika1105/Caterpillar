import { 
  Machine, 
  Operator, 
  Site, 
  Task, 
  TelemetryPoint, 
  SafetyAlert, 
  Incident, 
  EnergyPoint, 
  TrainingRecord, 
  TwoHourSummary 
} from '../types';

export const INITIAL_SITES: Site[] = [
  { site_id: 'S01', name: 'Chennai OMR Metro Corridor', city: 'Chennai', lat: 12.9010, lon: 80.2279, soil_type: 'Sandy Clay', speed_limit_kmh: 10.0 },
  { site_id: 'S02', name: 'Bengaluru Ring Road Pkg 3', city: 'Bengaluru', lat: 12.9716, lon: 77.7500, soil_type: 'Red Soil', speed_limit_kmh: 10.0 },
  { site_id: 'S03', name: 'Hosur Aggregate Quarry', city: 'Hosur', lat: 12.7409, lon: 77.8253, soil_type: 'Rocky Hardpan', speed_limit_kmh: 10.0 },
];

export const INITIAL_MACHINES: Machine[] = [
  { machine_id: 'EXC001', machine_class: 'mini_excavator', powertrain: 'diesel', reference_model: 'CAT 303 CR', site_id: 'S01', primary_operator_id: 'OP1001', engine_hours_at_start: 1523.5, fuel_tank_l: 45.0, commission_year: 2019 },
  { machine_id: 'EXC002', machine_class: 'excavator', powertrain: 'diesel', reference_model: 'CAT 320', site_id: 'S01', primary_operator_id: 'OP1002', engine_hours_at_start: 6412.0, fuel_tank_l: 345.0, commission_year: 2022 },
  { machine_id: 'EXC003', machine_class: 'excavator', powertrain: 'diesel', reference_model: 'CAT 320', site_id: 'S02', primary_operator_id: 'OP1003', engine_hours_at_start: 3890.4, fuel_tank_l: 345.0, commission_year: 2024 },
  { machine_id: 'EXC004', machine_class: 'electric_excavator', powertrain: 'electric', reference_model: 'CAT 320 EV (20t Electric)', site_id: 'S02', primary_operator_id: 'OP1004', engine_hours_at_start: 412.7, battery_kwh: 300.0, max_charge_kw: 150.0, commission_year: 2024 },
  { machine_id: 'EXC005', machine_class: 'electric_mini_excavator', powertrain: 'electric', reference_model: 'CAT 301.9 EV Mini', site_id: 'S01', primary_operator_id: 'OP1005', engine_hours_at_start: 288.1, battery_kwh: 64.0, max_charge_kw: 40.0, commission_year: 2024 },
  { machine_id: 'EXC006', machine_class: 'excavator', powertrain: 'diesel', reference_model: 'CAT 320', site_id: 'S03', primary_operator_id: 'OP1006', engine_hours_at_start: 8120.9, fuel_tank_l: 345.0, commission_year: 2018 },
  { machine_id: 'WL001', machine_class: 'wheel_loader', powertrain: 'diesel', reference_model: 'CAT 950 GC', site_id: 'S01', primary_operator_id: 'OP1007', engine_hours_at_start: 5230.2, fuel_tank_l: 300.0, commission_year: 2019 },
  { machine_id: 'WL002', machine_class: 'wheel_loader', powertrain: 'diesel', reference_model: 'CAT 950 GC', site_id: 'S03', primary_operator_id: 'OP1008', engine_hours_at_start: 7011.6, fuel_tank_l: 300.0, commission_year: 2017 },
  { machine_id: 'DZ001', machine_class: 'dozer', powertrain: 'diesel', reference_model: 'CAT D6', site_id: 'S02', primary_operator_id: 'OP1009', engine_hours_at_start: 4402.3, fuel_tank_l: 400.0, commission_year: 2020 },
  { machine_id: 'DZ002', machine_class: 'dozer', powertrain: 'diesel', reference_model: 'CAT D6', site_id: 'S03', primary_operator_id: 'OP1010', engine_hours_at_start: 9310.8, fuel_tank_l: 400.0, commission_year: 2016 },
  { machine_id: 'BH001', machine_class: 'backhoe_loader', powertrain: 'diesel', reference_model: 'CAT 432', site_id: 'S01', primary_operator_id: 'OP1011', engine_hours_at_start: 2210.5, fuel_tank_l: 160.0, commission_year: 2021 },
  { machine_id: 'BH002', machine_class: 'backhoe_loader', powertrain: 'diesel', reference_model: 'CAT 432', site_id: 'S02', primary_operator_id: 'OP1012', engine_hours_at_start: 3105.0, fuel_tank_l: 160.0, commission_year: 2016 },
];

export const INITIAL_OPERATORS: Operator[] = [
  { operator_id: 'OP1001', name: 'Arjun Kumar', experience_years: 6, home_site_id: 'S01', shift: 'Day Shift (08:00 - 17:00)', certifications: ['excavator', 'mini_excavator', 'wheel_loader'] },
  { operator_id: 'OP1002', name: 'Suresh Babu', experience_years: 11, home_site_id: 'S01', shift: 'Day Shift (08:00 - 17:00)', certifications: ['excavator'] },
  { operator_id: 'OP1003', name: 'Manjunath R', experience_years: 4, home_site_id: 'S02', shift: 'Day Shift (08:00 - 17:00)', certifications: ['excavator', 'mini_excavator'] },
  { operator_id: 'OP1004', name: 'Priya Shankar', experience_years: 3, home_site_id: 'S02', shift: 'Day Shift (08:00 - 17:00)', certifications: ['ev_high_voltage', 'excavator', 'mini_excavator', 'wheel_loader'] },
  { operator_id: 'OP1005', name: 'Karthik Raja', experience_years: 5, home_site_id: 'S01', shift: 'Day Shift (08:00 - 17:00)', certifications: ['backhoe_loader', 'ev_high_voltage', 'excavator', 'mini_excavator'] },
  { operator_id: 'OP1006', name: 'Venkatesh M', experience_years: 14, home_site_id: 'S03', shift: 'Day Shift (08:00 - 17:00)', certifications: ['dozer', 'excavator'] },
  { operator_id: 'OP1007', name: 'Ravi Teja', experience_years: 2, home_site_id: 'S01', shift: 'Day Shift (08:00 - 17:00)', certifications: ['excavator', 'mini_excavator', 'wheel_loader'] },
  { operator_id: 'OP1008', name: 'Lakshmi Narayan', experience_years: 9, home_site_id: 'S03', shift: 'Day Shift (08:00 - 17:00)', certifications: ['dozer', 'wheel_loader'] },
  { operator_id: 'OP1009', name: 'Imran Pasha', experience_years: 7, home_site_id: 'S02', shift: 'Day Shift (08:00 - 17:00)', certifications: ['dozer'] },
  { operator_id: 'OP1010', name: 'Gopal Krishnan', experience_years: 17, home_site_id: 'S03', shift: 'Day Shift (08:00 - 17:00)', certifications: ['dozer'] },
  { operator_id: 'OP1011', name: 'Dinesh Selvam', experience_years: 8, home_site_id: 'S01', shift: 'Day Shift (08:00 - 17:00)', certifications: ['backhoe_loader', 'dozer', 'wheel_loader'] },
  { operator_id: 'OP1012', name: 'Harish Gowda', experience_years: 5, home_site_id: 'S02', shift: 'Day Shift (08:00 - 17:00)', certifications: ['backhoe_loader', 'excavator'] },
  { operator_id: 'OP1013', name: 'Anand Pillai', experience_years: 12, home_site_id: 'S01', shift: 'Day Shift (08:00 - 17:00)', certifications: ['backhoe_loader', 'ev_high_voltage', 'excavator', 'mini_excavator', 'wheel_loader'] },
  { operator_id: 'OP1014', name: 'Mohammed Rafiq', experience_years: 10, home_site_id: 'S02', shift: 'Day Shift (08:00 - 17:00)', certifications: ['backhoe_loader', 'ev_high_voltage', 'excavator', 'mini_excavator', 'wheel_loader'] },
  { operator_id: 'OP1015', name: 'Sathya Moorthy', experience_years: 1, home_site_id: 'S03', shift: 'Day Shift (08:00 - 17:00)', certifications: ['backhoe_loader', 'excavator', 'mini_excavator', 'wheel_loader'] },
];

export const INITIAL_ENERGY_POINTS: EnergyPoint[] = [
  { point_id: 'S01-FB1', site_id: 'S01', type: 'fuel_bowser', name: 'Metro North Mobile Bowser', max_rate: 120, status: 'available', lat: 12.9022, lon: 80.2270 },
  { point_id: 'S01-DC1', site_id: 'S01', type: 'dc_fast_charger', name: 'OMR Supercharge Pod 1', max_rate: 60.0, status: 'available', lat: 12.9002, lon: 80.2290 },
  { point_id: 'S02-FB1', site_id: 'S02', type: 'fuel_bowser', name: 'Ring Road Heavy Diesel Bowser', max_rate: 150, status: 'available', lat: 12.9728, lon: 77.7491 },
  { point_id: 'S02-DC1', site_id: 'S02', type: 'dc_fast_charger', name: 'High-Power Dual Port EV Station', max_rate: 150.0, status: 'available', lat: 12.9708, lon: 77.7511 },
  { point_id: 'S03-FB1', site_id: 'S03', type: 'fuel_bowser', name: 'Quarry Pit Bowser Station', max_rate: 180, status: 'available', lat: 12.7421, lon: 77.8244 },
];

export const INITIAL_TASKS: Task[] = [
  { task_id: 'T-10492', task_type: 'trench_excavation', site_id: 'S01', machine_id: 'EXC002', operator_id: 'OP1002', start_time: '2026-09-23T08:30:00Z', planned_duration_min: 180, quantity: 450, quantity_unit: 'm³', status: 'in_progress', notes: 'Trenching for storm water drain package 2. High water table caution.' },
  { task_id: 'T-10493', task_type: 'foundation_dig', site_id: 'S02', machine_id: 'EXC004', operator_id: 'OP1004', start_time: '2026-09-23T09:00:00Z', planned_duration_min: 240, quantity: 600, quantity_unit: 'm³', status: 'in_progress', notes: 'Pylon pier excavation using 20t Electric CAT. Keep battery buffer above 20%.' },
  { task_id: 'T-10494', task_type: 'stockpile_loading', site_id: 'S01', machine_id: 'WL001', operator_id: 'OP1007', start_time: '2026-09-23T09:15:00Z', planned_duration_min: 150, quantity: 800, quantity_unit: 'tonnes', status: 'in_progress', notes: 'Loading sub-base aggregate to tipper trucks at bay 4.' },
  { task_id: 'T-10495', task_type: 'bulk_earthmoving', site_id: 'S02', machine_id: 'DZ001', operator_id: 'OP1009', start_time: '2026-09-23T10:00:00Z', planned_duration_min: 210, quantity: 1200, quantity_unit: 'm³', status: 'pending', notes: 'Pushing cut material toward embankment slope.' },
  { task_id: 'T-10496', task_type: 'quarry_rip_push', site_id: 'S03', machine_id: 'DZ002', operator_id: 'OP1010', start_time: '2026-09-23T07:45:00Z', planned_duration_min: 300, quantity: 1500, quantity_unit: 'tonnes', status: 'in_progress', notes: 'Hard granite ripper pass at bench 3.' },
  { task_id: 'T-10497', task_type: 'utility_backfill', site_id: 'S01', machine_id: 'BH001', operator_id: 'OP1011', start_time: '2026-09-23T11:00:00Z', planned_duration_min: 120, quantity: 180, quantity_unit: 'm³', status: 'pending', notes: 'Backfilling telecom conduit line near station 12.' },
];

export const INITIAL_TRAINING: TrainingRecord[] = [
  { record_id: 'TR-01', operator_id: 'OP1001', course_name: 'Seatbelt and ROPS safety', valid_from: '2024-08-27', valid_until: '2027-08-12', completed: true, score_pct: 67 },
  { record_id: 'TR-02', operator_id: 'OP1001', course_name: 'Proximity and blind-spot awareness', valid_from: '2024-12-06', valid_until: '2026-11-26', completed: true, score_pct: 79 },
  { record_id: 'TR-03', operator_id: 'OP1002', course_name: 'Seatbelt and ROPS safety', valid_from: '2022-10-02', valid_until: '2025-09-16', completed: true, score_pct: 73, is_expired: true },
  { record_id: 'TR-04', operator_id: 'OP1002', course_name: 'Proximity and blind-spot awareness', valid_from: '2025-01-24', valid_until: '2027-01-14', completed: true, score_pct: 90 },
  { record_id: 'TR-05', operator_id: 'OP1004', course_name: 'EV High Voltage Safety Systems', valid_from: '2024-01-15', valid_until: '2027-01-15', completed: true, score_pct: 98 },
  { record_id: 'TR-06', operator_id: 'OP1005', course_name: 'EV High Voltage Safety Systems', valid_from: '2024-02-10', valid_until: '2027-02-10', completed: true, score_pct: 94 },
  { record_id: 'TR-07', operator_id: 'OP1007', course_name: 'Seatbelt and ROPS safety', valid_from: '2023-03-12', valid_until: '2026-03-12', completed: true, score_pct: 62, is_expired: true },
  { record_id: 'TR-08', operator_id: 'OP1009', course_name: 'Heavy Dozer Blade Control', valid_from: '2024-05-18', valid_until: '2027-05-18', completed: true, score_pct: 88 },
  { record_id: 'TR-09', operator_id: 'OP1010', course_name: 'Quarry Bench Stability & Slope Safety', valid_from: '2024-04-10', valid_until: '2027-04-10', completed: true, score_pct: 95 },
];

export const INITIAL_SUMMARIES: TwoHourSummary[] = [
  { machine_id: 'EXC001', machine_class: 'Mini Excavator', powertrain: 'diesel', operating_hours_2h: 1.4, idle_hours_2h: 0.6, fuel_or_kwh_consumed: 7.2, unit: 'L', load_cycles: 42, harsh_events: 0, avg_coolant_temp: 84.2, active_alerts: 0, seatbelt_compliance_pct: 98.4 },
  { machine_id: 'EXC002', machine_class: 'Excavator (CAT 320)', powertrain: 'diesel', operating_hours_2h: 1.7, idle_hours_2h: 0.3, fuel_or_kwh_consumed: 38.4, unit: 'L', load_cycles: 96, harsh_events: 1, avg_coolant_temp: 91.0, active_alerts: 1, seatbelt_compliance_pct: 82.0 },
  { machine_id: 'EXC003', machine_class: 'Excavator (CAT 320)', powertrain: 'diesel', operating_hours_2h: 1.5, idle_hours_2h: 0.5, fuel_or_kwh_consumed: 34.1, unit: 'L', load_cycles: 88, harsh_events: 0, avg_coolant_temp: 87.5, active_alerts: 0, seatbelt_compliance_pct: 99.1 },
  { machine_id: 'EXC004', machine_class: 'CAT 320 EV', powertrain: 'electric', operating_hours_2h: 1.6, idle_hours_2h: 0.4, fuel_or_kwh_consumed: 48.2, unit: 'kWh', load_cycles: 92, harsh_events: 0, avg_coolant_temp: 61.4, active_alerts: 0, seatbelt_compliance_pct: 100.0 },
  { machine_id: 'EXC005', machine_class: 'CAT 301.9 EV', powertrain: 'electric', operating_hours_2h: 1.3, idle_hours_2h: 0.7, fuel_or_kwh_consumed: 14.8, unit: 'kWh', load_cycles: 38, harsh_events: 0, avg_coolant_temp: 58.2, active_alerts: 0, seatbelt_compliance_pct: 100.0 },
  { machine_id: 'EXC006', machine_class: 'Excavator (CAT 320)', powertrain: 'diesel', operating_hours_2h: 1.1, idle_hours_2h: 0.9, fuel_or_kwh_consumed: 29.3, unit: 'L', load_cycles: 64, harsh_events: 2, avg_coolant_temp: 94.6, active_alerts: 1, seatbelt_compliance_pct: 78.5 },
  { machine_id: 'WL001', machine_class: 'Wheel Loader (950 GC)', powertrain: 'diesel', operating_hours_2h: 1.8, idle_hours_2h: 0.2, fuel_or_kwh_consumed: 42.0, unit: 'L', load_cycles: 114, harsh_events: 0, avg_coolant_temp: 89.1, active_alerts: 0, seatbelt_compliance_pct: 95.0 },
  { machine_id: 'WL002', machine_class: 'Wheel Loader (950 GC)', powertrain: 'diesel', operating_hours_2h: 1.6, idle_hours_2h: 0.4, fuel_or_kwh_consumed: 39.5, unit: 'L', load_cycles: 102, harsh_events: 1, avg_coolant_temp: 90.8, active_alerts: 0, seatbelt_compliance_pct: 92.4 },
  { machine_id: 'DZ001', machine_class: 'Dozer (CAT D6)', powertrain: 'diesel', operating_hours_2h: 1.7, idle_hours_2h: 0.3, fuel_or_kwh_consumed: 54.2, unit: 'L', load_cycles: 58, harsh_events: 0, avg_coolant_temp: 92.3, active_alerts: 0, seatbelt_compliance_pct: 99.4 },
  { machine_id: 'DZ002', machine_class: 'Dozer (CAT D6)', powertrain: 'diesel', operating_hours_2h: 1.8, idle_hours_2h: 0.2, fuel_or_kwh_consumed: 57.0, unit: 'L', load_cycles: 62, harsh_events: 1, avg_coolant_temp: 96.1, active_alerts: 1, seatbelt_compliance_pct: 91.0 },
  { machine_id: 'BH001', machine_class: 'Backhoe Loader (432)', powertrain: 'diesel', operating_hours_2h: 1.2, idle_hours_2h: 0.8, fuel_or_kwh_consumed: 15.6, unit: 'L', load_cycles: 32, harsh_events: 0, avg_coolant_temp: 86.4, active_alerts: 0, seatbelt_compliance_pct: 96.0 },
  { machine_id: 'BH002', machine_class: 'Backhoe Loader (432)', powertrain: 'diesel', operating_hours_2h: 1.5, idle_hours_2h: 0.5, fuel_or_kwh_consumed: 19.8, unit: 'L', load_cycles: 44, harsh_events: 0, avg_coolant_temp: 88.0, active_alerts: 0, seatbelt_compliance_pct: 97.2 },
];

export const INITIAL_ALERTS: SafetyAlert[] = [
  { alert_id: 'AL-901', machine_id: 'EXC002', operator_id: 'OP1002', site_id: 'S01', alert_code: 'unbelted_moving', severity: 'critical', message: 'CRITICAL: Machine traveling at 6.8 km/h while operator seatbelt unfastened', start: '2026-09-23T13:54:10Z', duration_min: 4, acknowledged: false },
  { alert_id: 'AL-902', machine_id: 'EXC006', operator_id: 'OP1006', site_id: 'S03', alert_code: 'coolant_high', severity: 'high', message: 'Engine coolant temperature reached 98.4°C (Safe threshold: 95°C)', start: '2026-09-23T13:42:00Z', duration_min: 16, acknowledged: true },
  { alert_id: 'AL-903', machine_id: 'DZ002', operator_id: 'OP1010', site_id: 'S03', alert_code: 'proximity_breach', severity: 'high', message: 'Ground personnel detected within 2.4m swing radius in red zone', start: '2026-09-23T13:30:15Z', duration_min: 2, acknowledged: true },
  { alert_id: 'AL-904', machine_id: 'WL002', operator_id: 'OP1008', site_id: 'S03', alert_code: 'excessive_idle', severity: 'low', message: 'Continuous low-idle duration exceeded 45 minutes with A/C running', start: '2026-09-23T12:15:00Z', duration_min: 48, acknowledged: true },
];

export const INITIAL_INCIDENTS: Incident[] = [
  {
    incident_id: 'INC-2026-01',
    site_id: 'S01',
    machine_id: 'EXC002',
    operator_id: 'OP1002',
    task_id: 'T-10492',
    incident_type: 'Near Miss - Proximity',
    severity: 'high',
    description: 'Surveyor entered blind spot while excavator slewed to spoil pile. Proximity radar buzzer alerted operator in time.',
    timestamp: '2026-09-23T11:45:00Z',
    status: 'investigating'
  },
  {
    incident_id: 'INC-2026-02',
    site_id: 'S03',
    machine_id: 'DZ002',
    operator_id: 'OP1010',
    task_id: 'T-10496',
    incident_type: 'Equipment Minor Damage',
    severity: 'medium',
    description: 'Boulder roll contacted track shoe guard on steep bench descent. No hydraulic leaks observed.',
    timestamp: '2026-09-22T16:20:00Z',
    status: 'resolved'
  }
];

export const INITIAL_ANOMALIES = [
  {
    id: 'ANOM-01',
    machine_id: 'EXC002',
    timestamp: '2026-09-23T11:30:00Z',
    type: 'abnormal_fuel_burn',
    severity: 'high',
    score: 0.88,
    description: 'Fuel burn rate surged to 29.4 L/h (expected: 18.2 L/h) during standard trenching. Isolation Forest flagged hydraulic relief valve bypass.',
    ml_detected: true,
    rule_detected: false,
    impact: 'Estimated 28% excess fuel consumption; potential pump cavitation.'
  },
  {
    id: 'ANOM-02',
    machine_id: 'EXC004',
    timestamp: '2026-09-23T12:10:00Z',
    type: 'thermal_battery_delta',
    severity: 'medium',
    score: 0.74,
    description: 'Module 3 cell temperature gradient exceeds 6.2°C under 120kW peak breakout torque.',
    ml_detected: true,
    rule_detected: false,
    impact: 'Fast-charging current derated automatically by BMS to protect lifespan.'
  },
  {
    id: 'ANOM-03',
    machine_id: 'DZ002',
    timestamp: '2026-09-23T10:45:00Z',
    type: 'harsh_track_slip',
    severity: 'medium',
    score: 0.69,
    description: 'Repeated high-RPM track slip without ground speed gain indicates severe undercarriage spin on bedrock.',
    ml_detected: true,
    rule_detected: true,
    impact: 'Accelerated track wear rate; operator coaching advisory issued.'
  }
];
