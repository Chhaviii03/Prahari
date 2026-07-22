import { useEffect, useState } from 'react';
import { api } from '../api';
import type { ZoneState } from '../types';
import { bandHex } from '../components/ui';
import { PlantMap } from '../components/PlantMap';

type MapConfig = {
  center: { lat: number; lng: number };
  zoom: number;
  bounds: { south: number; west: number; north: number; east: number };
};

type Worker = { worker_id: string; zone_id: string; lat: number; lng: number; name: string };

type EvacRoute = {
  from_zone: string;
  label?: string;
  route: { lat: number; lng: number }[];
};

const DEFAULT_MAP: MapConfig = {
  center: { lat: 17.61285, lng: 83.19192 },
  zoom: 15,
  bounds: { south: 17.606, west: 83.184, north: 17.620, east: 83.200 },
};

export function Heatmap() {
  const [zones, setZones] = useState<ZoneState[]>([]);
  const [workers, setWorkers] = useState<Worker[]>([]);
  const [permits, setPermits] = useState<{ permit_id: string; zone_id: string; status: string }[]>([]);
  const [evacRoutes, setEvacRoutes] = useState<EvacRoute[]>([]);
  const [mapConfig, setMapConfig] = useState<MapConfig>(DEFAULT_MAP);

  useEffect(() => {
    const load = () =>
      api.getHeatmap().then((d) => {
        setZones(d.zones);
        setWorkers(d.workers as Worker[]);
        setPermits(d.permits as typeof permits);
        setEvacRoutes((d as { evacuation_routes?: EvacRoute[] }).evacuation_routes ?? []);
        if ((d as { map?: MapConfig }).map) setMapConfig((d as { map: MapConfig }).map);
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
        <p className="text-xs text-text-secondary">
          Visakhapatnam Steel Plant · Satellite + CRS zone overlays · Workers · Permits (§15.4.2)
        </p>
      </header>

      <div className="flex-1 grid grid-cols-12 gap-4 min-h-0">
        <div className="col-span-9 bg-bg-surface rounded-lg border border-gray-800 p-2 relative overflow-hidden min-h-[420px]">
          <PlantMap mapConfig={mapConfig} zones={zones} workers={workers} evacRoutes={visibleRoutes} />

          <div className="absolute bottom-4 left-4 z-[1000] flex flex-wrap gap-x-4 gap-y-1 text-[10px] bg-bg-base/90 border border-gray-800 rounded px-2 py-1.5">
            {[
              { color: bandHex('CRITICAL'), label: 'Critical' },
              { color: bandHex('ACTIVE'), label: 'Active' },
              { color: bandHex('WATCH'), label: 'Watch' },
              { color: '#1C2229', label: 'Nominal' },
            ].map((l) => (
              <div key={l.label} className="flex items-center gap-1">
                <span className="w-3 h-3 rounded border border-gray-600" style={{ background: l.color }} />
                {l.label}
              </div>
            ))}
            <div className="flex items-center gap-1.5">
              <span className="w-4 h-0.5 bg-sev-critical border-dashed border-t border-sev-critical" />
              <span className="text-sev-critical font-medium">Evacuation route</span>
            </div>
          </div>
        </div>

        <div className="col-span-3 space-y-3 overflow-y-auto">
          <div className="bg-bg-surface rounded-lg border border-gray-800 p-3">
            <h3 className="text-xs font-medium text-text-secondary uppercase mb-2">Zone Status</h3>
            {zones.filter((z) => z.crs > 0 || z.ch4_lel > 0 || z.occupancy > 0).map((z) => (
              <div key={z.zone_id} className="text-xs mb-2 pb-2 border-b border-gray-800/50">
                <div className="font-medium">{z.zone_id} · {z.band || 'NOMINAL'}</div>
                <div className="text-text-secondary">CRS: {z.crs.toFixed(0)}</div>
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

          {visibleRoutes.length > 0 && (
            <div className="bg-sev-critical/10 rounded-lg border border-sev-critical/30 p-3">
              <h3 className="text-xs font-medium text-sev-critical uppercase mb-1">Evacuation Route</h3>
              <p className="text-xs text-text-secondary">
                Follow the red dashed line on the map to exit {visibleRoutes[0].from_zone} to the assembly point.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
