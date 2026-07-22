import { useEffect, useState } from 'react';
import { TrendingUp, AlertTriangle, Clock, Shield } from 'lucide-react';
import { api } from '../api';

type Executive = {
  plant_name: string;
  period: string;
  kpis: Record<string, number>;
  trends: { month: string; incidents: number; near_misses: number; prahari_catches: number }[];
  motif_breakdown: { motif: string; count: number }[];
  regulatory_exposure: string[];
};

export function ExecutiveDashboardPage() {
  const [data, setData] = useState<Executive | null>(null);

  useEffect(() => {
    api.getExecutive().then(setData);
  }, []);

  if (!data) return <div className="p-4 text-text-secondary">Loading executive dashboard...</div>;

  const k = data.kpis;

  return (
    <div className="p-4 h-full flex flex-col">
      <header className="mb-4">
        <h1 className="text-lg font-semibold flex items-center gap-2">
          <TrendingUp className="text-accent" size={20} /> Executive Dashboard
        </h1>
        <p className="text-xs text-text-secondary">
          {data.plant_name} · {data.period} — aggregated risk trends, compliance KPIs (§15.4.6, §20)
        </p>
      </header>

      <div className="grid grid-cols-4 gap-3 mb-4">
        {[
          { label: 'Compound Hazards', value: k.compound_hazards_detected, icon: AlertTriangle },
          { label: 'Critical Open', value: k.critical_open, icon: Shield },
          { label: 'Avg Lead Time', value: `${k.avg_lead_time_min}m`, icon: Clock },
          { label: 'FNR Reduction', value: `${k.fnr_reduction_pct}%`, icon: TrendingUp },
        ].map(({ label, value, icon: Icon }) => (
          <div key={label} className="bg-bg-surface border border-gray-800 rounded-lg p-4">
            <Icon size={16} className="text-accent mb-2" />
            <div className="text-2xl font-bold tabular-nums">{value}</div>
            <div className="text-[10px] text-text-secondary uppercase">{label}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-12 gap-4 flex-1 min-h-0">
        <div className="col-span-8 bg-bg-surface border border-gray-800 rounded-lg p-4">
          <h3 className="text-xs font-medium text-text-secondary uppercase mb-4">Risk Trend (4 months)</h3>
          <div className="flex items-end gap-4 h-40">
            {data.trends.map((t) => (
              <div key={t.month} className="flex-1 flex flex-col items-center gap-1">
                <div className="w-full flex flex-col gap-0.5 justify-end h-32">
                  <div className="bg-sev-critical/80 rounded-t w-full" style={{ height: `${t.incidents * 20 + 4}px` }} title={`Incidents: ${t.incidents}`} />
                  <div className="bg-sev-active/60 w-full" style={{ height: `${t.near_misses * 8}px` }} title={`Near misses: ${t.near_misses}`} />
                  <div className="bg-accent/60 rounded-b w-full" style={{ height: `${t.prahari_catches * 6}px` }} title={`PRAHARI catches: ${t.prahari_catches}`} />
                </div>
                <span className="text-[10px] text-text-secondary">{t.month}</span>
              </div>
            ))}
          </div>
          <div className="flex gap-4 mt-3 text-[10px] text-text-secondary">
            <span className="flex items-center gap-1"><span className="w-2 h-2 bg-sev-critical rounded" /> Incidents</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 bg-sev-active rounded" /> Near misses</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 bg-accent rounded" /> PRAHARI catches</span>
          </div>
        </div>

        <div className="col-span-4 space-y-4">
          <div className="bg-bg-surface border border-gray-800 rounded-lg p-4">
            <h3 className="text-xs font-medium text-text-secondary uppercase mb-2">Zones at Risk</h3>
            <div className="text-3xl font-bold tabular-nums">{k.zones_at_risk}<span className="text-lg text-text-secondary">/{k.total_zones}</span></div>
            <div className="text-xs text-text-secondary mt-1">Recommendation acceptance: {k.recommendation_acceptance_pct}%</div>
          </div>
          <div className="bg-bg-surface border border-gray-800 rounded-lg p-4">
            <h3 className="text-xs font-medium text-text-secondary uppercase mb-2">Motif Breakdown</h3>
            {data.motif_breakdown.map((m) => (
              <div key={m.motif} className="flex justify-between text-xs mb-1">
                <span className="font-mono text-accent">{m.motif}</span>
                <span className="tabular-nums">{m.count}</span>
              </div>
            ))}
          </div>
          <div className="bg-bg-surface border border-gray-800 rounded-lg p-4">
            <h3 className="text-xs font-medium text-text-secondary uppercase mb-2">Regulatory Exposure</h3>
            {data.regulatory_exposure.map((r) => (
              <div key={r} className="text-xs text-text-secondary mb-1">{r}</div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
