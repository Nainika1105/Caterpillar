import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useFleet } from '../../context/FleetContext';
import { MachineHUD } from './MachineHUD';
import { CurrentTaskCard } from './CurrentTaskCard';
import { WeatherAdvisory } from './WeatherAdvisory';
import { EnergyAdvisory } from './EnergyAdvisory';
import { IncidentModal } from './IncidentModal';
import { ShieldAlert, Volume2, HardHat, FileWarning } from 'lucide-react';
import { cabAudio } from '../../services/voiceAlerts';

export const OperatorDashboard: React.FC = () => {
  const { activeOperator, activeMachine } = useAuth();
  const { currentTelemetry } = useFleet();
  const [isIncidentOpen, setIsIncidentOpen] = useState(false);

  return (
    <div className="space-y-4 max-w-7xl mx-auto pb-10">
      {/* Cab Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-cat-panel p-3.5 rounded-xl border border-cat-border shadow-cat">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-lg bg-cat-dark border border-cat-yellow/30 flex items-center justify-center text-cat-yellow font-black">
            <HardHat className="w-6 h-6" />
          </div>
          <div>
            <div className="text-white font-bold text-sm tracking-wide flex items-center space-x-2">
              <span>{activeOperator.name}</span>
              <span className="text-[10px] bg-slate-800 text-slate-300 font-mono px-2 py-0.5 rounded border border-slate-700">
                {activeOperator.operator_id}
              </span>
            </div>
            <div className="text-xs text-slate-400 font-mono">
              Certifications: {activeOperator.certifications.join(', ')} · Shift: {activeOperator.shift}
            </div>
          </div>
        </div>

        {/* Quick Cab Action Buttons */}
        <div className="flex items-center space-x-2">
          <button
            onClick={() => cabAudio.speak(`System check nominal. Unit ${activeMachine.machine_id} online. Seatbelt sensor active.`, 'check', 0)}
            className="flex items-center space-x-1.5 px-3 py-2 rounded-lg bg-cat-dark hover:bg-cat-hover border border-cat-border text-xs text-slate-300 font-semibold"
            title="Perform audio system voice check"
          >
            <Volume2 className="w-4 h-4 text-cat-yellow" />
            <span className="hidden sm:inline">Voice Test</span>
          </button>

          <button
            onClick={() => setIsIncidentOpen(true)}
            className="flex items-center space-x-1.5 px-4 py-2 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-xs font-bold uppercase tracking-wider shadow-md transition-transform active:scale-95"
          >
            <FileWarning className="w-4 h-4" />
            <span>Log Safety Incident</span>
          </button>
        </div>
      </div>

      {/* Machine Instrument HUD with Live CAN-bus metrics & Proximity */}
      <MachineHUD />

      {/* Operational Task Execution & Advisory Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left Column: Active Task (7 cols) */}
        <div className="lg:col-span-7">
          <CurrentTaskCard />
        </div>

        {/* Right Column: Climate & Energy Advisories (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          <WeatherAdvisory />
          <EnergyAdvisory />
        </div>
      </div>

      {/* Incident Modal */}
      <IncidentModal
        isOpen={isIncidentOpen}
        onClose={() => setIsIncidentOpen(false)}
      />
    </div>
  );
};
