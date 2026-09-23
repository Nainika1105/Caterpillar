import React from 'react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Legend, CartesianGrid } from 'recharts';
import { Brain, Cpu, CheckCircle2, AlertTriangle, ShieldCheck, Flame, Zap } from 'lucide-react';

export const AnomalyDashboard: React.FC = () => {
  const comparisonData: Array<{ name: string; Rules: number; ML_IsolationForest: number }> = [];
  const liveAnomalies: Array<{ id: string; machine_id: string; type: string; score: number; severity: string; description: string; rule_detected: boolean; timestamp: string }> = [];

  return (
    <div className="bg-cat-panel border border-cat-border rounded-xl p-4 shadow-cat space-y-5">
      <div className="border-b border-cat-border pb-3">
        <div className="flex items-center space-x-2">
          <Brain className="w-5 h-5 text-cat-yellow" />
          <h3 className="text-sm font-bold font-mono uppercase tracking-wider text-white">
            Unusual Behavior & Anomaly Detection (Isolation Forest vs Edge Rules)
          </h3>
        </div>
        <p className="text-xs text-slate-400 font-mono mt-1">
          Detects multivariate degradation and subtle mechanical faults that threshold-based rules miss (e.g. pump cavitation, valve bypass, cell thermal gradients).
        </p>
      </div>

      {/* Benchmark comparison chart */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        <div className="lg:col-span-6 bg-cat-dark p-4 rounded-lg border border-cat-border">
          <div className="text-xs font-mono font-bold uppercase text-white mb-3 flex items-center justify-between">
            <span>Detection Rate: Rule Engine vs Isolation Forest</span>
            <span className="text-[10px] text-cat-yellow font-normal">+42% Detection Gain</span>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={comparisonData} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2E343D" />
                <XAxis dataKey="name" tick={{ fill: '#94A3B8', fontSize: 10 }} interval={0} angle={-15} textAnchor="end" />
                <YAxis tick={{ fill: '#94A3B8', fontSize: 10 }} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#1A1D21', borderColor: '#2E343D', borderRadius: '6px', fontSize: '11px', fontFamily: 'monospace' }}
                  labelStyle={{ color: '#FFCD11' }}
                />
                <Legend wrapperStyle={{ fontSize: '11px', fontFamily: 'monospace' }} />
                <Bar dataKey="Rules" name="Rule Engine (Baseline)" fill="#64748B" radius={[4, 4, 0, 0]} />
                <Bar dataKey="ML_IsolationForest" name="ML Isolation Forest" fill="#FFCD11" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Planted Anomalies Breakdown */}
        <div className="lg:col-span-6 space-y-3">
          <div className="text-xs font-mono font-bold uppercase text-white mb-2">
            Active Multivariate Anomalies Flagged
          </div>

          <div className="space-y-2.5">
            {liveAnomalies.map(anom => (
              <div 
                key={anom.id}
                className="bg-cat-dark border border-cat-border p-3.5 rounded-lg text-xs space-y-2"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <span className="font-mono font-bold text-cat-yellow">{anom.id}</span>
                    <span className="font-mono text-white font-semibold">UNIT: {anom.machine_id}</span>
                    <span className="px-1.5 py-0.5 rounded bg-cat-panel font-mono text-[10px] text-slate-300 uppercase">
                      {anom.type.replace(/_/g, ' ')}
                    </span>
                  </div>
                  <div className="flex items-center space-x-1.5">
                    <span className="text-[10px] font-mono text-slate-400">Score: {anom.score}</span>
                    <span className="px-1.5 py-0.5 rounded bg-rose-950 text-rose-400 border border-rose-800 text-[10px] font-mono uppercase font-bold">
                      {anom.severity}
                    </span>
                  </div>
                </div>

                <p className="text-slate-300 font-sans text-xs leading-relaxed">
                  {anom.description}
                </p>

                <div className="flex items-center justify-between pt-1 border-t border-cat-border text-[11px] font-mono">
                  <div className="flex items-center space-x-2">
                    <span className={`flex items-center space-x-1 ${anom.rule_detected ? 'text-emerald-400' : 'text-slate-500'}`}>
                      {anom.rule_detected ? <CheckCircle2 className="w-3 h-3" /> : <span className="w-3 h-3 text-center">✗</span>}
                      <span>Rule Engine</span>
                    </span>
                    <span className="text-slate-600">|</span>
                    <span className="flex items-center space-x-1 text-cat-yellow font-bold">
                      <CheckCircle2 className="w-3 h-3" />
                      <span>ML Isolation Forest</span>
                    </span>
                  </div>
                  <span className="text-slate-400">{new Date(anom.timestamp).toLocaleTimeString()}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
