import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { 
  Machine, 
  Operator, 
  Site, 
  Task, 
  TelemetryPoint, 
  SafetyAlert, 
  Incident, 
  EnergyPoint, 
  TwoHourSummary, 
  Severity 
} from '../types';
import { api } from '../services/api';
import { wsService } from '../services/websocket';
import { cabAudio } from '../services/voiceAlerts';
import { useAuth } from './AuthContext';

interface FleetContextType {
  machines: Machine[];
  operators: Operator[];
  sites: Site[];
  tasks: Task[];
  alerts: SafetyAlert[];
  incidents: Incident[];
  summaries: TwoHourSummary[];
  energyPoints: EnergyPoint[];
  currentTelemetry: TelemetryPoint;
  criticalAlert: SafetyAlert | null;
  audioMuted: boolean;
  toggleAudioMute: () => void;
  isBackendConnected: boolean;
  acknowledgeAlert: (alertId: string) => Promise<void>;
  updateTaskStatus: (taskId: string, status: Task['status']) => Promise<void>;
  createTask: (newTask: Omit<Task, 'task_id'>) => Promise<Task>;
  reportIncident: (incident: Omit<Incident, 'incident_id' | 'timestamp' | 'status'>) => Promise<Incident>;
  triggerSimulationAlert: (code: 'unbelted_moving' | 'proximity_breach' | 'coolant_high' | 'low_battery') => void;
  refreshData: () => Promise<void>;
}

const FleetContext = createContext<FleetContextType | undefined>(undefined);

