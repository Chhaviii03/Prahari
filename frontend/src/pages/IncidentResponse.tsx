import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Siren, CheckCircle, Circle, Map, Users, FileText, Lock } from 'lucide-react';
import { api } from '../api';
import type { DashboardItem } from '../types';
import { bandHex } from '../components/ui';

type Emergency = {
  active: boolean;
  zone_id?: string;
  risk_id?: string;
  steps: { step: string; status: string; ts: string }[];
  declared_at?: string;
};

export function IncidentResponsePage() {
  const [emergency, setEmergency] = useState<Emergency | null>(null);
  const [items, setItems] = useState<DashboardItem[]>([]);
  const [declaring, setDeclaring] = useState(false);
  const navigate = useNavigate();

  const load = async () => {
    const [dash, em] = await Promise.all([
      api.getDashboard(),
      api.getEmergency(),
    ]);
    setItems(dash.items);
    setEmergency(em as Emergency);
  };

  useEffect(() => { load(); const i = setInterval(load, 5000); return () => clearInterval(i); }, []);

  const declare = async () => {
    const risk = items[0]?.risk;
    if (!risk) return;
    if (!confirm(`Declare emergency for zone ${risk.zone_id}? (1-step confirm per §21.2)`)) return;
    setDeclaring(true);
    try {
      await api.declareEmergency(risk.zone_id, risk.risk_id);
      await load();
    } finally {
      setDeclaring(false);
    }
  };

  const active = emergency?.active;

  return (
    <div className="p-4 h-full flex flex-col">
      <header className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold flex items-center gap-2">
            <Siren className={active ? 'text-sev-critical' : 'text-text-secondary'} size={20} />
            Incident Response Workflow
          </h1>
          <p className="text-xs text-text-secondary">
            Emergency orchestration — evacuation, notifications, evidence lock, draft report (§15.4.4, §21.2)
          </p>
        </div>
        {!active && items.length > 0 && (
          <button
            onClick={declare}
            disabled={declaring}
            className="bg-sev-critical text-white text-xs font-bold px-4 py-2 rounded flex items-center gap-1"
          >
            <Siren size={14} /> Declare Emergency
          </button>
        )}
      </header>

      {active ? (
        <div className="flex-1 grid grid-cols-12 gap-4 min-h-0">
          <div className="col-span-8 bg-sev-critical/5 border-2 border-sev-critical/40 rounded-lg p-4">
            <div className="text-sev-critical font-bold text-lg mb-2">INCIDENT RESPONSE MODE</div>
            <p className="text-sm mb-4">Zone {emergency?.zone_id} — full-bleed situational awareness</p>

            <div className="bg-bg-base rounded-lg p-4 mb-4 min-h-[200px] relative">
              <div className="text-xs text-text-secondary mb-2 flex items-center gap-1">
                <Map size={12} /> Mini-heatmap — affected zone highlighted
              </div>
              <svg viewBox="0 0 400 120" className="w-full h-32">
                <rect width="400" height="120" fill="#0B0F14" />
                <rect x="160" y="40" width="80" height="40" rx="4" fill={bandHex('CRITICAL')} fillOpacity="0.6" stroke="#FF3B30" strokeWidth="2" />
                <text x="200" y="65" textAnchor="middle" fill="#F2F4F7" fontSize="12" fontWeight="bold">{emergency?.zone_id}</text>
                <path d="M 200 80 L 200 110 L 320 110" fill="none" stroke="#FF3B30" strokeWidth="2" strokeDasharray="6 4" />
                <text x="260" y="105" fill="#FF3B30" fontSize="8">Evacuation route</text>
                <circle cx="185" cy="55" r="5" fill="#0A84FF" />
                <circle cx="200" cy="58" r="5" fill="#0A84FF" />
                <circle cx="215" cy="55" r="5" fill="#0A84FF" />
              </svg>
            </div>

            <div className="grid grid-cols-3 gap-2 text-xs">
              <div className="bg-bg-surface rounded p-2 flex items-center gap-2">
                <Users size={14} className="text-accent" /> 3 workers notified
              </div>
              <div className="bg-bg-surface rounded p-2 flex items-center gap-2">
                <Lock size={14} className="text-sev-ok" /> Evidence locked
              </div>
              <div className="bg-bg-surface rounded p-2 flex items-center gap-2">
                <FileText size={14} className="text-accent" /> Draft report generating
              </div>
            </div>
          </div>

          <div className="col-span-4 bg-bg-surface border border-gray-800 rounded-lg p-4 overflow-y-auto">
            <h3 className="text-xs font-medium text-text-secondary uppercase mb-3">Live Checklist</h3>
            {(emergency?.steps || []).map((s, i) => (
              <div key={i} className="flex items-start gap-2 mb-3 text-sm">
                {s.status === 'complete' ? (
                  <CheckCircle size={16} className="text-sev-ok shrink-0 mt-0.5" />
                ) : (
                  <Circle size={16} className="text-sev-active shrink-0 mt-0.5 animate-pulse" />
                )}
                <div>
                  <div>{s.step}</div>
                  <div className="text-[10px] text-text-secondary">{new Date(s.ts).toLocaleTimeString()}</div>
                </div>
              </div>
            ))}
            {emergency?.risk_id && (
              <button
                onClick={() => navigate(`/risk/${emergency.risk_id}`)}
                className="mt-4 w-full text-xs bg-bg-base border border-gray-700 rounded py-2 hover:border-accent"
              >
                View Evidence Package →
              </button>
            )}
          </div>
        </div>
      ) : (
        <div className="flex-1 flex flex-col items-center justify-center text-center p-8">
          <Siren className="text-text-secondary mb-4" size={48} />
          <p className="text-sm text-text-secondary max-w-md">
            No active emergency. Load the coke-oven demo from the Safety Dashboard, then use Declare Emergency
            from Risk Detail or here to enter Incident Response mode.
          </p>
          <button onClick={() => navigate('/')} className="mt-4 text-accent text-sm hover:underline">
            Go to Safety Dashboard →
          </button>
        </div>
      )}
    </div>
  );
}
