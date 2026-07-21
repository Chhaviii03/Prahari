import { Flame, HardHat, Users, Wrench, AlertTriangle, Zap, Box } from 'lucide-react';

export function bandColor(band: string): string {
  switch (band) {
    case 'CRITICAL': return 'text-sev-critical bg-sev-critical/15 border-sev-critical/40';
    case 'ACTIVE': return 'text-sev-active bg-sev-active/15 border-sev-active/40';
    case 'WATCH': return 'text-sev-watch bg-sev-watch/15 border-sev-watch/40';
    default: return 'text-sev-ok bg-sev-ok/15 border-sev-ok/40';
  }
}

export function bandHex(band: string): string {
  switch (band) {
    case 'CRITICAL': return '#FF3B30';
    case 'ACTIVE': return '#FF9F0A';
    case 'WATCH': return '#FFD60A';
    default: return '#30D158';
  }
}

export function HazardIcon({ type, size = 16 }: { type: string; size?: number }) {
  const props = { size, className: 'inline' };
  switch (type) {
    case 'gas': return <Flame {...props} />;
    case 'hotwork': return <Zap {...props} />;
    case 'confined': return <Box {...props} />;
    case 'workers': return <Users {...props} />;
    case 'maintenance': return <Wrench {...props} />;
    case 'ppe': return <HardHat {...props} />;
    case 'equipment': return <Wrench {...props} />;
    default: return <AlertTriangle {...props} />;
  }
}

export function formatLeadTime(seconds: number | null): string {
  if (!seconds) return '—';
  const mins = Math.round(seconds / 60);
  if (mins >= 60) return `~${Math.floor(mins / 60)}h${mins % 60}m`;
  return `~${mins}m`;
}

export function SeverityBadge({ band, score }: { band: string; score: number }) {
  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded border text-xs font-semibold tabular-nums ${bandColor(band)}`}>
      {band} · {score.toFixed(0)}
    </span>
  );
}
