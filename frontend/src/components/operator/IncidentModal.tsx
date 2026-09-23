import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useFleet } from '../../context/FleetContext';
import { Severity } from '../../types';
import { ShieldAlert, X, Send, Camera, AlertTriangle, CheckCircle2 } from 'lucide-react';

interface IncidentModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const IncidentModal: React.FC<IncidentModalProps> = ({ isOpen, onClose }) => {
  const { activeMachine, activeOperator } = useAuth();
  const { reportIncident, tasks } = useFleet();

  const currentTask = tasks.find(t => t.machine_id === activeMachine.machine_id && t.status === 'in_progress');

  const [incidentType, setIncidentType] = useState('Near Miss - Proximity');
  const [severity, setSeverity] = useState<Severity>('high');
  const [description, setDescription] = useState('');
  const [submitted, setSubmitted] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!description.trim()) return;

    await reportIncident({
      site_id: activeMachine.site_id,
      machine_id: activeMachine.machine_id,
      operator_id: activeOperator.operator_id,
      task_id: currentTask?.task_id,
      incident_type: incidentType,
      severity,
      description
    });

    setSubmitted(true);
    setTimeout(() => {
      setSubmitted(false);
      setDescription('');
      onClose();
    }, 1400);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
      <div className="bg-cat-panel border-2 border-cat-border rounded-xl max-w-lg w-full p-5 shadow-2xl relative">
        <div className="flex items-center justify-between border-b border-cat-border pb-3 mb-4">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 rounded bg-rose-600 text-white">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white uppercase tracking-wide">
                Cab Safety Incident Report
              </h2>
              <div className="text-[11px] font-mono text-slate-400">
                Unit {activeMachine.machine_id} · Operator {activeOperator.name}
              </div>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-cat-hover text-slate-400 hover:text-white"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {submitted ? (
          <div className="py-12 text-center">
            <CheckCircle2 className="w-14 h-14 text-emerald-400 mx-auto animate-bounce mb-3" />
            <h3 className="text-lg font-bold text-white">Report Logged Successfully</h3>
            <p className="text-xs text-slate-300 font-mono mt-1">
              Synchronized to local safety buffer & queued to cloud safety officer.
            </p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Incident Type Selector */}
            <div>
              <label className="block text-xs font-mono text-slate-300 uppercase mb-1">
                Classification
              </label>
              <select
                value={incidentType}
                onChange={(e) => setIncidentType(e.target.value)}
                className="w-full bg-cat-dark border border-cat-border rounded-lg px-3 py-2.5 text-white text-sm focus:border-cat-yellow focus:outline-none"
              >
                <option value="Near Miss - Proximity">Near Miss - Proximity / Swing Radius</option>
                <option value="Equipment Minor Damage">Equipment Minor Contact / Damage</option>
                <option value="Ground Condition Hazard">Unstable Bench / Soft Ground Slip</option>
                <option value="Thermal / Fluid Warning">Hydraulic Leak / Thermal Spike</option>
                <option value="Seatbelt / PPE Issue">Safety Restraint Non-Compliance</option>
              </select>
            </div>

            {/* Severity Radio Group */}
            <div>
              <label className="block text-xs font-mono text-slate-300 uppercase mb-1.5">
                Severity Rating
              </label>
              <div className="grid grid-cols-4 gap-2">
                {(['low', 'medium', 'high', 'critical'] as Severity[]).map((s) => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => setSeverity(s)}
                    className={`py-2 text-xs font-bold font-mono uppercase rounded border transition-colors ${
                      severity === s
                        ? s === 'critical' ? 'bg-rose-600 text-white border-rose-500'
                          : s === 'high' ? 'bg-orange-600 text-white border-orange-500'
                          : s === 'medium' ? 'bg-amber-500 text-black border-amber-400'
                          : 'bg-emerald-600 text-white border-emerald-500'
                        : 'bg-cat-dark text-slate-400 border-cat-border hover:bg-cat-hover'
                    }`}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>

            {/* Notes Input */}
            <div>
              <label className="block text-xs font-mono text-slate-300 uppercase mb-1">
                Field Observation / Operator Notes
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Describe circumstances, ground conditions, or personnel involved..."
                rows={3}
                required
                className="w-full bg-cat-dark border border-cat-border rounded-lg p-3 text-white text-sm focus:border-cat-yellow focus:outline-none resize-none placeholder:text-slate-500"
              />
            </div>

            <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 pt-1">
              <span className="flex items-center space-x-1">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                <span>Offline local buffer active</span>
              </span>
              <span>GPS: {activeMachine.site_id} Bench</span>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              className="w-full py-3 rounded-lg bg-cat-yellow hover:bg-cat-gold text-black font-bold text-sm uppercase tracking-wider transition-all flex items-center justify-center space-x-2 shadow-lg"
            >
              <Send className="w-4 h-4" />
              <span>Submit Safety Log</span>
            </button>
          </form>
        )}
      </div>
    </div>
  );
};
