import { useEffect, useState } from 'react';
import { api } from '../api';
import type { ZoneState } from '../types';
import { bandHex } from '../components/ui';

const ZONE_W = 58;
const ZONE_H = 36;
const VIEW_W = 400;
const VIEW_H = 210;

type EvacRoute = {
  from_zone: string;
  label?: string;
  route: { x: number; y: number }[];
};

export function Heatmap() {
  const [zones, setZones] = useState<ZoneState[]>([]);
  const [workers, setWorkers] = useState<{ worker_id: string; zone_id: string; x: number; y: number; name: string }[]>([]);
  const [permits, setPermits] = useState<{ permit_id: string; zone_id: string; status: string }[]>([]);
  const [evacRoutes, setEvacRoutes] = useState<EvacRoute[]>([]);

  useEffect(() => {
    const load = () => api.getHeatmap().then((d) => {
      setZones(d.zones);
      setWorkers(d.workers as typeof workers);
      setPermits(d.permits as typeof permits);
      setEvacRoutes((d as { evacuation_routes?: EvacRoute[] }).evacuation_routes ?? []);
    });
    load();
    const i = setInterval(load, 5000);
    return () => clearInterval(i);
  }, []);

  const hazardZones = new Set(
    zones.filter((z) => z.ch4_lel > 2 || z.h2s_ppm > 5 || z.occupancy > 0).map((z) => z.zone_id),
  );

  const visibleRoutes = evacRoutes.filter((r) => hazardZones.has(r.from_zone));

  return (
    <div className="p-4 h-full flex flex-col">
      <header className="mb-4">
        <h1 className="text-lg font-semibold">Geospatial Safety Heatmap</h1>
        <p className="text-xs text-ink-secondary">Plant layout · CRS-based zone heatmap · Workers · Permits (§15.4.2)</p>
      </header>

      <div className="flex-1 grid grid-cols-12 gap-4 min-h-0">
        <div className="col-span-9 bg-bg-surface rounded-xl border border-line shadow-card p-4 relative overflow-hidden">
          <svg viewBox={`0 0 ${VIEW_W} ${VIEW_H}`} className="w-full h-full" style={{ minHeight: 420 }}>
            <rect width={VIEW_W} height={VIEW_H} fill="#FAF8F8" />
            <text x={VIEW_W / 2} y={16} textAnchor="middle" fill="#475569" fontSize="10">
              Visakhapatnam Steel Plant — Zone Map
            </text>

            {/* Evacuation routes — drawn under zones */}
            {visibleRoutes.map((route, idx) => {
              if (route.route.length < 2) return null;
              const d = route.route.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ');
              const mid = route.route[Math.floor(route.route.length / 2)];
              return (
                <g key={`evac-${idx}`}>
                  <path
                    d={d}
                    fill="none"
                    stroke="#EF4444"
                    strokeWidth="2"
                    strokeDasharray="6 4"
                    strokeLinecap="round"
                  />
                  <circle cx={route.route[0].x} cy={route.route[0].y} r="3" fill="#EF4444" />
                  <circle cx={route.route[route.route.length - 1].x} cy={route.route[route.route.length - 1].y} r="3" fill="#EF4444" />
                  <text
                    x={mid.x}
                    y={mid.y - 8}
                    textAnchor="middle"
                    fill="#EF4444"
                    fontSize="8"
                    fontWeight="bold"
                  >
                    {route.label || 'Evacuation route'}
                  </text>
                </g>
              );
            })}

            {zones.map((zone) => {
              const x = zone.geo.x;
              const y = zone.geo.y;
              const band = zone.band || (zone.crs >= 75 ? 'CRITICAL' : zone.crs >= 40 ? 'ACTIVE' : zone.crs > 0 ? 'WATCH' : 'OK');
              const isStale = zone.data_quality === 'STALE';
              let fill = '#FFF1EC';
              if (!isStale && band === 'CRITICAL') fill = bandHex('CRITICAL');
              else if (!isStale && band === 'ACTIVE') fill = bandHex('ACTIVE');
              else if (!isStale && band === 'WATCH') fill = bandHex('WATCH');
              else if (isStale) fill = '#9CA3AF';
              const opacity = zone.crs > 0 ? Math.min(0.85, 0.25 + zone.crs / 120) : 0.55;

              return (
                <g key={zone.zone_id}>
                  <rect
                    x={x - ZONE_W / 2}
                    y={y - ZONE_H / 2}
                    width={ZONE_W}
                    height={ZONE_H}
                    rx="4"
                    fill={fill}
                    fillOpacity={opacity}
                    stroke={band === 'CRITICAL' || band === 'ACTIVE' ? fill : '#E5E7EB'}
                    strokeWidth={zone.crs >= 40 ? 2 : 1}
                    className={isStale ? 'stale-hatch' : ''}
                  />
                  <text x={x} y={y - 8} textAnchor="middle" fill="#111827" fontSize="9" fontWeight="bold">
                    {zone.zone_id}
                  </text>
                  <text x={x} y={y + 2} textAnchor="middle" fill="#475569" fontSize="6.5">
                    {zone.name.length > 16 ? zone.name.slice(0, 15) + '…' : zone.name}
                  </text>
                  {zone.crs > 0 && (
                    <text x={x} y={y + 12} textAnchor="middle" fill="#111827" fontSize="7" className="tabular-nums">
                      CRS {zone.crs.toFixed(0)} · {band}
                    </text>
                  )}
                  {zone.occupancy > 0 && (
                    <>
                      <circle cx={x + ZONE_W / 2 - 6} cy={y - ZONE_H / 2 + 6} r="7" fill="#F5A892" />
                      <text x={x + ZONE_W / 2 - 6} y={y - ZONE_H / 2 + 9} textAnchor="middle" fill="#111827" fontSize="7" fontWeight="bold">
                        {zone.occupancy}
                      </text>
                    </>
                  )}
                </g>
              );
            })}

            {workers.map((w) => (
              <g key={w.worker_id}>
                <circle cx={w.x} cy={w.y} r="3.5" fill="#F5A892" stroke="#FFFFFF" strokeWidth="1.5" />
              </g>
            ))}
          </svg>

          <div className="absolute bottom-4 left-4 flex flex-wrap gap-x-4 gap-y-1 text-[10px]">
            {[
              { color: bandHex('CRITICAL'), label: 'Critical' },
              { color: bandHex('ACTIVE'), label: 'Active' },
              { color: bandHex('WATCH'), label: 'Watch' },
              { color: '#FFF1EC', label: 'Nominal' },
            ].map((l) => (
              <div key={l.label} className="flex items-center gap-1">
                <span className="w-3 h-3 rounded border border-line" style={{ background: l.color }} />
                {l.label}
              </div>
            ))}
            <div className="flex items-center gap-1.5">
              <svg width="20" height="8" className="shrink-0">
                <line x1="0" y1="4" x2="20" y2="4" stroke="#EF4444" strokeWidth="2" strokeDasharray="4 2" />
              </svg>
              <span className="text-sev-critical font-medium">Evacuation route</span>
            </div>
          </div>
        </div>

        <div className="col-span-3 space-y-3 overflow-y-auto">
          <div className="bg-bg-surface rounded-xl border border-line shadow-card p-3">
            <h3 className="text-xs font-medium text-ink-secondary uppercase mb-2">Zone Status</h3>
            {zones.filter((z) => z.crs > 0 || z.ch4_lel > 0 || z.occupancy > 0).map((z) => (
              <div key={z.zone_id} className="text-xs mb-2 pb-2 border-b border-line/60">
                <div className="font-medium">{z.zone_id} · {z.band || 'NOMINAL'}</div>
                <div className="text-ink-secondary">CRS: {z.crs.toFixed(0)}</div>
                <div className="text-ink-secondary">CH₄: {z.ch4_lel.toFixed(1)}% LEL</div>
                <div className="text-ink-secondary">Workers: {z.occupancy}</div>
                {z.forecast_eta_minutes && (
                  <div className="text-sev-active">Forecast: LEL in ~{z.forecast_eta_minutes}m</div>
                )}
              </div>
            ))}
          </div>

          <div className="bg-bg-surface rounded-xl border border-line shadow-card p-3">
            <h3 className="text-xs font-medium text-ink-secondary uppercase mb-2">Active Permits</h3>
            {permits.length === 0 && <p className="text-xs text-ink-secondary">No active permits</p>}
            {permits.map((p) => (
              <div key={p.permit_id} className="text-xs mb-1">
                <span className="text-accent">{p.permit_id}</span>
                <span className="text-ink-secondary ml-1">· {p.zone_id} · {p.status}</span>
              </div>
            ))}
          </div>

          {visibleRoutes.length > 0 && (
            <div className="bg-sev-critical/10 rounded-lg border border-sev-critical/30 p-3">
              <h3 className="text-xs font-medium text-sev-critical uppercase mb-1">Evacuation Route</h3>
              <p className="text-xs text-ink-secondary">
                Follow the red dashed line on the map to exit {visibleRoutes[0].from_zone} to the assembly point.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
