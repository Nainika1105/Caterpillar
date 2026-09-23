import React, { useState } from 'react';
import { useFleet } from '../../context/FleetContext';
import { useAuth } from '../../context/AuthContext';
import { Machine, TwoHourSummary } from '../../types';
import { 
  Cpu, 
  Fuel, 
  BatteryCharging, 
  Clock, 
  AlertTriangle, 
  CheckCircle, 
  Activity, 
  ArrowUpRight 
} from 'lucide-react';

export const MachineGrid: React.FC = () => {
  const { machines, summaries, alerts, currentTelemetry } = useFleet();
  const { setActiveMachine, setRole } = useAuth();
  const [filter, setFilter] = useState<'all' | 'diesel' | 'electric'>('all');

  const filtered = machines.filter(m => {
    if (filter === 'diesel') return m.powertrain === 'diesel';
    if (filter === 'electric') return m.powertrain === 'electric';
    return true;
  });

  return (
    <div className="bg-cat-panel border border-cat-border rounded-xl p-4 shadow-cat">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-cat-border pb-3 mb-4">
        <div>
          <h3 className="text-sm font-bold font-mono uppercase tracking-wider text-white flex items-center space-x-2">
            <span>Fleet Equipment Status & 2-Hour Continuous Aggregates</span>
          </h3>
          <p className="text-xs text-slate-400 font-mono mt-0.5">
            TimescaleDB rolling 2-hour telemetry window: idle ratios, burn consumption, and safety compliance.
          </p>
        </div>

        {/* Filter Pills */}
        <div className="flex items-center space-x-1.5 bg-cat-dark p-1 rounded-lg border border-cat-border text-xs">
          <button
            onClick={() => setFilter('all')}
            className={`px-3 py-1 rounded font-mono font-medium transition-colors ${
              filter === 'all' ? 'bg-cat-yellow text-black font-bold' : 'text-slate-400 hover:text-white'
            }`}
          >
            All (12)
          </button>
          <button
            onClick={() => setFilter('diesel')}
            className={`px-3 py-1 rounded font-mono font-medium transition-colors ${
              filter === 'diesel' ? 'bg-cat-yellow text-black font-bold' : 'text-slate-400 hover:text-white'
            }`}
          >
            Diesel (10)
          </button>
          <button
            onClick={() => setFilter('electric')}
            className={`px-3 py-1 rounded font-mono font-medium transition-colors ${
              filter === 'electric' ? 'bg-cat-yellow text-black font-bold' : 'text-slate-400 hover:text-white'
            }`}
          >
            ⚡ Electric (2)
          </button>
        </div>
      </div>

      {/* Grid of 12 Machine Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3.5">
        {filtered.map(machine => {
          const isElectric = machine.powertrain === 'electric';
          const summary = summaries.find(s => s.machine_id === machine.machine_id);
          const activeAlert = alerts.find(a => a.machine_id === machine.machine_id && !a.acknowledged);

          // Real-time telemetry overlay for active machine
          const isSelected = machine.machine_id === currentTelemetry.machine_id;

          return (
            <div
              key={machine.machine_id}
              className={`bg-cat-dark/95 border rounded-lg p-3.5 relative overflow-hidden transition-all hover:border-cat-yellow/60 flex flex-col justify-between ${
                activeAlert 
                  ? 'border-rose-500/70 shadow-lg' 
                  : isSelected 
                    ? 'border-cat-yellow/80 shadow-cat-glow' 
                    : 'border-cat-border'
              }`}
            >
              {/* Card Header */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-2">
                    <span className="font-mono font-bold text-sm text-cat-yellow">
                      {machine.machine_id}
                    </span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded font-mono uppercase font-bold ${
                      isElectric ? 'bg-cyan-950 text-cyan-400 border border-cyan-800' : 'bg-slate-800 text-slate-300'
                    }`}>
                      {isElectric ? '⚡ EV' : '⛽ DIESEL'}
                    </span>
                  </div>

                  <span className="text-[11px] font-mono text-slate-400">
                    {machine.site_id}
                  </span>
                </div>

                <div className="text-xs font-bold text-white tracking-wide truncate">
                  {machine.reference_model}
                </div>
                <div className="text-[11px] text-slate-400 font-mono mb-3">
                  Primary OP: {machine.primary_operator_id || 'Rotating'}
                </div>

                {/* 2-Hour Continuous Aggregates */}
                <div className="bg-cat-panel p-2.5 rounded border border-cat-border text-[11px] font-mono space-y-1.5 mb-3">
                  <div className="flex items-center justify-between text-slate-400">
                    <span>Operating / Idle (2h):</span>
                    <span className="text-white font-semibold">
                      {summary?.operating_hours_2h ?? 1.5}h / {summary?.idle_hours_2h ?? 0.5}h
                    </span>
                  </div>

                  <div className="flex items-center justify-between text-slate-400">
                    <span>{isElectric ? 'Energy Drawn:' : 'Fuel Consumed:'}</span>
                    <span className="text-cat-yellow font-semibold">
                      {summary?.fuel_or_kwh_consumed ?? 32.4} {summary?.unit || (isElectric ? 'kWh' : 'L')}
                    </span>
                  </div>

                  <div className="flex items-center justify-between text-slate-400">
                    <span>Load Cycles Completed:</span>
                    <span className="text-white font-semibold">{summary?.load_cycles ?? 84}</span>
                  </div>

                  <div className="flex items-center justify-between text-slate-400">
                    <span>Seatbelt Compliance:</span>
                    <span className={`font-semibold ${
                      (summary?.seatbelt_compliance_pct ?? 95) < 90 ? 'text-rose-400' : 'text-emerald-400'
                    }`}>
                      {(summary?.seatbelt_compliance_pct ?? 95.0).toFixed(1)}%
                    </span>
                  </div>
                </div>

                {/* Active Alert Banner if any */}
                {activeAlert && (
                  <div className="p-2 rounded bg-rose-950/80 border border-rose-800 text-[10px] font-mono text-rose-300 font-semibold mb-3 flex items-center space-x-1.5">
                    <AlertTriangle className="w-3.5 h-3.5 text-rose-400 shrink-0" />
                    <span className="truncate">{activeAlert.alert_code.toUpperCase()}: {activeAlert.message}</span>
                  </div>
                )}
              </div>

              {/* Jump to In-Cab button */}
              <button
                onClick={() => {
                  setActiveMachine(machine);
                  setRole('operator');
                }}
                className="w-full py-1.5 px-2 rounded bg-cat-panel hover:bg-cat-hover border border-cat-border text-xs font-mono font-medium text-slate-300 hover:text-cat-yellow flex items-center justify-center space-x-1 transition-colors"
              >
                <span>Open Unit In Cab Tablet</span>
                <ArrowUpRight className="w-3.5 h-3.5" />
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
};
