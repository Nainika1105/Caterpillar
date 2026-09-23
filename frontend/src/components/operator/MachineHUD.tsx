import React from 'react';
import { useAuth } from '../../context/AuthContext';
import { useFleet } from '../../context/FleetContext';
import { 
  Gauge, 
  Fuel, 
  BatteryCharging, 
  Zap, 
  Thermometer, 
  Radar, 
  Activity, 
  AlertOctagon,
  CheckCircle2,
  Clock
} from 'lucide-react';

export const MachineHUD: React.FC = () => {
  const { activeMachine } = useAuth();
  const { currentTelemetry } = useFleet();

  const isElectric = activeMachine.powertrain === 'electric';
  const isMoving = currentTelemetry.ground_speed_kmh > 0.5;
  const isUnbelted = currentTelemetry.seatbelt_status === 'unfastened';
  const unbeltedMoving = isMoving && isUnbelted;

  // Proximity zone styling
  const proxZone = currentTelemetry.proximity_min_m < 2.0 
    ? 'danger'
    : currentTelemetry.proximity_min_m < 5.0 
      ? 'caution'
      : 'clear';

  return (
    <div className="bg-cat-panel border border-cat-border rounded-xl p-4 shadow-cat">
      {/* Header bar */}
      <div className="flex items-center justify-between border-b border-cat-border/80 pb-3 mb-4">
        <div className="flex items-center space-x-3">
          <div className="px-2.5 py-1 bg-black rounded border border-cat-yellow/30 font-mono text-cat-yellow font-bold text-sm">
            {activeMachine.machine_id}
          </div>
          <div>
            <div className="text-white font-bold text-sm tracking-wide flex items-center space-x-2">
              <span>{activeMachine.reference_model}</span>
              <span className={`text-[10px] px-2 py-0.5 rounded font-mono uppercase font-semibold ${
                isElectric ? 'bg-cyan-950 text-cyan-400 border border-cyan-800' : 'bg-amber-950 text-amber-400 border border-amber-800'
              }`}>
                {isElectric ? '⚡ High-Voltage Electric' : '⛽ Tier 4 Diesel'}
              </span>
            </div>
            <div className="text-slate-400 text-xs font-mono">
              Engine Hours: {currentTelemetry.engine_hours.toFixed(1)} hrs · State: <span className="uppercase text-cat-yellow font-semibold">{currentTelemetry.state}</span>
            </div>
          </div>
        </div>

        {/* Seatbelt Status Indicator (CRITICAL GLANCEABLE SAFETY) */}
        <div className={`flex items-center space-x-2 px-3.5 py-2 rounded-lg border font-mono font-bold text-xs transition-all ${
          unbeltedMoving
            ? 'bg-rose-600 text-white border-rose-400 animate-pulse-alert shadow-danger-glow'
            : isUnbelted
              ? 'bg-amber-500/20 text-amber-400 border-amber-500/50'
              : 'bg-emerald-950/60 text-emerald-400 border-emerald-800'
        }`}>
          {isUnbelted ? (
            <AlertOctagon className="w-5 h-5 animate-bounce" />
          ) : (
            <CheckCircle2 className="w-5 h-5" />
          )}
          <div className="text-left">
            <div className="text-[10px] uppercase opacity-75">CAB SEATBELT</div>
            <div className="text-xs uppercase">{isUnbelted ? 'UNFASTENED' : 'FASTENED (SAFE)'}</div>
          </div>
        </div>
      </div>

      {/* Main Gauges Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
        {/* Ground Speed Gauge */}
        <div className="bg-cat-dark/90 border border-cat-border rounded-lg p-3 relative overflow-hidden flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 text-xs font-mono">
            <span>GROUND SPEED</span>
            <Activity className="w-3.5 h-3.5 text-cat-yellow" />
          </div>
          <div className="my-2 text-center">
            <span className="text-3xl font-black font-mono tracking-tight text-white">
              {currentTelemetry.ground_speed_kmh.toFixed(1)}
            </span>
            <span className="text-xs text-slate-400 font-mono ml-1">km/h</span>
          </div>
          <div className="flex items-center justify-between text-[10px] text-slate-500 font-mono border-t border-cat-border/50 pt-1">
            <span>LIMIT: 10 km/h</span>
            <span className={currentTelemetry.ground_speed_kmh > 10 ? 'text-rose-400 font-bold' : 'text-emerald-400'}>
              {currentTelemetry.ground_speed_kmh > 10 ? 'OVERSPEED' : 'COMPLIANT'}
            </span>
          </div>
        </div>

        {/* Engine RPM Tachometer */}
        <div className="bg-cat-dark/90 border border-cat-border rounded-lg p-3 relative overflow-hidden flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 text-xs font-mono">
            <span>ENGINE RPM</span>
            <Gauge className="w-3.5 h-3.5 text-cat-yellow" />
          </div>
          <div className="my-2 text-center">
            <span className="text-3xl font-black font-mono tracking-tight text-cat-yellow">
              {currentTelemetry.engine_rpm}
            </span>
            <span className="text-xs text-slate-400 font-mono ml-1">rpm</span>
          </div>
          <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
            <div 
              className="bg-cat-yellow h-full transition-all duration-300"
              style={{ width: `${Math.min(100, (currentTelemetry.engine_rpm / 2200) * 100)}%` }}
            />
          </div>
        </div>

        {/* Energy (Fuel % or Battery SOC %) */}
        <div className="bg-cat-dark/90 border border-cat-border rounded-lg p-3 relative overflow-hidden flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 text-xs font-mono">
            <span>{isElectric ? 'BATTERY SOC' : 'FUEL LEVEL'}</span>
            {isElectric ? <BatteryCharging className="w-3.5 h-3.5 text-cyan-400" /> : <Fuel className="w-3.5 h-3.5 text-cat-yellow" />}
          </div>
          <div className="my-2 text-center">
            <span className={`text-3xl font-black font-mono tracking-tight ${
              (isElectric ? (currentTelemetry.battery_soc_pct || 65) : (currentTelemetry.fuel_level_pct || 75)) < 20
                ? 'text-rose-400'
                : isElectric ? 'text-cyan-300' : 'text-white'
            }`}>
              {(isElectric ? (currentTelemetry.battery_soc_pct || 65) : (currentTelemetry.fuel_level_pct || 75)).toFixed(1)}
            </span>
            <span className="text-xs text-slate-400 font-mono ml-1">%</span>
          </div>
          <div className="flex items-center justify-between text-[10px] text-slate-400 font-mono border-t border-cat-border/50 pt-1">
            <span>RATE</span>
            <span className="text-slate-200">
              {isElectric 
                ? `${(currentTelemetry.power_kw || 78).toFixed(0)} kW` 
                : `${(currentTelemetry.fuel_rate_lph || 17.5).toFixed(1)} L/h`}
            </span>
          </div>
        </div>

        {/* Hydraulic Pressure & Oil Temp */}
        <div className="bg-cat-dark/90 border border-cat-border rounded-lg p-3 relative overflow-hidden flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 text-xs font-mono">
            <span>HYDRAULICS</span>
            <Zap className="w-3.5 h-3.5 text-cat-yellow" />
          </div>
          <div className="my-2 text-center">
            <span className="text-3xl font-black font-mono tracking-tight text-white">
              {currentTelemetry.hydraulic_pressure_bar}
            </span>
            <span className="text-xs text-slate-400 font-mono ml-1">bar</span>
          </div>
          <div className="flex items-center justify-between text-[10px] text-slate-400 font-mono border-t border-cat-border/50 pt-1">
            <span>OIL TEMP</span>
            <span className="text-slate-200">{currentTelemetry.hydraulic_oil_temp_c.toFixed(1)}°C</span>
          </div>
        </div>

        {/* Engine Coolant Temp */}
        <div className="bg-cat-dark/90 border border-cat-border rounded-lg p-3 relative overflow-hidden flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 text-xs font-mono">
            <span>COOLANT TEMP</span>
            <Thermometer className="w-3.5 h-3.5 text-cat-yellow" />
          </div>
          <div className="my-2 text-center">
            <span className={`text-3xl font-black font-mono tracking-tight ${
              currentTelemetry.coolant_temp_c > 95 ? 'text-rose-400 animate-pulse' : 'text-white'
            }`}>
              {currentTelemetry.coolant_temp_c.toFixed(1)}
            </span>
            <span className="text-xs text-slate-400 font-mono ml-1">°C</span>
          </div>
          <div className="flex items-center justify-between text-[10px] text-slate-400 font-mono border-t border-cat-border/50 pt-1">
            <span>THRESHOLD</span>
            <span className="text-slate-300">95.0°C</span>
          </div>
        </div>

        {/* 360° Proximity Radar Arc */}
        <div className={`border rounded-lg p-3 relative overflow-hidden flex flex-col justify-between transition-colors ${
          proxZone === 'danger'
            ? 'bg-rose-950/80 border-rose-500 animate-pulse-alert'
            : proxZone === 'caution'
              ? 'bg-amber-950/60 border-amber-500'
              : 'bg-cat-dark/90 border-cat-border'
        }`}>
          <div className="flex items-center justify-between text-xs font-mono">
            <span className={proxZone === 'danger' ? 'text-rose-300 font-bold' : 'text-slate-400'}>
              PROXIMITY RADAR
            </span>
            <Radar className={`w-3.5 h-3.5 ${proxZone === 'danger' ? 'text-rose-400 animate-spin' : 'text-cat-yellow'}`} />
          </div>
          <div className="my-2 text-center">
            <span className={`text-3xl font-black font-mono tracking-tight ${
              proxZone === 'danger' ? 'text-rose-200' : proxZone === 'caution' ? 'text-amber-300' : 'text-emerald-400'
            }`}>
              {currentTelemetry.proximity_min_m.toFixed(1)}
            </span>
            <span className="text-xs text-slate-400 font-mono ml-1">m</span>
          </div>
          <div className="flex items-center justify-between text-[10px] font-mono border-t border-cat-border/50 pt-1">
            <span>SWING ZONE</span>
            <span className={`font-bold uppercase ${
              proxZone === 'danger' ? 'text-rose-300' : proxZone === 'caution' ? 'text-amber-400' : 'text-emerald-400'
            }`}>
              {proxZone === 'danger' ? 'DANGER ZONE' : proxZone === 'caution' ? 'CAUTION ZONE' : 'CLEAR'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
