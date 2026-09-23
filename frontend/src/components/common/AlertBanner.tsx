import React from 'react';
import { useFleet } from '../../context/FleetContext';
import { ShieldAlert, AlertTriangle, CheckCircle, Volume2 } from 'lucide-react';
import { cabAudio } from '../../services/voiceAlerts';

export const AlertBanner: React.FC = () => {
  const { criticalAlert, acknowledgeAlert, audioMuted } = useFleet();

  if (!criticalAlert) return null;

  const isCritical = criticalAlert.severity === 'critical';

  return (
    <div className={`relative overflow-hidden border-b-2 shadow-2xl transition-all duration-300 z-30 ${
      isCritical 
        ? 'bg-rose-950/95 border-rose-500 text-rose-100' 
        : 'bg-amber-950/95 border-amber-500 text-amber-100'
    }`}>
      {/* Animated Top Hazard Stripe Accent */}
      <div className={`h-1.5 w-full ${isCritical ? 'bg-rose-500' : 'bg-amber-500'} animate-pulse`} />

      <div className="max-w-7xl mx-auto px-4 py-3 flex flex-col md:flex-row items-center justify-between gap-3">
        <div className="flex items-center space-x-3 w-full md:w-auto">
          <div className={`p-2 rounded-lg ${
            isCritical ? 'bg-rose-600 text-white animate-bounce' : 'bg-amber-500 text-black'
          }`}>
            {isCritical ? <ShieldAlert className="w-6 h-6" /> : <AlertTriangle className="w-6 h-6" />}
          </div>
          
          <div>
            <div className="flex items-center space-x-2">
              <span className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded font-black tracking-wider ${
                isCritical ? 'bg-rose-500 text-white' : 'bg-amber-400 text-black'
              }`}>
                CAB SAFETY RULE: {criticalAlert.alert_code.toUpperCase().replace(/_/g, ' ')}
              </span>
              <span className="text-xs text-slate-300 font-mono">
                {new Date(criticalAlert.start).toLocaleTimeString()}
              </span>
            </div>
            
            <p className="text-sm md:text-base font-bold tracking-tight mt-0.5 font-sans">
              {criticalAlert.message}
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2.5 w-full md:w-auto justify-end">
          {/* Repeat voice button */}
          <button
            onClick={() => cabAudio.speak(criticalAlert.message, criticalAlert.alert_code, 0)}
            className="flex items-center space-x-1.5 px-3 py-2 rounded bg-black/40 hover:bg-black/60 border border-white/20 text-xs font-semibold"
            title="Replay Voice Alert"
          >
            <Volume2 className="w-3.5 h-3.5 text-cat-yellow" />
            <span className="hidden sm:inline">Replay Voice</span>
          </button>

          {/* Acknowledge Button */}
          <button
            onClick={() => acknowledgeAlert(criticalAlert.alert_id)}
            className={`flex items-center space-x-1.5 px-4 py-2 rounded font-bold text-xs uppercase tracking-wider transition-transform active:scale-95 shadow-md ${
              isCritical
                ? 'bg-rose-500 hover:bg-rose-400 text-white shadow-rose-900/50'
                : 'bg-amber-400 hover:bg-amber-300 text-black shadow-amber-900/50'
            }`}
          >
            <CheckCircle className="w-4 h-4" />
            <span>Acknowledge & Comply</span>
          </button>
        </div>
      </div>
    </div>
  );
};
