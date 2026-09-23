import React from 'react';
import { useAuth } from '../../context/AuthContext';
import { useFleet } from '../../context/FleetContext';
import { Fuel, BatteryCharging, Zap, ArrowRight, CheckCircle, AlertTriangle } from 'lucide-react';

export const EnergyAdvisory: React.FC = () => {
  const { activeMachine } = useAuth();
  const { currentTelemetry, energyPoints } = useFleet();

  const isElectric = activeMachine.powertrain === 'electric';
  const level = isElectric ? (currentTelemetry.battery_soc_pct || 65) : (currentTelemetry.fuel_level_pct || 75);
  const isLow = level < 25;

  // Calculate projected run time
  // If electric: 300 kWh * level% / power_kw
  // If diesel: tank_l * level% / fuel_rate_lph
  const projectedMinutes = isElectric
    ? Math.round(((activeMachine.battery_kwh || 300) * (level / 100)) / ((currentTelemetry.power_kw || 75) / 60))
    : Math.round(((activeMachine.fuel_tank_l || 300) * (level / 100)) / ((currentTelemetry.fuel_rate_lph || 18) / 60));

  // Find nearest energy point for this site
  const siteEnergyPoints = (energyPoints || []).filter(ep => ep.site_id === activeMachine.site_id);
  const recommendedPoint = isElectric 
    ? siteEnergyPoints.find(ep => ep.type === 'dc_fast_charger') || siteEnergyPoints[0] || {
        point_id: 'S01-DC1',
        site_id: 'S01',
        type: 'dc_fast_charger',
        name: 'OMR Supercharge Pod 1',
        max_rate: 60.0,
        status: 'available',
        lat: 12.9002,
        lon: 80.2290
      }
    : siteEnergyPoints.find(ep => ep.type === 'fuel_bowser') || siteEnergyPoints[0] || {
        point_id: 'S01-FB1',
        site_id: 'S01',
        type: 'fuel_bowser',
        name: 'Metro North Mobile Bowser',
        max_rate: 120,
        status: 'available',
        lat: 12.9022,
        lon: 80.2270
      };

  return (
    <div className="bg-cat-panel border border-cat-border rounded-xl p-4 shadow-cat">
      <div className="flex items-center justify-between border-b border-cat-border pb-2.5 mb-3">
        <div className="flex items-center space-x-2">
          {isElectric ? (
            <BatteryCharging className="w-4 h-4 text-cyan-400" />
          ) : (
            <Fuel className="w-4 h-4 text-cat-yellow" />
          )}
          <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-200">
            {isElectric ? 'EV Battery & Fast Charge Planning' : 'Fuel Burn & Bowser Allocation'}
          </span>
        </div>
        <span className={`text-[11px] font-mono font-bold uppercase px-2 py-0.5 rounded ${
          isLow ? 'bg-rose-950 text-rose-400 border border-rose-800' : 'bg-emerald-950 text-emerald-400 border border-emerald-800'
        }`}>
          {isLow ? 'REFILL/CHARGE REQUIRED' : 'RANGE SUFFICIENT'}
        </span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 mb-3">
        {/* Usable Capacity */}
        <div className="bg-cat-dark p-2.5 rounded border border-cat-border">
          <div className="text-[10px] font-mono text-slate-400">USABLE STATE</div>
          <div className="text-base font-bold font-mono text-white mt-0.5">
            {level.toFixed(1)}% {isElectric ? `(${((activeMachine.battery_kwh || 300) * level / 100).toFixed(0)} kWh)` : `(${((activeMachine.fuel_tank_l || 300) * level / 100).toFixed(0)} L)`}
          </div>
        </div>

        {/* Burn Rate */}
        <div className="bg-cat-dark p-2.5 rounded border border-cat-border">
          <div className="text-[10px] font-mono text-slate-400">CURRENT DRAW RATE</div>
          <div className="text-base font-bold font-mono text-white mt-0.5">
            {isElectric 
              ? `${(currentTelemetry.power_kw || 78).toFixed(0)} kW` 
              : `${(currentTelemetry.fuel_rate_lph || 17.5).toFixed(1)} L/h`}
          </div>
        </div>

        {/* Projected Runtime */}
        <div className="bg-cat-dark p-2.5 rounded border border-cat-border col-span-2 sm:col-span-1">
          <div className="text-[10px] font-mono text-slate-400">TIME UNTIL DEPLETION</div>
          <div className={`text-base font-bold font-mono mt-0.5 ${projectedMinutes < 60 ? 'text-amber-400' : 'text-emerald-400'}`}>
            ~{projectedMinutes} mins
          </div>
        </div>
      </div>

      {/* Charge or Bowser recommendation */}
      {recommendedPoint && (
        <div className="bg-cat-dark/70 p-3 rounded border border-cat-border flex items-center justify-between text-xs">
          <div>
            <div className="text-[10px] font-mono uppercase text-slate-400">
              {isElectric ? 'Target DC Fast Charger' : 'Designated Refuel Station'}
            </div>
            <div className="text-white font-bold flex items-center space-x-1.5 mt-0.5">
              <span>{recommendedPoint.name}</span>
              <span className="text-[10px] font-mono text-cat-yellow">[{recommendedPoint.point_id}]</span>
            </div>
            <div className="text-slate-400 text-[11px] font-mono mt-0.5">
              Status: <span className="text-emerald-400 font-semibold uppercase">{recommendedPoint.status}</span> · Capacity: {recommendedPoint.max_rate} {isElectric ? 'kW DC' : 'L/min'}
            </div>
          </div>

          <div className="text-right">
            <div className="text-[10px] font-mono text-slate-400">EST. REFILL/CHARGE TIME</div>
            <div className="text-cat-yellow font-mono font-bold text-sm">
              {isElectric ? '32 mins (to 85%)' : '6 mins (full)'}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
