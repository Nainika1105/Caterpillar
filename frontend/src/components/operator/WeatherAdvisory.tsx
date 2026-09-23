import React from 'react';
import { useAuth } from '../../context/AuthContext';
import { useFleet } from '../../context/FleetContext';
import { CloudRain, Sun, Compass, AlertCircle, Wind } from 'lucide-react';

export const WeatherAdvisory: React.FC = () => {
  const { activeMachine } = useAuth();
  const { sites, currentTelemetry } = useFleet();

  const currentSite = sites.find(s => s.site_id === activeMachine.site_id) || sites[0] || {
    site_id: 'S01',
    name: 'Chennai OMR Metro Corridor',
    city: 'Chennai',
    lat: 12.9010,
    lon: 80.2279,
    soil_type: 'Sandy Clay',
    speed_limit_kmh: 10.0
  };

  const hasRain = (currentTelemetry?.rain_mm_hr || 0) > 0;
  const isHighHeat = (currentTelemetry?.ambient_temp_c || 0) >= 35.0;

  // ML / Weather impact factor on task duration
  const soilPenaltyPercent = (currentSite.soil_type || '').toLowerCase().includes('rocky')
    ? 22
    : (currentSite.soil_type || '').toLowerCase().includes('clay')
      ? 14
      : 8;

  const weatherDelayPercent = hasRain ? soilPenaltyPercent + 15 : soilPenaltyPercent;

  return (
    <div className="bg-cat-panel border border-cat-border rounded-xl p-4 shadow-cat">
      <div className="flex items-center justify-between border-b border-cat-border pb-2.5 mb-3">
        <div className="flex items-center space-x-2">
          {hasRain ? (
            <CloudRain className="w-4 h-4 text-cyan-400" />
          ) : (
            <Sun className="w-4 h-4 text-cat-yellow" />
          )}
          <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-200">
            Site Climate & Ground Advisory
          </span>
        </div>
        <span className="text-[11px] font-mono text-cat-yellow font-bold">
          {currentSite.name} ({currentSite.site_id})
        </span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 mb-3">
        {/* Ambient Temperature */}
        <div className="bg-cat-dark p-2.5 rounded border border-cat-border">
          <div className="text-[10px] font-mono text-slate-400">AMBIENT TEMP</div>
          <div className="text-base font-bold font-mono text-white mt-0.5">
            {currentTelemetry.ambient_temp_c.toFixed(1)}°C
          </div>
        </div>

        {/* Rain Rate */}
        <div className="bg-cat-dark p-2.5 rounded border border-cat-border">
          <div className="text-[10px] font-mono text-slate-400">PRECIPITATION</div>
          <div className={`text-base font-bold font-mono mt-0.5 ${hasRain ? 'text-cyan-400' : 'text-slate-300'}`}>
            {currentTelemetry.rain_mm_hr.toFixed(1)} mm/h
          </div>
        </div>

        {/* Soil Condition */}
        <div className="bg-cat-dark p-2.5 rounded border border-cat-border">
          <div className="text-[10px] font-mono text-slate-400">GROUND SUBSTRATE</div>
          <div className="text-xs font-bold font-mono text-cat-yellow mt-1 truncate">
            {currentSite.soil_type}
          </div>
        </div>

        {/* Speed Limit */}
        <div className="bg-cat-dark p-2.5 rounded border border-cat-border">
          <div className="text-[10px] font-mono text-slate-400">SITE SPEED CAP</div>
          <div className="text-base font-bold font-mono text-white mt-0.5">
            {currentSite.speed_limit_kmh} km/h
          </div>
        </div>
      </div>

      {/* Ground resistance & time estimator impact */}
      <div className="p-2.5 rounded bg-cat-dark/70 border border-cat-yellow/30 flex items-start space-x-2.5">
        <AlertCircle className="w-4 h-4 text-cat-yellow shrink-0 mt-0.5" />
        <div className="text-xs leading-relaxed text-slate-300">
          <span className="font-semibold text-cat-yellow">Ground Resistance Impact (+{weatherDelayPercent}%): </span>
          {currentSite.soil_type} combined with ambient moisture requires higher breakout force. 
          Bucket fill factor calculated at 88%. Machine stability alerts active.
        </div>
      </div>
    </div>
  );
};
