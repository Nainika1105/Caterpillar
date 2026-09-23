import { Machine, Operator, Site, Task, SafetyAlert, Incident, TrainingRecord, AssignmentSuggestion, TwoHourSummary, EnergyPoint } from '../types';

const BASE_URL = '/api/v1';

class ApiService {
  private isOnlineWithBackend = false;
  private accessToken: string | null = sessionStorage.getItem('cat_access_token');

  constructor() {
    this.checkBackendHealth();
  }

  public async checkBackendHealth(): Promise<boolean> {
    try {
      const res = await fetch('/health', { signal: AbortSignal.timeout(1500) });
      this.isOnlineWithBackend = res.ok;
    } catch {
      this.isOnlineWithBackend = false;
    }
    return this.isOnlineWithBackend;
  }

  private async authenticate(): Promise<void> {
    if (this.accessToken) return;
    const body = new URLSearchParams({ username: 'admin', password: 'admin' });
    const res = await fetch(`${BASE_URL}/auth/token`, { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body });
    if (!res.ok) throw new Error(`Authentication failed: ${res.status}`);
    const token = await res.json() as { access_token: string };
    this.accessToken = token.access_token;
    sessionStorage.setItem('cat_access_token', token.access_token);
  }

  private async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    await this.authenticate();
    const headers = new Headers(init.headers);
    headers.set('Authorization', `Bearer ${this.accessToken}`);
    if (init.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
    const res = await fetch(`${BASE_URL}${path}`, { ...init, headers });
    if (!res.ok) throw new Error(`API ${res.status}: ${path}`);
    return await res.json() as T;
  }

  public getBackendStatus(): boolean {
    return this.isOnlineWithBackend;
  }

  // --- SITES ---
  public async getSites(): Promise<Site[]> {
    const data = await this.request<{ items: Array<{ site_id: string; name: string; city: string; latitude: number; longitude: number }> }>('/sites');
    return data.items.map(site => ({ ...site, lat: site.latitude, lon: site.longitude, soil_type: 'unknown', speed_limit_kmh: 10 }));
  }

  // --- MACHINES ---
  public async getMachines(): Promise<Machine[]> {
    const data = await this.request<{ items: Machine[] }>('/machines');
    return data.items.map(machine => ({ ...machine, reference_model: machine.machine_class, engine_hours_at_start: 0, commission_year: 0 }));
  }

  // --- OPERATORS ---
  public async getOperators(): Promise<Operator[]> {
    const data = await this.request<{ items: Array<Operator & { certifications: string[] }> }>('/operators');
    return data.items.map(operator => ({ ...operator, shift: 'Day Shift (08:00 - 17:00)' }));
  }

  // --- TASKS ---
  public async getTasks(): Promise<Task[]> {
    const data = await this.request<{ items: Array<Record<string, unknown>> }>('/tasks');
    return data.items.map(task => this.mapTask(task));
  }

  private mapTask(task: Record<string, unknown>): Task {
    const status = task.status === 'scheduled' ? 'pending' : task.status as Task['status'];
    return { task_id: String(task.id), task_type: String(task.task_type), site_id: String(task.site_id), machine_id: String(task.machine_id || ''), operator_id: String(task.operator_id || ''), start_time: String(task.created_at), planned_duration_min: Number(task.planned_duration_min), quantity: 0, quantity_unit: 'unit', status, notes: task.notes ? String(task.notes) : undefined };
  }

  public async createTask(newTask: Omit<Task, 'task_id'>): Promise<Task> {
    const created = await this.request<Record<string, unknown>>('/tasks', { method: 'POST', body: JSON.stringify({ task_type: newTask.task_type, site_id: newTask.site_id, machine_id: newTask.machine_id, operator_id: newTask.operator_id, planned_duration_min: newTask.planned_duration_min, notes: newTask.notes }) });
    return this.mapTask(created);
  }

  public async updateTaskStatus(taskId: string, status: Task['status']): Promise<Task | null> {
    const action = status === 'completed' ? 'complete' : status === 'in_progress' ? 'start' : undefined;
    if (!action) return null;
    const updated = await this.request<Record<string, unknown>>(`/tasks/${taskId}/${action}`, { method: 'POST' });
    return this.mapTask(updated);
  }

