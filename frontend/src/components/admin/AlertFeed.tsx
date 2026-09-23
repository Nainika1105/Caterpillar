import React, { useState } from 'react';
import { useFleet } from '../../context/FleetContext';
import { Severity, SafetyAlert } from '../../types';
import { ShieldAlert, AlertTriangle, CheckCircle, Clock, Volume2, Filter } from 'lucide-react';
import { cabAudio } from '../../services/voiceAlerts';

export const AlertFeed: React.FC = () => {
  const { alerts, acknowledgeAlert } = useFleet();
  const [severityFilter, setSeverityFilter] = useState<'all' | Severity>('all');
  const [showAcknowledged, setShowAcknowledged] = useState(false);

  const filteredAlerts = alerts.filter(a => {
    if (!showAcknowledged && a.acknowledged) return false;
    if (severityFilter !== 'all' && a.severity !== severityFilter) return false;
    return true;
  });

  return (
    <div className="bg-cat-panel border border-cat-border rounded-xl p-4 shadow-cat">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-cat-border pb-3 mb-4">
        <div>
          <h3 className="text-sm font-bold font-mono uppercase tracking-wider text-white flex items-center space-x-2">
            <span>Central Safety Ingestion Feed (Edge → Cloud WebSocket)</span>
          </h3>
          <p className="text-xs text-slate-400 font-mono mt-0.5">
            Streaming alerts evaluated locally by cab edge gateways and forwarded in sub-second latency.
          </p>
        </div>

        {/* Filter controls */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Severity selector */}
          <div className="flex items-center space-x-1 bg-cat-dark p-1 rounded-lg border border-cat-border text-xs font-mono">
            <button
              onClick={() => setSeverityFilter('all')}
              className={`px-2.5 py-1 rounded transition-colors ${
                severityFilter === 'all' ? 'bg-cat-yellow text-black font-bold' : 'text-slate-400 hover:text-white'
              }`}
            >
              All
            </button>
            <button
              onClick={() => setSeverityFilter('critical')}
              className={`px-2.5 py-1 rounded transition-colors ${
                severityFilter === 'critical' ? 'bg-rose-600 text-white font-bold' : 'text-rose-400 hover:text-white'
              }`}
            >
              Critical
            </button>
            <button
              onClick={() => setSeverityFilter('high')}
              className={`px-2.5 py-1 rounded transition-colors ${
                severityFilter === 'high' ? 'bg-amber-500 text-black font-bold' : 'text-amber-400 hover:text-white'
              }`}
            >
              High
            </button>
          </div>

          {/* Toggle Acknowledged */}
          <label className="flex items-center space-x-1.5 text-xs font-mono text-slate-400 cursor-pointer bg-cat-dark px-2.5 py-1.5 rounded border border-cat-border">
            <input
              type="checkbox"
              checked={showAcknowledged}
              onChange={(e) => setShowAcknowledged(e.target.checked)}
              className="accent-cat-yellow rounded"
            />
            <span>Show Acknowledged</span>
          </label>
        </div>
      </div>

      {/* Alerts List */}
      <div className="space-y-2.5">
        {filteredAlerts.length === 0 ? (
          <div className="p-8 text-center text-slate-400 font-mono text-xs bg-cat-dark rounded-lg border border-cat-border">
            No active safety alerts matching criteria. Fleet safety rules operating within nominal parameters.
          </div>
        ) : (
          filteredAlerts.map(alert => {
            const isCritical = alert.severity === 'critical';
            const isHigh = alert.severity === 'high';

            return (
              <div
                key={alert.alert_id}
                className={`p-3.5 rounded-lg border flex flex-col md:flex-row items-start md:items-center justify-between gap-3 transition-all ${
                  alert.acknowledged
                    ? 'bg-cat-dark/50 border-cat-border opacity-60'
                    : isCritical
                      ? 'bg-rose-950/60 border-rose-500/80 shadow-md'
                      : isHigh
                        ? 'bg-amber-950/40 border-amber-500/60'
                        : 'bg-cat-dark border-cat-border'
                }`}
              >
                <div className="flex items-start space-x-3">
                  <div className={`p-2 rounded-lg shrink-0 mt-0.5 ${
                    isCritical ? 'bg-rose-600 text-white' : isHigh ? 'bg-amber-500 text-black' : 'bg-slate-700 text-white'
                  }`}>
                    {isCritical ? <ShieldAlert className="w-5 h-5" /> : <AlertTriangle className="w-5 h-5" />}
                  </div>

                  <div>
                    <div className="flex flex-wrap items-center gap-2 mb-1">
                      <span className="font-mono font-bold text-xs text-cat-yellow">{alert.alert_id}</span>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cat-dark border border-cat-border font-bold text-white uppercase">
                        UNIT: {alert.machine_id}
                      </span>
                      <span className="text-[10px] font-mono text-slate-400">
                        OP: {alert.operator_id} · SITE: {alert.site_id}
                      </span>
                      <span className={`text-[10px] font-mono uppercase font-bold px-1.5 py-0.5 rounded ${
                        isCritical ? 'bg-rose-500 text-white' : 'bg-amber-400 text-black'
                      }`}>
                        {alert.severity}
                      </span>
                      {alert.acknowledged && (
                        <span className="text-[10px] font-mono text-emerald-400 font-bold flex items-center space-x-1">
                          <CheckCircle className="w-3 h-3" />
                          <span>ACKNOWLEDGED</span>
                        </span>
                      )}
                    </div>

                    <p className="text-xs md:text-sm font-semibold text-white">
                      {alert.message}
                    </p>

                    <div className="text-[10px] font-mono text-slate-400 mt-1 flex items-center space-x-2">
                      <Clock className="w-3 h-3 text-cat-yellow" />
                      <span>Triggered: {new Date(alert.start).toLocaleString()}</span>
                      {alert.duration_min && <span>· Duration: {alert.duration_min}m</span>}
                    </div>
                  </div>
                </div>

                {/* Action button */}
                <div className="flex items-center space-x-2 self-end md:self-center shrink-0">
                  <button
                    onClick={() => cabAudio.speak(alert.message, alert.alert_code, 0)}
                    className="p-2 rounded bg-cat-dark hover:bg-cat-hover border border-cat-border text-slate-300 hover:text-cat-yellow"
                    title="Audio playback"
                  >
                    <Volume2 className="w-4 h-4" />
                  </button>

                  {!alert.acknowledged && (
                    <button
                      onClick={() => acknowledgeAlert(alert.alert_id)}
                      className="px-3.5 py-2 rounded bg-cat-yellow hover:bg-cat-gold text-black font-mono font-bold text-xs uppercase tracking-wider transition-all"
                    >
                      Acknowledge
                    </button>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
