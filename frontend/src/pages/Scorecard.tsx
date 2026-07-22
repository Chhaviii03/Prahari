import { useEffect, useState } from 'react';
import { Play, RotateCcw, TrendingUp } from 'lucide-react';
import { api } from '../api';
import type { Scorecard } from '../types';

export function ScorecardPage() {
  const [scorecard, setScorecard] = useState<Scorecard | null>(null);
  const [replaying, setReplaying] = useState(false);
  const [replayStep, setReplayStep] = useState(0);

  const load = () => api.getScorecard().then(setScorecard);

  useEffect(() => { load(); }, []);

  const runReplay = async () => {
    setReplaying(true);
    await api.resetDemo();
    const offsets = [-110, -75, -40, -10, 0];
    for (let i = 0; i < offsets.length; i++) {
      setReplayStep(i);
      await api.stepReplay(offsets[i]);
      await new Promise((r) => setTimeout(r, 1500));
    }
    setReplaying(false);
    load();
  };

  if (!scorecard) return <div className="p-4 text-ink-secondary">Loading scorecard...</div>;

  return (
    <div className="p-4">
      <header className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-lg font-semibold">Demo-Day Scorecard</h1>
          <p className="text-xs text-ink-secondary">§9a.5 — PRAHARI vs Single-Sensor Baseline on Coke-Oven Scenario</p>
        </div>
        <div className="flex gap-2">
          <button onClick={runReplay} disabled={replaying} className="flex items-center gap-1.5 bg-accent-peach text-ink-primary text-xs px-3 py-1.5 rounded">
            <Play size={14} /> {replaying ? `Replaying step ${replayStep + 1}/5...` : 'Run Live Replay'}
          </button>
          <button onClick={async () => { await api.resetDemo(); load(); }} className="flex items-center gap-1.5 bg-bg-elevated border border-line text-xs px-3 py-1.5 rounded">
            <RotateCcw size={14} /> Reset
          </button>
        </div>
      </header>

      <div className="grid grid-cols-2 gap-4 mb-6">
        <div className="bg-bg-surface rounded-xl border border-line shadow-card p-4">
          <div className="text-xs text-ink-secondary uppercase mb-2">Single-Sensor Baseline (SCADA)</div>
          <div className="text-3xl font-bold text-sev-critical mb-1">
            {scorecard.baseline_detected ? 'ALERT' : 'SILENT'}
          </div>
          <div className="text-sm text-ink-secondary">
            Lead time: {scorecard.baseline_lead_time_minutes} min
          </div>
          <div className="text-xs text-ink-secondary mt-2">
            Every individual sensor stayed under its own threshold — missed the compound hazard
          </div>
        </div>

        <div className="bg-bg-surface rounded-lg border border-sev-ok/30 p-4">
          <div className="text-xs text-ink-secondary uppercase mb-2">PRAHARI (Compound Detection)</div>
          <div className="text-3xl font-bold text-sev-ok mb-1">
            CRS {scorecard.prahari_crs} · DETECTED
          </div>
          <div className="text-sm text-ink-secondary">
            Lead time: {scorecard.prahari_lead_time_minutes} min · Motif: {scorecard.prahari_motif}
          </div>
          <div className="text-xs text-ink-secondary mt-2">
            Citations: {scorecard.regulatory_citations.join(', ')}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-3 mb-6">
        {[
          { label: 'Recall', value: `${(scorecard.recall * 100).toFixed(0)}%`, sub: `vs ${(scorecard.baseline_recall * 100).toFixed(0)}% baseline` },
          { label: 'Precision', value: `${(scorecard.precision * 100).toFixed(0)}%`, sub: 'On labelled set' },
          { label: 'FNR Reduction', value: `${scorecard.fnr_reduction_pct.toFixed(0)}%`, sub: 'Relative vs baseline' },
          { label: 'Lead Time', value: `${scorecard.prahari_lead_time_minutes}m`, sub: 'Median on forecastable motifs' },
        ].map((m) => (
          <div key={m.label} className="bg-bg-surface rounded-xl border border-line shadow-card p-3 text-center">
            <div className="text-[10px] text-ink-secondary uppercase">{m.label}</div>
            <div className="text-2xl font-bold tabular-nums mt-1">{m.value}</div>
            <div className="text-[10px] text-ink-secondary">{m.sub}</div>
          </div>
        ))}
      </div>

      <div className="bg-bg-surface rounded-xl border border-line shadow-card p-4">
        <h3 className="text-sm font-medium mb-3 flex items-center gap-2">
          <TrendingUp size={16} /> Scenario Timeline — {scorecard.scenario_name}
        </h3>
        <div className="space-y-2">
          {scorecard.timeline.map((t) => (
            <div key={t.offset} className="grid grid-cols-12 gap-2 text-xs items-center py-2 border-b border-line/60">
              <div className="col-span-1 font-mono text-ink-secondary">T{t.offset >= 0 ? '+' : ''}{t.offset}m</div>
              <div className="col-span-5 text-ink-secondary">{t.description}</div>
              <div className={`col-span-3 font-medium ${t.baseline === 'SILENT' ? 'text-ink-secondary' : 'text-sev-critical'}`}>
                Baseline: {t.baseline}
              </div>
              <div className={`col-span-3 font-medium ${t.prahari === 'SILENT' ? 'text-ink-secondary' : 'text-sev-ok'}`}>
                PRAHARI: {t.prahari}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="mt-4 text-xs text-ink-secondary text-center">
        Honesty rule (§9a): These are measured results from the replay harness — not aspirational targets.
      </div>
    </div>
  );
}
