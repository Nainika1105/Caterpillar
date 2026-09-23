import React, { useState } from 'react';
import { useFleet } from '../../context/FleetContext';
import { api } from '../../services/api';
import { TrainingRecord } from '../../types';
import { 
  GraduationCap, 
  Award, 
  AlertTriangle, 
  CheckCircle2, 
  Calendar, 
  ShieldCheck, 
  Search, 
  Filter,
  RefreshCw
} from 'lucide-react';

export const TrainingDashboard: React.FC = () => {
  const { operators } = useFleet();
  const [trainingList, setTrainingList] = useState<TrainingRecord[]>([]);
  const [selectedFilter, setSelectedFilter] = useState<'all' | 'expired' | 'valid'>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [renewedId, setRenewedId] = useState<string | null>(null);

  React.useEffect(() => {
    Promise.all(operators.map(operator => api.getTrainingRecords(operator.operator_id)))
      .then(records => setTrainingList(records.flat()))
      .catch(() => setTrainingList([]));
  }, [operators]);

  const handleRenew = (recordId: string) => {
    setTrainingList(prev => prev.map(rec => {
      if (rec.record_id === recordId) {
        return {
          ...rec,
          is_expired: false,
          valid_until: '2027-09-23',
          score_pct: 95
        };
      }
      return rec;
    }));
    setRenewedId(recordId);
    setTimeout(() => setRenewedId(null), 2500);
  };

  const filtered = trainingList.filter(rec => {
    if (selectedFilter === 'expired' && !rec.is_expired) return false;
    if (selectedFilter === 'valid' && rec.is_expired) return false;

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const op = operators.find(o => o.operator_id === rec.operator_id);
      return (
        rec.course_name.toLowerCase().includes(q) ||
        rec.operator_id.toLowerCase().includes(q) ||
        (op && op.name.toLowerCase().includes(q))
      );
    }
    return true;
  });

  const expiredCount = trainingList.filter(t => t.is_expired).length;

  return (
    <div className="space-y-4 max-w-7xl mx-auto pb-12">
      {/* Header bar */}
      <div className="bg-cat-panel border border-cat-border p-4 rounded-xl shadow-cat">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-cat-border pb-3 mb-3">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 rounded-lg bg-cat-dark border border-cat-yellow/30 text-cat-yellow">
              <GraduationCap className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-base font-bold font-mono uppercase tracking-wide text-white">
                Operator Certification & Safety Training Hub
              </h2>
              <p className="text-xs text-slate-400 font-mono mt-0.5">
                Centralized credential management: Task Matcher automatically enforces credential validity before machine dispatch.
              </p>
            </div>
          </div>

          {/* Quick Stats Pill */}
          <div className="flex items-center space-x-2">
            <div className="px-3 py-1.5 rounded-lg bg-cat-dark border border-cat-border font-mono text-xs">
              <span className="text-slate-400">Total Records: </span>
              <strong className="text-white">{trainingList.length}</strong>
            </div>
            <div className={`px-3 py-1.5 rounded-lg border font-mono text-xs ${
              expiredCount > 0 
                ? 'bg-rose-950/60 border-rose-800 text-rose-300' 
                : 'bg-emerald-950/60 border-emerald-800 text-emerald-300'
            }`}>
              <span>Lapsed Credentials: </span>
              <strong>{expiredCount}</strong>
            </div>
          </div>
        </div>

        {/* Filter & Search Bar */}
        <div className="flex flex-wrap items-center justify-between gap-3 text-xs font-mono">
          <div className="flex items-center space-x-2 bg-cat-dark p-1 rounded-lg border border-cat-border">
            <button
              onClick={() => setSelectedFilter('all')}
              className={`px-3 py-1 rounded transition-colors ${
                selectedFilter === 'all' ? 'bg-cat-yellow text-black font-bold' : 'text-slate-400 hover:text-white'
              }`}
            >
              All Records
            </button>
            <button
              onClick={() => setSelectedFilter('expired')}
              className={`px-3 py-1 rounded transition-colors ${
                selectedFilter === 'expired' ? 'bg-rose-600 text-white font-bold' : 'text-rose-400 hover:text-white'
              }`}
            >
              Lapsed / Action Required ({expiredCount})
            </button>
            <button
              onClick={() => setSelectedFilter('valid')}
              className={`px-3 py-1 rounded transition-colors ${
                selectedFilter === 'valid' ? 'bg-emerald-600 text-white font-bold' : 'text-emerald-400 hover:text-white'
              }`}
            >
              Current &amp; Compliant
            </button>
          </div>

          <div className="relative min-w-[240px]">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search by operator or course..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-cat-dark border border-cat-border rounded-lg pl-8 pr-3 py-1.5 text-white text-xs focus:border-cat-yellow focus:outline-none placeholder:text-slate-500 font-mono"
            />
          </div>
        </div>
      </div>

      {/* Training Table */}
      <div className="bg-cat-panel border border-cat-border rounded-xl overflow-hidden shadow-cat">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-cat-dark border-b border-cat-border text-slate-400 uppercase text-[10px]">
              <tr>
                <th className="py-3 px-4">Operator Name</th>
                <th className="py-3 px-4">Certified Course Module</th>
                <th className="py-3 px-4">Examination Score</th>
                <th className="py-3 px-4">Validity Horizon</th>
                <th className="py-3 px-4">Compliance Status</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-cat-border/60">
              {filtered.map(rec => {
                const op = operators.find(o => o.operator_id === rec.operator_id);
                const isRenewed = renewedId === rec.record_id;

                return (
                  <tr key={rec.record_id} className="hover:bg-cat-dark/60 transition-colors">
                    <td className="py-3 px-4">
                      <div className="font-bold text-white text-sm">{op?.name || rec.operator_id}</div>
                      <div className="text-[10px] text-slate-400">{rec.operator_id} · {op?.home_site_id}</div>
                    </td>

                    <td className="py-3 px-4">
                      <div className="font-semibold text-slate-200">{rec.course_name}</div>
                      <div className="text-[10px] text-slate-400">Class: Mandatory Safety Recertification</div>
                    </td>

                    <td className="py-3 px-4">
                      <span className={`font-bold ${rec.score_pct >= 80 ? 'text-emerald-400' : 'text-amber-400'}`}>
                        {rec.score_pct}%
                      </span>
                    </td>

                    <td className="py-3 px-4 text-slate-300">
                      <div className="flex items-center space-x-1">
                        <Calendar className="w-3.5 h-3.5 text-cat-yellow" />
                        <span>Valid until: {rec.valid_until || 'Indefinite'}</span>
                      </div>
                    </td>

                    <td className="py-3 px-4">
                      {rec.is_expired ? (
                        <div className="inline-flex items-center space-x-1 px-2.5 py-1 rounded bg-rose-950 text-rose-300 border border-rose-800 text-[10px] font-bold">
                          <AlertTriangle className="w-3 h-3 text-rose-400" />
                          <span>EXPIRED (DISPATCH BLOCKED)</span>
                        </div>
                      ) : (
                        <div className="inline-flex items-center space-x-1 px-2.5 py-1 rounded bg-emerald-950 text-emerald-300 border border-emerald-800 text-[10px] font-bold">
                          <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                          <span>ACTIVE &amp; VERIFIED</span>
                        </div>
                      )}
                    </td>

                    <td className="py-3 px-4 text-right">
                      {rec.is_expired ? (
                        <button
                          onClick={() => handleRenew(rec.record_id)}
                          className="px-3 py-1.5 rounded bg-cat-yellow hover:bg-cat-gold text-black font-bold text-[11px] uppercase tracking-wider transition-all shadow"
                        >
                          {isRenewed ? 'Refreshed!' : 'Log Re-Cert'}
                        </button>
                      ) : (
                        <span className="text-[11px] text-slate-500 font-mono">Current</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