  // --- ALERTS ---
  public async getAlerts(): Promise<SafetyAlert[]> {
    const data = await this.request<{ items: Array<Record<string, unknown>> }>('/alerts');
    return data.items.map(alert => ({ alert_id: String(alert.alert_id || `${alert.alert_code}-${alert.started_at}`), machine_id: String(alert.machine_id), operator_id: String(alert.operator_id || ''), site_id: String(alert.site_id), alert_code: String(alert.alert_code), severity: alert.severity as SafetyAlert['severity'], message: String(alert.alert_code), start: String(alert.started_at), end: alert.ended_at ? String(alert.ended_at) : undefined, duration_min: Number(alert.duration_min), acknowledged: false }));
  }

  public async acknowledgeAlert(alertId: string): Promise<void> {
    void alertId;
  }

  // --- INCIDENTS ---
  public async getIncidents(): Promise<Incident[]> {
    const data = await this.request<{ items: Array<Record<string, unknown>> }>('/incidents');
    return data.items.map(incident => ({ incident_id: String(incident.id), site_id: String(incident.site_id), machine_id: String(incident.machine_id || ''), operator_id: String(incident.operator_id || ''), incident_type: String(incident.category), severity: incident.severity as Incident['severity'], description: String(incident.description), timestamp: String(incident.created_at), status: 'reported' }));
  }

  public async reportIncident(incident: Omit<Incident, 'incident_id' | 'timestamp' | 'status'>): Promise<Incident> {
    const created = await this.request<Record<string, unknown>>('/incidents', { method: 'POST', body: JSON.stringify({ site_id: incident.site_id, machine_id: incident.machine_id, operator_id: incident.operator_id, category: incident.incident_type, severity: incident.severity, description: incident.description }) });
    return { ...incident, incident_id: String(created.id), timestamp: String(created.created_at), status: 'reported' };
  }

  // --- TRAINING ---
  public async getTrainingRecords(operatorId: string): Promise<TrainingRecord[]> {
    const records = await this.request<Array<Record<string, unknown>>>(`/operators/${operatorId}/training`);
    return records.map(record => ({ record_id: `${operatorId}-${String(record.course_name)}`, operator_id: String(record.operator_id), course_name: String(record.course_name), valid_from: '', valid_until: record.expires_at ? String(record.expires_at) : undefined, completed: Boolean(record.completed), score_pct: 0, is_expired: Boolean(record.expires_at && new Date(String(record.expires_at)).getTime() < Date.now()) }));
  }

  // --- 2-HOUR SUMMARIES ---
  public async getSummaries(): Promise<TwoHourSummary[]> {
    return [];
  }

  // --- ENERGY POINTS ---
  public async getEnergyPoints(): Promise<EnergyPoint[]> {
    return [];
  }

  public async getLatestTelemetry(machineId: string): Promise<Record<string, unknown> | null> {
    try {
      const response = await fetch(`/ingest/telemetry/latest?machine_id=${encodeURIComponent(machineId)}`);
      if (!response.ok) return null;
      return await response.json() as Record<string, unknown>;
    } catch {
      return null;
    }
  }

  // --- SMART TASK MATCHER ---
  public async computeTaskMatches(
    taskType: string,
    quantity: number,
    siteId: string
  ): Promise<AssignmentSuggestion[]> {
    const data = await this.request<{ suggestions: Array<{ operator_id: string; machine_id: string; estimated_duration_min: number; is_certified: boolean; score: number; reason: string }> }>('/predict/assignment', { method: 'POST', body: JSON.stringify({ site_id: siteId, task_duration_min: Math.max(1, quantity), task_type: taskType }) });
    return data.suggestions.map(suggestion => ({ operator_id: suggestion.operator_id, operator_name: suggestion.operator_id, machine_id: suggestion.machine_id, machine_model: suggestion.machine_id, is_certified: suggestion.is_certified, missing_certifications: suggestion.is_certified ? [] : [suggestion.reason], estimated_duration_min: suggestion.estimated_duration_min, confidence_score: suggestion.score, energy_sufficient: true, ranking_score: Math.round(suggestion.score * 100) }));
  }
}

export const api = new ApiService();
