import { useEffect, useState } from 'react';
import { AlertTriangle, FileCheck, Shield } from 'lucide-react';
import { api } from '../api';
import { bandColor } from '../components/ui';

type Permit = {
  permit_id: string;
  zone_id: string;
  zone_name: string;
  status: string;
  type: string;
  conflicts: string[];
  severity: string;
};

export function PermitIntelligencePage() {
  const [permits, setPermits] = useState<Permit[]>([]);
  const [overrideId, setOverrideId] = useState<string | null>(null);
  const [justification, setJustification] = useState('');
  const [loading, setLoading] = useState(false);

  const load = () => api.getPermits().then((d) => setPermits(d.permits));

  useEffect(() => { load(); const i = setInterval(load, 5000); return () => clearInterval(i); }, []);

  const submitOverride = async (permitId: string) => {
    if (!justification.trim()) return;
    setLoading(true);
    try {
      await api.overridePermit(permitId, justification);
      setOverrideId(null);
      setJustification('');
      load();
    } finally {
      setLoading(false);
    }
  };

  const conflicts = permits.filter((p) => p.conflicts.length > 0);

  return (
    <div className="p-4 h-full flex flex-col">
      <header className="mb-4">
        <h1 className="text-lg font-semibold flex items-center gap-2">
          <FileCheck className="text-accent" size={20} /> Permit Intelligence
        </h1>
        <p className="text-xs text-text-secondary">
          Active permit monitoring, conflict detection, controlled overrides — audited (§15.4.3)
        </p>
      </header>

      <div className="grid grid-cols-3 gap-3 mb-4">
        <div className="bg-bg-surface border border-gray-800 rounded-lg p-3">
          <div className="text-2xl font-bold tabular-nums">{permits.length}</div>
          <div className="text-xs text-text-secondary">Active / Scheduled</div>
        </div>
        <div className="bg-sev-critical/10 border border-sev-critical/30 rounded-lg p-3">
          <div className="text-2xl font-bold tabular-nums text-sev-critical">{conflicts.length}</div>
          <div className="text-xs text-text-secondary">Live Conflicts</div>
        </div>
        <div className="bg-bg-surface border border-gray-800 rounded-lg p-3">
          <div className="text-2xl font-bold tabular-nums">{permits.filter((p) => p.status === 'ACTIVE').length}</div>
          <div className="text-xs text-text-secondary">Active Permits</div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto space-y-2">
        {permits.length === 0 && (
          <p className="text-sm text-text-secondary text-center py-8">
            No permits loaded. Run Load Coke-Oven Demo from the Safety Dashboard.
          </p>
        )}
        {permits.map((p) => (
          <div key={`${p.permit_id}-${p.status}`} className="bg-bg-surface border border-gray-800 rounded-lg p-4">
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-mono text-sm text-accent">{p.permit_id}</span>
                  <span className={`text-[10px] px-1.5 py-0.5 rounded border ${bandColor(p.severity === 'OK' ? 'WATCH' : p.severity)}`}>
                    {p.severity}
                  </span>
                  <span className="text-[10px] text-text-secondary">{p.status}</span>
                </div>
                <div className="text-xs text-text-secondary">{p.zone_id} · {p.zone_name} · {p.type}</div>
                {p.conflicts.length > 0 && (
                  <div className="mt-2 space-y-1">
                    {p.conflicts.map((c, i) => (
                      <div key={i} className="flex items-start gap-1 text-xs text-sev-active">
                        <AlertTriangle size={12} className="shrink-0 mt-0.5" /> {c}
                      </div>
                    ))}
                  </div>
                )}
              </div>
              {p.conflicts.length > 0 && (
                <button
                  onClick={() => setOverrideId(p.permit_id)}
                  className="text-xs bg-bg-base border border-gray-700 px-3 py-1.5 rounded hover:border-sev-active shrink-0"
                >
                  Override (audited)
                </button>
              )}
            </div>
            {overrideId === p.permit_id && (
              <div className="mt-3 pt-3 border-t border-gray-800">
                <label className="text-xs text-text-secondary block mb-1">Justification required (§9.3)</label>
                <textarea
                  value={justification}
                  onChange={(e) => setJustification(e.target.value)}
                  className="w-full bg-bg-base border border-gray-700 rounded p-2 text-sm h-16"
                  placeholder="Reason for permit override..."
                />
                <div className="flex gap-2 mt-2">
                  <button
                    onClick={() => submitOverride(p.permit_id)}
                    disabled={loading || !justification.trim()}
                    className="text-xs bg-accent text-white px-3 py-1.5 rounded disabled:opacity-50 flex items-center gap-1"
                  >
                    <Shield size={12} /> Submit Override
                  </button>
                  <button onClick={() => setOverrideId(null)} className="text-xs text-text-secondary px-3 py-1.5">
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