export const FleetProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { activeMachine, activeOperator } = useAuth();
  const [machines, setMachines] = useState<Machine[]>([]);
  const [operators, setOperators] = useState<Operator[]>([]);
  const [sites, setSites] = useState<Site[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [alerts, setAlerts] = useState<SafetyAlert[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [summaries, setSummaries] = useState<TwoHourSummary[]>([]);
  const [energyPoints, setEnergyPoints] = useState<EnergyPoint[]>([]);
  const [audioMuted, setAudioMuted] = useState(false);
  const [isBackendConnected, setIsBackendConnected] = useState(false);

  const [currentTelemetry, setCurrentTelemetry] = useState<TelemetryPoint>(() => ({
    timestamp: new Date().toISOString(),
    site_id: activeMachine.site_id,
    machine_id: activeMachine.machine_id,
    operator_id: activeOperator.operator_id,
    state: 'off',
    is_power_on: false,
    is_operator_present: false,
    seatbelt_status: 'fastened',
    engine_rpm: 0,
    ground_speed_kmh: 0,
    fuel_level_pct: undefined,
    battery_soc_pct: undefined,
    fuel_rate_lph: undefined,
    power_kw: undefined,
    hydraulic_pressure_bar: 0,
    hydraulic_oil_temp_c: 0,
    coolant_temp_c: 0,
    load_cycles: 0,
    proximity_min_m: 20,
    proximity_zone: 'clear',
    harsh_events: 0,
    ambient_temp_c: 0,
    rain_mm_hr: 0.0,
    engine_hours: activeMachine.engine_hours_at_start
  }));

  // Fetch initial datasets
  const loadData = useCallback(async () => {
    try {
      const [m, op, s, t, a, inc, sum, ep] = await Promise.all([
        api.getMachines(),
        api.getOperators(),
        api.getSites(),
        api.getTasks(),
        api.getAlerts(),
        api.getIncidents(),
        api.getSummaries(),
        api.getEnergyPoints()
      ]);
      setMachines(m);
      setOperators(op);
      setSites(s);
      setTasks(t);
      setAlerts(a);
      setIncidents(inc);
      setSummaries(sum);
      setEnergyPoints(ep);
    } catch (err) {
      console.error('Failed to load fleet data', err);
    }
  }, []);

  useEffect(() => {
    loadData();
    setIsBackendConnected(api.getBackendStatus());
  }, [loadData]);

  // Handle active WebSocket messages
  useEffect(() => {
    const unsubscribe = wsService.subscribe((event) => {
      if (event.type === 'telemetry.point') {
        const pt = event.data as TelemetryPoint;
        if (pt.machine_id === activeMachine.machine_id || !pt.machine_id) {
          setCurrentTelemetry(prev => ({
            ...prev,
            ...pt,
            machine_id: activeMachine.machine_id,
            battery_soc_pct: activeMachine.powertrain === 'electric' ? (prev.battery_soc_pct || 65) - 0.02 : undefined,
          }));
        }
      } else if (event.type === 'alert.received' || event.type === 'alert.created') {
        const alert = event.data as SafetyAlert;
        setAlerts(prev => [alert, ...prev.filter(a => a.alert_id !== alert.alert_id)]);
        
        // Trigger In-Cab Audio & Voice Alert immediately!
        if (alert.severity === 'critical' || alert.severity === 'high') {
          cabAudio.speak(alert.message, alert.alert_code, 8);
        } else {
          cabAudio.playIndustrialChirp(false);
        }
      } else if (event.type === 'connection.status') {
        const conn = event.data as { connected: boolean; liveServer: boolean };
        setIsBackendConnected(conn.liveServer);
      }
    });

    return () => {
      unsubscribe();
    };
  }, [activeMachine.machine_id, activeMachine.powertrain]);

  useEffect(() => {
    if (!activeMachine.machine_id) return;
    let cancelled = false;
    const poll = async () => {
      const telemetry = await api.getLatestTelemetry(activeMachine.machine_id);
      if (!cancelled && telemetry) {
        setCurrentTelemetry(previous => ({ ...previous, ...telemetry } as TelemetryPoint));
      }
    };
    void poll();
    const interval = window.setInterval(() => { void poll(); }, 5000);
    return () => { cancelled = true; window.clearInterval(interval); };
  }, [activeMachine.machine_id]);

  // Critical alert for banner
  const criticalAlert = alerts.find(a => !a.acknowledged && (a.severity === 'critical' || a.severity === 'high')) || null;

  const toggleAudioMute = () => {
    const next = !audioMuted;
    setAudioMuted(next);
    cabAudio.setMuted(next);
  };

  const acknowledgeAlert = async (alertId: string) => {
    await api.acknowledgeAlert(alertId);
    setAlerts(prev => prev.map(a => a.alert_id === alertId ? { ...a, acknowledged: true } : a));
  };

  const updateTaskStatus = async (taskId: string, status: Task['status']) => {
    const updated = await api.updateTaskStatus(taskId, status);
    if (updated) {
      setTasks(prev => prev.map(t => t.task_id === taskId ? updated : t));
    }
  };

  const createTask = async (newTask: Omit<Task, 'task_id'>) => {
    const created = await api.createTask(newTask);
    setTasks(prev => [created, ...prev]);
    return created;
  };

  const reportIncident = async (incident: Omit<Incident, 'incident_id' | 'timestamp' | 'status'>) => {
    const created = await api.reportIncident(incident);
    setIncidents(prev => [created, ...prev]);
    return created;
  };

  // Demo alert trigger
  const triggerSimulationAlert = (code: 'unbelted_moving' | 'proximity_breach' | 'coolant_high' | 'low_battery') => {
    let alert: SafetyAlert;

    if (code === 'unbelted_moving') {
      setCurrentTelemetry(prev => ({
        ...prev,
        seatbelt_status: 'unfastened',
        ground_speed_kmh: 7.2
      }));
      alert = {
        alert_id: `AL-EMG-${Date.now().toString().slice(-4)}`,
        machine_id: activeMachine.machine_id,
        operator_id: activeOperator.operator_id,
        site_id: activeMachine.site_id,
        alert_code: 'unbelted_moving',
        severity: 'critical',
        message: 'EMERGENCY: Seatbelt unbuckled while machine is in motion at 7.2 km/h. Stop immediately or fasten belt.',
        start: new Date().toISOString(),
        acknowledged: false
      };
    } else if (code === 'proximity_breach') {
      setCurrentTelemetry(prev => ({
        ...prev,
        proximity_min_m: 1.8,
        proximity_zone: 'danger'
      }));
      alert = {
        alert_id: `AL-EMG-${Date.now().toString().slice(-4)}`,
        machine_id: activeMachine.machine_id,
        operator_id: activeOperator.operator_id,
        site_id: activeMachine.site_id,
        alert_code: 'proximity_breach',
        severity: 'critical',
        message: 'PROXIMITY BREACH: Worker detected in Red Zone at 1.8 meters swing radius! Halt slewing!',
        start: new Date().toISOString(),
        acknowledged: false
      };
    } else if (code === 'coolant_high') {
      setCurrentTelemetry(prev => ({
        ...prev,
        coolant_temp_c: 102.5
      }));
      alert = {
        alert_id: `AL-EMG-${Date.now().toString().slice(-4)}`,
        machine_id: activeMachine.machine_id,
        operator_id: activeOperator.operator_id,
        site_id: activeMachine.site_id,
        alert_code: 'coolant_high',
        severity: 'high',
        message: 'THERMAL OVERHEAT: Coolant temperature surged to 102.5°C. Throttle back to low idle.',
        start: new Date().toISOString(),
        acknowledged: false
      };
    } else {
      // low_battery
      setCurrentTelemetry(prev => ({
        ...prev,
        battery_soc_pct: 14.2
      }));
      alert = {
        alert_id: `AL-EMG-${Date.now().toString().slice(-4)}`,
        machine_id: activeMachine.machine_id,
        operator_id: activeOperator.operator_id,
        site_id: activeMachine.site_id,
        alert_code: 'battery_low',
        severity: 'high',
        message: 'ENERGY DEPLETION ADVISORY: Battery at 14%. Remaining runtime: 22 mins. Proceed to charger S02-DC1.',
        start: new Date().toISOString(),
        acknowledged: false
      };
    }

    wsService.triggerLocalAlert(alert);
  };

  return (
    <FleetContext.Provider value={{
      machines,
      operators,
      sites,
      tasks,
      alerts,
      incidents,
      summaries,
      energyPoints,
      currentTelemetry,
      criticalAlert,
      audioMuted,
      toggleAudioMute,
      isBackendConnected,
      acknowledgeAlert,
      updateTaskStatus,
      createTask,
      reportIncident,
      triggerSimulationAlert,
      refreshData: loadData
    }}>
      {children}
    </FleetContext.Provider>
  );
};

export const useFleet = () => {
  const ctx = useContext(FleetContext);
  if (!ctx) throw new Error('useFleet must be used within FleetProvider');
  return ctx;
};
