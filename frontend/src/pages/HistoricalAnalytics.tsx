import { useEffect, useState } from 'react';
import { LineChart, Play, TrendingUp } from 'lucide-react';
import { api } from '../api';

type Analytics = {
  scenario_name: string;
  replay_offset: number;
  metrics: Record<string, number>;
  motif_performance: { motif_id: string; name: string; version: string; fires_in_session: number; avg_lead_time_min: number | null; precision: number | null }[];
  crs_timeline: { offset: number; crs: string }[];
  active_risks: number;
};

export function HistoricalAnalyticsPage() {
  const [data, setData] = useState<Analytics | null>(null);

  const load = () => api.getAnalytics().then(setData);

  useEffect(() => { load(); }, []);

  if (!data) return <div className="p-4 text-ink-secondary">Loading analytics...</div>;

  return (
    <div className="p-4 h-full flex flex-col">
      <header className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold flex items-center gap-2">
            <LineChart className="text-accent" size={20} /> Historical Analytics
          </h1>
          <p className="text-xs text-ink-secondary">
            Trends, replays, motif performance — evaluation framework (§9a, §16.3)
          </p>
        </div>
        <button
          onClick={async () => { await api.startReplay(); setTimeout(load, 2000); }}
          className="flex items-center gap-1 text-xs bg-accent-peach text-ink-primary px-3 py-1.5 rounded"
        >
          <Play size={12} /> Run Scenario Replay
        </button>
      </header>

      <div className="grid grid-cols-4 gap-3 mb-4">
        {[
          { label: 'Precision', value: `${(data.metrics.precision * 100).toFixed(0)}%` },
          { label: 'Recall', value: `${(data.metrics.recall * 100).toFixed(0)}%` },
          { label: 'FNR Reduction', value: `${data.metrics.fnr_reduction_pct.toFixed(0)}%` },
          { label: 'Lead Time', value: `${data.metrics.prahari_lead_time_min}m` },
        ].map((m) => (
          <div key={m.label} className="bg-bg-surface border border-line rounded-xl shadow-card p-3">
            <div className="text-xl font-bold tabular-nums">{m.value}</div>
            <div className="text-[10px] text-ink-secondary uppercase">{m.label}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-12 gap-4 flex-1 min-h-0">
        <div className="col-span-7 bg-bg-surface border border-line rounded-xl shadow-card p-4 overflow-y-auto">
          <h3 className="text-xs font-medium text-ink-secondary uppercase mb-3 flex items-center gap-1">
            <TrendingUp size={14} /> Motif Performance — {data.scenario_name}
          </h3>
          <table className="w-full text-xs">
            <thead>
              <tr className="text-ink-secondary border-b border-line">
                <th className="text-left py-2">Motif</th>
                <th className="text-left py-2">Version</th>
                <th className="text-right py-2">Fires</th>
                <th className="text-right py-2">Avg Lead</th>
              </tr>
            </thead>
            <tbody>
              {data.motif_performance.map((m) => (
                <tr key={m.motif_id} className="border-b border-line/60">
                  <td className="py-2 font-mono text-accent">{m.motif_id}</td>
                  <td className="py-2">{m.version}</td>
                  <td className="py-2 text-right tabular-nums">{m.fires_in_session}</td>
                  <td className="py-2 text-right tabular-nums">{m.avg_lead_time_min ? `${m.avg_lead_time_min}m` : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="col-span-5 bg-bg-surface border border-line rounded-xl shadow-card p-4 overflow-y-auto">
          <h3 className="text-xs font-medium text-ink-secondary uppercase mb-3">CRS Timeline (Replay)</h3>
          <p className="text-[10px] text-ink-secondary mb-2">Offset: T{data.replay_offset}m · Active risks: {data.active_risks}</p>
          {data.crs_timeline.map((t) => (
            <div key={t.offset} className="flex items-center gap-2 mb-2 text-xs">
              <span className="font-mono text-ink-secondary w-12">T{t.offset}m</span>
              <div className="flex-1 bg-bg-base rounded h-4 overflow-hidden">
                <div
                  className="h-full bg-sev-critical/80"
                  style={{ width: `${Math.min(100, parseFloat(t.crs) || 0)}%` }}
                />
              </div>
              <span className="tabular-nums w-8 text-right">{t.crs}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
