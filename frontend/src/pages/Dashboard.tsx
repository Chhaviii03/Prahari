import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Play, RotateCcw, AlertTriangle, Clock, ChevronRight } from 'lucide-react';
import { api } from '../api';
import type { DashboardItem } from '../types';
import { HazardIcon, SeverityBadge, formatLeadTime } from '../components/ui';

export function Dashboard() {
  const [items, setItems] = useState<DashboardItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [demoLoading, setDemoLoading] = useState(false);
  const navigate = useNavigate();

  const load = async () => {
    try {
      const data = await api.getDashboard();
      setItems(data.items);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); const i = setInterval(load, 5000); return () => clearInterval(i); }, []);

  const loadDemo = async () => {
    setDemoLoading(true);
    try {
      await api.loadScenario();
      await load();
    } finally {
      setDemoLoading(false);
    }
  };

  return (
    <div className="p-4 h-full flex flex-col">
      <header className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-lg font-semibold">Live Safety Dashboard</h1>
          <p className="text-xs text-text-secondary">Prioritised Risk Instances · Deterministic detection (P3)</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={loadDemo}
            disabled={demoLoading}
            className="flex items-center gap-1.5 bg-accent hover:bg-accent/90 text-white text-xs font-medium px-3 py-1.5 rounded"
          >
            <Play size={14} /> {demoLoading ? 'Loading...' : 'Load Coke-Oven Demo'}
          </button>
          <button
            onClick={async () => { await api.resetDemo(); load(); }}
            className="flex items-center gap-1.5 bg-bg-elevated border border-gray-700 text-text-secondary text-xs px-3 py-1.5 rounded hover:text-text-primary"
          >
            <RotateCcw size={14} /> Reset
          </button>
        </div>
      </header>

      <div className="flex-1 grid grid-cols-12 gap-4 min-h-0">
        <div className="col-span-5 bg-bg-surface rounded-lg border border-gray-800 flex flex-col overflow-hidden">
          <div className="px-3 py-2 border-b border-gray-800 text-xs font-medium text-text-secondary uppercase tracking-wider">
            Risk Queue ({items.length})
          </div>
          <div className="flex-1 overflow-y-auto">
            {loading && <div className="p-4 text-sm text-text-secondary">Loading...</div>}
            {!loading && items.length === 0 && (
              <div className="p-6 text-center">
                <AlertTriangle className="mx-auto text-text-secondary mb-2" size={32} />
                <p className="text-sm text-text-secondary">No active risk instances</p>
                <p className="text-xs text-text-secondary mt-1">Click "Load Coke-Oven Demo" to see the compound hazard scenario</p>
              </div>
            )}
            {items.map((item, idx) => (
              <button
                key={item.risk.risk_id}
                onClick={() => navigate(`/risk/${item.risk.risk_id}`)}
                className={`w-full text-left p-3 border-b border-gray-800/50 hover:bg-bg-elevated transition-colors ${idx === 0 ? 'pulse-critical' : ''}`}
              >
                <div className="flex items-center justify-between mb-1">
                  <SeverityBadge band={item.risk.crs.band} score={item.risk.crs.score} />
                  <div className="flex items-center gap-1 text-xs text-text-secondary">
                    <Clock size={12} />
                    {formatLeadTime(item.risk.lead_time_seconds)} lead
                  </div>
                </div>
                <div className="flex items-center gap-1.5 mb-1">
                  {item.hazard_icons.map((h) => <HazardIcon key={h} type={h} size={14} />)}
                  <span className="text-sm font-medium">{item.risk.zone_id}</span>
                  <span className="text-xs text-text-secondary">· {item.risk.motif_id}</span>
                </div>
                <p className="text-xs text-text-secondary line-clamp-2">{item.summary}</p>
                <div className="flex items-center justify-end mt-1">
                  <ChevronRight size={14} className="text-text-secondary" />
                </div>
              </button>
            ))}
          </div>
        </div>

        <div className="col-span-7 bg-bg-surface rounded-lg border border-gray-800 p-4">
          <h2 className="text-sm font-medium mb-3">System Status</h2>
          <div className="grid grid-cols-3 gap-3 mb-4">
            {[
              { label: 'Detection Engine', status: 'P3 Deterministic', ok: true },
              { label: 'Digital Twin', status: 'P2 Live', ok: true },
              { label: 'AI Enrichment', status: 'P4/P5 Ready', ok: true },
            ].map((s) => (
              <div key={s.label} className="bg-bg-base rounded p-3 border border-gray-800">
                <div className="text-[10px] text-text-secondary uppercase">{s.label}</div>
                <div className="text-sm font-medium flex items-center gap-1.5 mt-1">
                  <span className={`w-2 h-2 rounded-full ${s.ok ? 'bg-sev-ok' : 'bg-sev-critical'}`} />
                  {s.status}
                </div>
              </div>
            ))}
          </div>

          <div className="bg-bg-base rounded border border-gray-800 p-4">
            <h3 className="text-xs font-medium text-text-secondary uppercase mb-2">Deterministic / AI Boundary</h3>
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="border border-sev-ok/30 rounded p-3 bg-sev-ok/5">
                <div className="font-semibold text-sev-ok mb-1">DETERMINISTIC ZONE</div>
                <div className="text-text-secondary space-y-0.5">
                  <div>P1 Data Intelligence</div>
                  <div>P2 Digital Twin</div>
                  <div>P3 Compound Risk Engine</div>
                  <div className="text-sev-ok font-medium mt-1">"IS THIS DANGEROUS?" → yes/no</div>
                </div>
              </div>
              <div className="border border-accent/30 rounded p-3 bg-accent/5">
                <div className="font-semibold text-accent mb-1">AI-ASSISTED ZONE</div>
                <div className="text-text-secondary space-y-0.5">
                  <div>P4 Multi-Agent Intelligence</div>
                  <div>P5 Decision Intelligence</div>
                  <div className="text-accent font-medium mt-1">"WHY & WHAT DO WE DO?"</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
