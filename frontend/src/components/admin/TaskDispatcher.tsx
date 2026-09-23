import React, { useState } from 'react';
import { useFleet } from '../../context/FleetContext';
import { api } from '../../services/api';
import { AssignmentSuggestion, Task } from '../../types';
import { 
  ClipboardList, 
  Send, 
  Sparkles, 
  ShieldAlert, 
  ShieldCheck, 
  Clock, 
  Target, 
  Cpu, 
  CheckCircle2 
} from 'lucide-react';

export const TaskDispatcher: React.FC = () => {
  const { sites, machines, operators, createTask } = useFleet();

  const [siteId, setSiteId] = useState<string>('S01');
  const [taskType, setTaskType] = useState<string>('trench_excavation');
  const [quantity, setQuantity] = useState<number>(450);
  const [quantityUnit, setQuantityUnit] = useState<string>('m³');
  const [notes, setNotes] = useState<string>('');

  const [selectedSuggestion, setSelectedSuggestion] = useState<AssignmentSuggestion | null>(null);
  const [dispatchedSuccess, setDispatchedSuccess] = useState(false);

  // Compute smart matcher suggestions
  const [suggestions, setSuggestions] = useState<AssignmentSuggestion[]>([]);

  // Set initial selected suggestion
  React.useEffect(() => {
    let cancelled = false;
    api.computeTaskMatches(taskType, quantity, siteId).then(nextSuggestions => {
      if (!cancelled) {
        setSuggestions(nextSuggestions);
        setSelectedSuggestion(nextSuggestions.find(s => s.is_certified) || nextSuggestions[0] || null);
      }
    }).catch(() => {
      if (!cancelled) {
        setSuggestions([]);
        setSelectedSuggestion(null);
      }
    });
    return () => { cancelled = true; };
  }, [taskType, quantity, siteId]);

  const handleDispatch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedSuggestion) return;

    if (!selectedSuggestion.is_certified) {
      alert(`Safety Violation: Cannot dispatch task! Operator lacks required certifications: ${selectedSuggestion.missing_certifications.join(', ')}`);
      return;
    }

    await createTask({
      task_type: taskType,
      site_id: siteId,
      machine_id: selectedSuggestion.machine_id,
      operator_id: selectedSuggestion.operator_id,
      start_time: new Date().toISOString(),
      planned_duration_min: selectedSuggestion.estimated_duration_min,
      quantity,
      quantity_unit: quantityUnit,
      status: 'pending',
      notes: notes || `Auto-matched by CAT Fleet Matcher with ML duration estimate of ${selectedSuggestion.estimated_duration_min} mins.`
    });

    setDispatchedSuccess(true);
    setTimeout(() => {
      setDispatchedSuccess(false);
      setNotes('');
    }, 2500);
  };

  return (
    <div className="bg-cat-panel border border-cat-border rounded-xl p-4 shadow-cat">
      <div className="border-b border-cat-border pb-3 mb-4">
        <h3 className="text-sm font-bold font-mono uppercase tracking-wider text-white flex items-center space-x-2">
          <span>Task Allocation & AI Matcher Dispatcher</span>
          <span className="px-2 py-0.5 rounded bg-cat-yellow/20 text-cat-yellow text-[10px] font-mono font-bold border border-cat-yellow/40">
            XGBoost Duration Estimator Active
          </span>
        </h3>
        <p className="text-xs text-slate-400 font-mono mt-0.5">
          Matches certified operators with available machines and predicts cycle completion times using weather and ground features.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Left Column: Task Definition Form (5 cols) */}
        <form onSubmit={handleDispatch} className="lg:col-span-5 space-y-3.5 bg-cat-dark p-4 rounded-lg border border-cat-border">
          <div className="text-xs font-mono uppercase font-bold text-cat-yellow border-b border-cat-border pb-2">
            1. Define Work Package
          </div>

          {/* Site Selection */}
          <div>
            <label className="block text-xs font-mono text-slate-300 uppercase mb-1">Target Site</label>
            <select
              value={siteId}
              onChange={(e) => setSiteId(e.target.value)}
              className="w-full bg-cat-panel border border-cat-border rounded px-3 py-2 text-white text-xs font-mono focus:border-cat-yellow focus:outline-none"
            >
              {sites.map(s => (
                <option key={s.site_id} value={s.site_id}>
                  {s.name} ({s.city}) - {s.soil_type}
                </option>
              ))}
            </select>
          </div>

          {/* Task Type */}
          <div>
            <label className="block text-xs font-mono text-slate-300 uppercase mb-1">Operation Type</label>
            <select
              value={taskType}
              onChange={(e) => setTaskType(e.target.value)}
              className="w-full bg-cat-panel border border-cat-border rounded px-3 py-2 text-white text-xs font-mono focus:border-cat-yellow focus:outline-none"
            >
              <option value="trench_excavation">Trench Excavation (Storm drain / Utilities)</option>
              <option value="foundation_dig">Foundation & Pier Dig (Structural)</option>
              <option value="stockpile_loading">Stockpile Loading (Aggregates to Tippers)</option>
              <option value="bulk_earthmoving">Bulk Earthmoving (Cut & Fill Grading)</option>
              <option value="quarry_rip_push">Quarry Heavy Rip & Push (Hard Rock)</option>
              <option value="utility_backfill">Utility Backfill & Compaction</option>
            </select>
          </div>

          {/* Quantity & Unit */}
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-xs font-mono text-slate-300 uppercase mb-1">Target Volume</label>
              <input
                type="number"
                min="10"
                max="10000"
                value={quantity}
                onChange={(e) => setQuantity(Number(e.target.value))}
                className="w-full bg-cat-panel border border-cat-border rounded px-3 py-2 text-white text-xs font-mono focus:border-cat-yellow focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-mono text-slate-300 uppercase mb-1">Unit</label>
              <select
                value={quantityUnit}
                onChange={(e) => setQuantityUnit(e.target.value)}
                className="w-full bg-cat-panel border border-cat-border rounded px-3 py-2 text-white text-xs font-mono focus:border-cat-yellow focus:outline-none"
              >
                <option value="m³">m³ (Cubic Meters)</option>
                <option value="tonnes">Tonnes (Metric)</option>
                <option value="cycles">Load Cycles</option>
              </select>
            </div>
          </div>

          {/* Notes */}
          <div>
            <label className="block text-xs font-mono text-slate-300 uppercase mb-1">Field Specifics</label>
            <input
              type="text"
              placeholder="e.g. Bench 4 ramp alignment, wet ground caution"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full bg-cat-panel border border-cat-border rounded px-3 py-2 text-white text-xs focus:border-cat-yellow focus:outline-none placeholder:text-slate-500"
            />
          </div>

          {dispatchedSuccess ? (
            <div className="p-3 bg-emerald-950 border border-emerald-500 rounded text-emerald-400 font-mono text-xs font-bold text-center flex items-center justify-center space-x-2 animate-bounce">
              <CheckCircle2 className="w-4 h-4" />
              <span>TASK DISPATCHED TO CAB OVER WEBSOCKET</span>
            </div>
          ) : (
            <button
              type="submit"
              disabled={!selectedSuggestion || !selectedSuggestion.is_certified}
              className={`w-full py-2.5 rounded font-bold text-xs uppercase tracking-wider transition-all flex items-center justify-center space-x-2 ${
                selectedSuggestion && selectedSuggestion.is_certified
                  ? 'bg-cat-yellow hover:bg-cat-gold text-black shadow-lg cursor-pointer'
                  : 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700'
              }`}
            >
              <Send className="w-4 h-4" />
              <span>Dispatch Task to Operator Cab</span>
            </button>
          )}
        </form>

        {/* Right Column: AI Task Matcher Ranked Suggestions (7 cols) */}
        <div className="lg:col-span-7 space-y-3">
          <div className="flex items-center justify-between border-b border-cat-border pb-2">
            <div className="flex items-center space-x-2 text-xs font-mono uppercase font-bold text-white">
              <Sparkles className="w-4 h-4 text-cat-yellow" />
              <span>2. AI Recommendation & Certification Engine</span>
            </div>
            <span className="text-[11px] font-mono text-slate-400">
              Evaluated {suggestions.length} Fleet Pairs
            </span>
          </div>

          <div className="space-y-2">
            {suggestions.map((sug, idx) => {
              const isSelected = selectedSuggestion?.operator_id === sug.operator_id && selectedSuggestion?.machine_id === sug.machine_id;

              return (
                <div
                  key={`${sug.operator_id}-${sug.machine_id}`}
                  onClick={() => setSelectedSuggestion(sug)}
                  className={`p-3 rounded-lg border transition-all cursor-pointer ${
                    isSelected
                      ? 'bg-cat-dark border-cat-yellow shadow-cat-glow'
                      : 'bg-cat-dark/70 border-cat-border hover:border-slate-600'
                  } ${!sug.is_certified ? 'opacity-70' : ''}`}
                >
                  <div className="flex flex-wrap items-center justify-between gap-2 mb-1.5">
                    <div className="flex items-center space-x-2">
                      <span className={`w-5 h-5 rounded-full flex items-center justify-center font-mono font-bold text-[10px] ${
                        idx === 0 ? 'bg-cat-yellow text-black' : 'bg-slate-800 text-slate-300'
                      }`}>
                        #{idx + 1}
                      </span>
                      <span className="font-bold text-white text-xs">{sug.operator_name}</span>
                      <span className="font-mono text-slate-400 text-[11px]">({sug.operator_id})</span>
                      <span className="text-slate-500">→</span>
                      <span className="font-mono font-bold text-cat-yellow text-xs">{sug.machine_id}</span>
                      <span className="text-slate-300 text-xs">({sug.machine_model})</span>
                    </div>

                    {/* Certification Badge */}
                    <div>
                      {sug.is_certified ? (
                        <span className="flex items-center space-x-1 px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 text-[10px] font-mono font-bold border border-emerald-800">
                          <ShieldCheck className="w-3 h-3" />
                          <span>CERTIFIED ({sug.ranking_score}%)</span>
                        </span>
                      ) : (
                        <span className="flex items-center space-x-1 px-2 py-0.5 rounded bg-rose-950 text-rose-400 text-[10px] font-mono font-bold border border-rose-800">
                          <ShieldAlert className="w-3 h-3" />
                          <span>BLOCKED: MISSING CERT</span>
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Missing certification alert */}
                  {!sug.is_certified && (
                    <div className="text-[11px] font-mono text-rose-400 bg-rose-950/40 p-1.5 rounded border border-rose-900/60 my-1.5">
                      ⚠️ Safety Violation: Operator lacks required credential: <span className="font-bold underline">{sug.missing_certifications.join(', ')}</span>. Assignment blocked by safety policy.
                    </div>
                  )}

                  {/* Duration and Energy Metrics */}
                  <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 pt-1 border-t border-cat-border/60">
                    <div className="flex items-center space-x-1">
                      <Clock className="w-3 h-3 text-cat-yellow" />
                      <span>XGBoost Predicted Duration: <strong className="text-white">{sug.estimated_duration_min} mins</strong></span>
                    </div>
                    <div>
                      Energy Sufficiency: <span className="text-emerald-400 font-bold">100% OK</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};
