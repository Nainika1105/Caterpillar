import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useFleet } from '../../context/FleetContext';
import { 
  ShieldAlert, 
  Volume2, 
  VolumeX, 
  Wifi, 
  Cpu, 
  HardHat, 
  LayoutDashboard, 
  GraduationCap, 
  ChevronDown,
  AlertTriangle,
  Play
} from 'lucide-react';

export const Navbar: React.FC = () => {
  const { role, setRole, activeMachine, setActiveMachine, activeOperator, setActiveOperator } = useAuth();
  const { 
    machines, 
    operators, 
    audioMuted, 
    toggleAudioMute, 
    isBackendConnected, 
    triggerSimulationAlert 
  } = useFleet();

  const [showDemoMenu, setShowDemoMenu] = useState(false);

  return (
    <header className="bg-cat-panel border-b border-cat-border px-4 py-2.5 select-none sticky top-0 z-40 shadow-cat">
      <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-3">
        {/* Brand identity */}
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-2 bg-black px-2.5 py-1.5 rounded border border-cat-yellow/40">
            {/* CAT Triangle */}
            <div className="w-5 h-5 relative flex items-center justify-center">
              <svg viewBox="0 0 100 100" className="w-full h-full">
                <polygon points="50,10 90,85 10,85" fill="#FFCD11" />
                <polygon points="50,32 76,75 24,75" fill="#000000" />
              </svg>
            </div>
            <span className="font-bold tracking-wider text-cat-yellow text-base font-mono">CAT</span>
            <span className="text-xs uppercase tracking-widest text-slate-400 font-semibold border-l border-slate-700 pl-2">
              Operator Assistant
            </span>
          </div>

          {/* Mode Switcher Tabs */}
          <nav className="flex items-center space-x-1 bg-cat-dark p-1 rounded-lg border border-cat-border">
            <button
              onClick={() => setRole('operator')}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded text-xs font-semibold transition-all ${
                role === 'operator'
                  ? 'bg-cat-yellow text-black shadow'
                  : 'text-slate-400 hover:text-white hover:bg-cat-hover'
              }`}
            >
              <HardHat className="w-3.5 h-3.5" />
              <span>Cab Tablet</span>
            </button>

            <button
              onClick={() => setRole('admin')}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded text-xs font-semibold transition-all ${
                role === 'admin'
                  ? 'bg-cat-yellow text-black shadow'
                  : 'text-slate-400 hover:text-white hover:bg-cat-hover'
              }`}
            >
              <LayoutDashboard className="w-3.5 h-3.5" />
              <span>Fleet Admin</span>
            </button>

            <button
              onClick={() => setRole('trainer')}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded text-xs font-semibold transition-all ${
                role === 'trainer'
                  ? 'bg-cat-yellow text-black shadow'
                  : 'text-slate-400 hover:text-white hover:bg-cat-hover'
              }`}
            >
              <GraduationCap className="w-3.5 h-3.5" />
              <span>Training Hub</span>
            </button>
          </nav>
        </div>

        {/* Machine & Operator Context Selectors */}
        <div className="flex items-center space-x-2.5">
          {/* Active Machine Selector */}
          <div className="flex items-center space-x-1.5 bg-cat-dark px-2.5 py-1 rounded border border-cat-border text-xs">
            <span className="text-slate-500 font-mono">UNIT:</span>
            <select
              value={activeMachine.machine_id}
              onChange={(e) => {
                const found = machines.find(m => m.machine_id === e.target.value);
                if (found) setActiveMachine(found);
              }}
              className="bg-transparent text-cat-yellow font-mono font-bold focus:outline-none cursor-pointer"
            >
              {machines.map((m) => (
                <option key={m.machine_id} value={m.machine_id} className="bg-cat-panel text-white">
                  {m.machine_id} ({m.reference_model}) {m.powertrain === 'electric' ? '⚡EV' : '⛽'}
                </option>
              ))}
            </select>
          </div>

          {/* Active Operator Switcher */}
          <div className="hidden md:flex items-center space-x-1.5 bg-cat-dark px-2.5 py-1 rounded border border-cat-border text-xs">
            <span className="text-slate-500 font-mono">OP:</span>
            <select
              value={activeOperator.operator_id}
              onChange={(e) => {
                const found = operators.find(o => o.operator_id === e.target.value);
                if (found) setActiveOperator(found);
              }}
              className="bg-transparent text-white font-medium focus:outline-none cursor-pointer"
            >
              {operators.map((op) => (
                <option key={op.operator_id} value={op.operator_id} className="bg-cat-panel text-white">
                  {op.name} ({op.operator_id})
                </option>
              ))}
            </select>
          </div>

          {/* Demo Trigger Modal Button */}
          <div className="relative">
            <button
              onClick={() => setShowDemoMenu(!showDemoMenu)}
              className="flex items-center space-x-1 bg-amber-500/10 border border-amber-500/40 text-amber-400 hover:bg-amber-500/20 px-2.5 py-1.5 rounded text-xs font-semibold transition-colors"
              title="Simulate Real-time Safety Infraction"
            >
              <AlertTriangle className="w-3.5 h-3.5 text-cat-yellow" />
              <span>Simulate Alert</span>
              <ChevronDown className="w-3 h-3 ml-0.5" />
            </button>

            {showDemoMenu && (
              <div 
                className="absolute right-0 mt-2 w-64 bg-cat-panel border border-cat-border rounded-lg shadow-xl py-2 z-50 text-xs"
                onMouseLeave={() => setShowDemoMenu(false)}
              >
                <div className="px-3 py-1 text-slate-400 font-mono text-[10px] uppercase border-b border-cat-border">
                  Edge Rule Engine In-Cab Triggers
                </div>
                
                <button
                  onClick={() => {
                    triggerSimulationAlert('unbelted_moving');
                    setShowDemoMenu(false);
                  }}
                  className="w-full text-left px-3 py-2 hover:bg-cat-hover flex items-center space-x-2 text-rose-300 font-medium"
                >
                  <span className="w-2 h-2 rounded-full bg-rose-500 animate-ping" />
                  <span>Unbelted While Moving (&gt;0 km/h)</span>
                </button>

                <button
                  onClick={() => {
                    triggerSimulationAlert('proximity_breach');
                    setShowDemoMenu(false);
                  }}
                  className="w-full text-left px-3 py-2 hover:bg-cat-hover flex items-center space-x-2 text-amber-300 font-medium"
                >
                  <span className="w-2 h-2 rounded-full bg-amber-500" />
                  <span>Proximity Breach (1.8m Red Zone)</span>
                </button>

                <button
                  onClick={() => {
                    triggerSimulationAlert('coolant_high');
                    setShowDemoMenu(false);
                  }}
                  className="w-full text-left px-3 py-2 hover:bg-cat-hover flex items-center space-x-2 text-orange-300 font-medium"
                >
                  <span className="w-2 h-2 rounded-full bg-orange-500" />
                  <span>Coolant Overheat (102.5°C)</span>
                </button>

                <button
                  onClick={() => {
                    triggerSimulationAlert('low_battery');
                    setShowDemoMenu(false);
                  }}
                  className="w-full text-left px-3 py-2 hover:bg-cat-hover flex items-center space-x-2 text-cyan-300 font-medium"
                >
                  <span className="w-2 h-2 rounded-full bg-cyan-400" />
                  <span>EV Low Battery (&lt;15% SOC)</span>
                </button>
              </div>
            )}
          </div>

          {/* Cab Audio Voice Alert Mute / Unmute */}
          <button
            onClick={toggleAudioMute}
            className={`p-1.5 rounded border text-xs transition-colors ${
              audioMuted 
                ? 'bg-rose-950/40 border-rose-800 text-rose-400' 
                : 'bg-cat-dark border-cat-border text-cat-yellow hover:bg-cat-hover'
            }`}
            title={audioMuted ? 'Cab Voice Alerts Muted' : 'Cab Voice Alerts Active'}
          >
            {audioMuted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
          </button>

          {/* Cloud API vs Edge Autonomous Status Indicator */}
          <div 
            className="flex items-center space-x-1.5 px-2.5 py-1 rounded bg-cat-dark border border-cat-border text-[11px]"
            title={isBackendConnected ? "Connected to Cloud FastAPI backend" : "Autonomous Edge Gateway Mode (Offline Safe)"}
          >
            {isBackendConnected ? (
              <>
                <Wifi className="w-3.5 h-3.5 text-emerald-400 animate-pulse" />
                <span className="text-emerald-400 font-mono font-medium hidden sm:inline">CLOUD LIVE</span>
              </>
            ) : (
              <>
                <Cpu className="w-3.5 h-3.5 text-cat-yellow" />
                <span className="text-cat-yellow font-mono font-medium hidden sm:inline">EDGE GATEWAY</span>
              </>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};
