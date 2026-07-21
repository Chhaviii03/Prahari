import { useEffect, useState } from 'react';
import { api } from '../api';
import type { ZoneState } from '../types';
import { bandHex } from '../components/ui';

export function Heatmap() {
  const [zones, setZones] = useState<ZoneState[]>([]);
  const [workers, setWorkers] = useState<{ worker_id: string; zone_id: string; x: number; y: number; name: string }[]>([]);
  const [permits, setPermits] = useState<{ permit_id: string; zone_id: string; status: string }[]>([]);

  useEffect(() => {
    const load = () => api.getHeatmap().then((d) => {
      setZones(d.zones);
      setWorkers(d.workers as typeof workers);
      setPermits(d.permits as typeof permits);
    });
    load();
    const i = setInterval(load, 5000);
    return () => clearInterval(i);
  }, []);

  const maxCrs = Math.max(...zones.map((z) => z.ch4_lel > 0 ? (z.ch4_lel > 10 ? 75 : z.ch4_lel > 5 ? 50 : 20) : 0), 1);

  return (
    <div className="p-4 h-full flex flex-col">
      <header className="mb-4">
        <h1 className="text-lg font-semibold">Geospatial Safety Heatmap</h1>
        <p className="text-xs text-text-secondary">Plant layout · CRS zones · Worker positions · Permit overlays</p>
      </header>

      <div className="flex-1 grid grid-cols-12 gap-4 min-h-0">
        <div className="col-span-9 bg-bg-surface rounded-lg border border-gray-800 p-4 relative overflow-hidden">
          <svg viewBox="0 0 300 180" className="w-full h-full" style={{ minHeight: 400 }}>
            <rect width="300" height="180" fill="#0B0F14" />
            <text x="150" y="15" textAnchor="middle" fill="#9CA3AF" fontSize="10">Visakhapatnam Steel Plant — Zone Map</text>

            {zones.map((zone) => {
              const x = zone.geo.x;
              const y = zone.geo.y;
              const intensity = zone.ch4_lel;
              let fill = '#1C2229';
              if (intensity > 10) fill = bandHex('CRITICAL');
              else if (intensity > 5) fill = bandHex('ACTIVE');
              else if (intensity > 2) fill = bandHex('WATCH');
              const opacity = intensity > 0 ? Math.min(0.8, 0.2 + intensity / 20) : 0.3;

              return (
                <g key={zone.zone_id}>
                  <rect
                    x={x - 25}
                    y={y - 20}
                    width="50"
                    height="40"
                    rx="4"
                    fill={fill}
                    fillOpacity={opacity}
                    stroke={intensity > 5 ? fill : '#374151'}
                    strokeWidth={zone.zone_id === 'C-12' && intensity > 5 ? 2 : 1}
                    className={zone.data_quality === 'STALE' ? 'stale-hatch' : ''}
                  />
                  <text x={x} y={y - 5} textAnchor="middle" fill="#F2F4F7" fontSize="9" fontWeight="bold">{zone.zone_id}</text>
                  <text x={x} y={y + 6} textAnchor="middle" fill="#9CA3AF" fontSize="7">{zone.name.slice(0, 18)}</text>
                  {zone.ch4_lel > 0 && (
                    <text x={x} y={y + 16} textAnchor="middle" fill="#F2F4F7" fontSize="8" className="tabular-nums">
                      CH₄ {zone.ch4_lel.toFixed(1)}% LEL
                    </text>
                  )}
                  {zone.occupancy > 0 && (
                    <circle cx={x + 20} cy={y - 15} r="8" fill="#0A84FF" />
                  )}
                  {zone.occupancy > 0 && (
                    <text x={x + 20} y={y - 12} textAnchor="middle" fill="white" fontSize="7">{zone.occupancy}</text>
                  )}
                </g>
              );
            })}

            {workers.map((w) => (
              <g key={w.worker_id}>
                <circle cx={w.x} cy={w.y} r="4" fill="#0A84FF" stroke="#F2F4F7" strokeWidth="1" />
                <text x={w.x} y={w.y + 12} textAnchor="middle" fill="#0A84FF" fontSize="6">{w.name}</text>
              </g>
            ))}

            {zones.find((z) => z.zone_id === 'C-12') && (zones.find((z) => z.zone_id === 'C-12')?.ch4_lel ?? 0) > 5 && (
              <path
                d="M 160 90 L 140 60 L 100 40"
                fill="none"
                stroke="#FF3B30"
                strokeWidth="1.5"
                strokeDasharray="4 2"
                opacity="0.7"
              />
            )}
          </svg>

          <div className="absolute bottom-4 left-4 flex gap-3 text-[10px]">
            {[
              { color: bandHex('CRITICAL'), label: 'Critical' },
              { color: bandHex('ACTIVE'), label: 'Active' },
              { color: bandHex('WATCH'), label: 'Watch' },
              { color: '#1C2229', label: 'Nominal' },
            ].map((l) => (
              <div key={l.label} className="flex items-center gap-1">
                <span className="w-3 h-3 rounded" style={{ background: l.color }} />
                {l.label}
              </div>
            ))}
          </div>
        </div>

        <div className="col-span-3 space-y-3 overflow-y-auto">
          <div className="bg-bg-surface rounded-lg border border-gray-800 p-3">
            <h3 className="text-xs font-medium text-text-secondary uppercase mb-2">Zone Status</h3>
            {zones.filter((z) => z.ch4_lel > 0 || z.occupancy > 0).map((z) => (
              <div key={z.zone_id} className="text-xs mb-2 pb-2 border-b border-gray-800/50">
                <div className="font-medium">{z.zone_id}</div>
                <div className="text-text-secondary">CH₄: {z.ch4_lel.toFixed(1)}% LEL</div>
                <div className="text-text-secondary">Workers: {z.occupancy}</div>
                {z.forecast_eta_minutes && (
                  <div className="text-sev-active">Forecast: LEL in ~{z.forecast_eta_minutes}m</div>
                )}
              </div>
            ))}
          </div>

          <div className="bg-bg-surface rounded-lg border border-gray-800 p-3">
            <h3 className="text-xs font-medium text-text-secondary uppercase mb-2">Active Permits</h3>
            {permits.length === 0 && <p className="text-xs text-text-secondary">No active permits</p>}
            {permits.map((p) => (
              <div key={p.permit_id} className="text-xs mb-1">
                <span className="text-accent">{p.permit_id}</span>
                <span className="text-text-secondary ml-1">· {p.zone_id} · {p.status}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
