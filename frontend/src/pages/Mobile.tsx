import { useEffect, useState } from 'react';
import { AlertTriangle, CheckCircle, MapPin, LogOut, Wifi, WifiOff } from 'lucide-react';
import { api } from '../api';
import type { User, ZoneState } from '../types';
import { bandColor } from '../components/ui';

export function Mobile({ user, onLogout }: { user?: User; onLogout?: () => void }) {
  const [zone, setZone] = useState<ZoneState | null>(null);
  const [emergency, setEmergency] = useState(false);
  const [lastSync, setLastSync] = useState<Date | null>(null);
  const [offline, setOffline] = useState(false);
  const zoneId = user?.zone_id || 'C-12';

  useEffect(() => {
    const load = async () => {
      try {
        const hm = await api.getHeatmap();
        const z = hm.zones.find((x) => x.zone_id === zoneId) || hm.zones[0];
        setZone(z || null);
        setLastSync(new Date());
        setOffline(false);
        const em = await api.getEmergency();
        setEmergency((em as { active: boolean }).active);
      } catch {
        setOffline(true);
      }
    };
    load();
    const i = setInterval(load, 5000);
    return () => clearInterval(i);
  }, [zoneId]);

  const hazardous = zone && (zone.crs >= 40 || zone.ch4_lel > 5 || emergency);
  const band = zone?.band || 'WATCH';

  return (
    <div className="max-w-sm mx-auto min-h-screen app-watermark p-4">
      <div className="flex items-center justify-between mb-4 pt-2">
        <div>
          <h1 className="text-lg font-bold">PRAHARI Worker</h1>
          <p className="text-xs text-ink-secondary">{user?.name || 'Field Worker'}</p>
        </div>
        <div className="flex items-center gap-2">
          {offline ? <WifiOff size={14} className="text-sev-active" /> : <Wifi size={14} className="text-sev-ok" />}
          {onLogout && (
            <button onClick={onLogout} className="text-ink-secondary p-1">
              <LogOut size={16} />
            </button>
          )}
        </div>
      </div>

      {offline && (
        <div className="bg-sev-active/10 border border-sev-active/40 rounded-lg p-3 mb-4 text-xs text-sev-active">
          Cannot confirm current zone state — showing last-known data only (§22.3)
        </div>
      )}

      {hazardous ? (
        <div className="bg-sev-critical/20 border-2 border-sev-critical rounded-xl p-6 mb-4 text-center">
          <AlertTriangle className="mx-auto text-sev-critical mb-3" size={48} />
          <div className="text-lg font-bold text-sev-critical mb-2">ZONE UNSAFE</div>
          {emergency && <p className="text-xs text-sev-critical font-bold mb-2">EMERGENCY DECLARED</p>}
          <p className="text-sm">
            {zone && `CRS ${zone.crs.toFixed(0)} (${band})`}
            {zone && zone.ch4_lel > 0 && ` · CH₄ ${zone.ch4_lel.toFixed(1)}% LEL`}
          </p>
          <p className="text-xs text-ink-secondary mt-2">Do NOT enter. Await supervisor instructions.</p>
          <button className="mt-4 w-full bg-sev-critical text-white font-bold py-4 rounded-lg text-sm">
            EVACUATE NOW → Exit via Route A
          </button>
        </div>
      ) : (
        <div className="bg-sev-ok/20 border-2 border-sev-ok rounded-xl p-6 mb-4 text-center">
          <CheckCircle className="mx-auto text-sev-ok mb-3" size={48} />
          <div className="text-lg font-bold text-sev-ok mb-2">ZONE SAFE</div>
          <p className="text-sm text-ink-secondary">No active compound hazards in your zone</p>
        </div>
      )}

      {zone && (
        <div className="bg-bg-surface rounded-xl border border-line p-4 space-y-3">
          <div className="flex items-center gap-2">
            <MapPin size={16} className="text-accent" />
            <span className="font-medium">{zone.zone_id}</span>
            <span className={`text-[10px] px-1.5 py-0.5 rounded border ${bandColor(band)}`}>{band}</span>
          </div>
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div className="bg-bg-base rounded p-2">
              <div className="text-[10px] text-ink-secondary">CRS</div>
              <div className="tabular-nums font-medium">{zone.crs.toFixed(0)}</div>
            </div>
            <div className="bg-bg-base rounded p-2">
              <div className="text-[10px] text-ink-secondary">CH₄</div>
              <div className="tabular-nums font-medium">{zone.ch4_lel.toFixed(1)}% LEL</div>
            </div>
            <div className="bg-bg-base rounded p-2">
              <div className="text-[10px] text-ink-secondary">Workers</div>
              <div className="tabular-nums font-medium">{zone.occupancy}</div>
            </div>
            <div className="bg-bg-base rounded p-2">
              <div className="text-[10px] text-ink-secondary">Forecast</div>
              <div className="tabular-nums font-medium text-xs">
                {zone.forecast_eta_minutes ? `LEL ~${zone.forecast_eta_minutes}m` : '—'}
              </div>
            </div>
          </div>
          <div className="text-[10px] text-ink-secondary">
            As of {lastSync ? lastSync.toLocaleTimeString() : '—'} · RF-dead zone safe display (§22.3)
          </div>
        </div>
      )}

      <div className="mt-4 bg-bg-surface rounded-xl border border-line p-4">
        <h3 className="text-xs font-medium text-ink-secondary uppercase mb-2">Your Permits</h3>
        {zone?.scheduled_permits?.length ? (
          zone.scheduled_permits.map((p) => (
            <div key={p} className="text-sm mb-2">
              <div>{p}</div>
              <div className="text-xs text-sev-critical mt-0.5">HOLD — Do not proceed until hazard cleared</div>
            </div>
          ))
        ) : (
          <>
            <div className="text-sm">PTW-2240 — Confined Space Entry</div>
            <div className="text-xs text-sev-critical mt-1">HOLD — Do not proceed until hazard cleared</div>
          </>
        )}
      </div>

      <div className="mt-4 text-center text-[10px] text-ink-secondary">
        Worker Mobile · field view per PRD §15.4.7 / §22.3
      </div>
    </div>
  );
}
