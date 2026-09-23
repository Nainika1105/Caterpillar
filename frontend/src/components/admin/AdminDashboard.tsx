import React, { useState } from 'react';
import { FleetMap } from './FleetMap';
import { MachineGrid } from './MachineGrid';
import { AlertFeed } from './AlertFeed';
import { TaskDispatcher } from './TaskDispatcher';
import { AnomalyDashboard } from './AnomalyDashboard';
import { OperatorAnalytics } from './OperatorAnalytics';
import { useFleet } from '../../context/FleetContext';
import { 
  MapPin, 
  LayoutGrid, 
  ShieldAlert, 
  ClipboardList, 
  Brain, 
  Users, 
  Activity,
  CheckCircle2,
  FileWarning
} from 'lucide-react';

export const AdminDashboard: React.FC = () => {
  const { machines, alerts, incidents, tasks } = useFleet();
  const [activeTab, setActiveTab] = useState<'fleet' | 'alerts' | 'tasks' | 'anomalies' | 'analytics'>('fleet');

  const activeAlertsCount = alerts.filter(a => !a.acknowledged).length;

  return (
    <div className="space-y-4 max-w-7xl mx-auto pb-12">
      {/* Top Fleet KPI Metric Ribbon */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="bg-cat-panel border border-cat-border p-3 rounded-xl shadow-cat">
          <div className="text-[11px] font-mono text-slate-400 uppercase">Total Fleet Units</div>
          <div className="text-2xl font-black font-mono text-white mt-1 flex items-center justify-between">
            <span>{machines.length} Units</span>
            <Activity className="w-5 h-5 text-cat-yellow" />
          </div>
          <div className="text-[10px] font-mono text-slate-400 mt-1">10 Diesel · 2 Electric</div>
        </div>

        <div className="bg-cat-panel border border-cat-border p-3 rounded-xl shadow-cat">
          <div className="text-[11px] font-mono text-slate-400 uppercase">Active Safety Alerts</div>
          <div className="text-2xl font-black font-mono mt-1 flex items-center justify-between">
            <span className={activeAlertsCount > 0 ? 'text-rose-400' : 'text-emerald-400'}>
              {activeAlertsCount} Active
            </span>
            <ShieldAlert className={`w-5 h-5 ${activeAlertsCount > 0 ? 'text-rose-400 animate-pulse' : 'text-emerald-400'}`} />
          </div>
          <div className="text-[10px] font-mono text-slate-400 mt-1">Sub-second MQTT ingest</div>
        </div>

        <div className="bg-cat-panel border border-cat-border p-3 rounded-xl shadow-cat">
          <div className="text-[11px] font-mono text-slate-400 uppercase">Shift Tasks Dispatched</div>
          <div className="text-2xl font-black font-mono text-white mt-1 flex items-center justify-between">
            <span>{tasks.filter(t => t.status === 'in_progress').length} In-Progress</span>
            <ClipboardList className="w-5 h-5 text-cat-yellow" />
          </div>
          <div className="text-[10px] font-mono text-slate-400 mt-1">{tasks.length} Total Registered</div>
        </div>

        <div className="bg-cat-panel border border-cat-border p-3 rounded-xl shadow-cat">
          <div className="text-[11px] font-mono text-slate-400 uppercase">Safety Incidents Logged</div>
          <div className="text-2xl font-black font-mono text-white mt-1 flex items-center justify-between">
            <span>{incidents.length} Reports</span>
            <FileWarning className="w-5 h-5 text-amber-400" />
          </div>
          <div className="text-[10px] font-mono text-slate-400 mt-1">Local Edge + Cloud synced</div>
        </div>
      </div>

      {/* Admin Tab Navigation */}
      <div className="flex flex-wrap items-center gap-1.5 bg-cat-panel p-1.5 rounded-xl border border-cat-border shadow-cat text-xs">
        <button
          onClick={() => setActiveTab('fleet')}
          className={`flex items-center space-x-1.5 px-3.5 py-2 rounded-lg font-mono font-bold transition-all ${
            activeTab === 'fleet'
              ? 'bg-cat-yellow text-black shadow'
              : 'text-slate-300 hover:text-white hover:bg-cat-hover'
          }`}
        >
          <MapPin className="w-4 h-4" />
          <span>Fleet Map & Equipment</span>
        </button>

        <button
          onClick={() => setActiveTab('alerts')}
          className={`flex items-center space-x-1.5 px-3.5 py-2 rounded-lg font-mono font-bold transition-all relative ${
            activeTab === 'alerts'
              ? 'bg-cat-yellow text-black shadow'
              : 'text-slate-300 hover:text-white hover:bg-cat-hover'
          }`}
        >
          <ShieldAlert className="w-4 h-4" />
          <span>Live Safety Feed</span>
          {activeAlertsCount > 0 && (
            <span className="w-2 h-2 rounded-full bg-rose-500 animate-ping ml-1" />
          )}
        </button>

        <button
          onClick={() => setActiveTab('tasks')}
          className={`flex items-center space-x-1.5 px-3.5 py-2 rounded-lg font-mono font-bold transition-all ${
            activeTab === 'tasks'
              ? 'bg-cat-yellow text-black shadow'
              : 'text-slate-300 hover:text-white hover:bg-cat-hover'
          }`}
        >
          <ClipboardList className="w-4 h-4" />
          <span>Smart Task Matcher</span>
        </button>

        <button
          onClick={() => setActiveTab('anomalies')}
          className={`flex items-center space-x-1.5 px-3.5 py-2 rounded-lg font-mono font-bold transition-all ${
            activeTab === 'anomalies'
              ? 'bg-cat-yellow text-black shadow'
              : 'text-slate-300 hover:text-white hover:bg-cat-hover'
          }`}
        >
          <Brain className="w-4 h-4" />
          <span>AI Anomaly Detection</span>
        </button>

        <button
          onClick={() => setActiveTab('analytics')}
          className={`flex items-center space-x-1.5 px-3.5 py-2 rounded-lg font-mono font-bold transition-all ${
            activeTab === 'analytics'
              ? 'bg-cat-yellow text-black shadow'
              : 'text-slate-300 hover:text-white hover:bg-cat-hover'
          }`}
        >
          <Users className="w-4 h-4" />
          <span>Operator Analytics</span>
        </button>
      </div>

      {/* Main Tab Panels */}
      {activeTab === 'fleet' && (
        <div className="space-y-4">
          <FleetMap />
          <MachineGrid />
        </div>
      )}

      {activeTab === 'alerts' && <AlertFeed />}
      {activeTab === 'tasks' && <TaskDispatcher />}
      {activeTab === 'anomalies' && <AnomalyDashboard />}
      {activeTab === 'analytics' && <OperatorAnalytics />}
    </div>
  );
};
