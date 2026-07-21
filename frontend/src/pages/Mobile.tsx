import { useEffect, useState } from 'react';
import { AlertTriangle, CheckCircle, MapPin } from 'lucide-react';
import { api } from '../api';
import type { ZoneState } from '../types';
import { bandColor } from '../components/ui';

export function Mobile() {
  const [zone, setZone] = useState<ZoneState | null>(null);
  const [alert, setAlert] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const hm = await api.getHeatmap();
        const c12 = hm.zones.find((z) => z.zone_id === 'C-12');
        setZone(c12 || null);
        if (c12 && c12.ch4_lel > 5) {
          setAlert(`HAZARD in ${c12.zone_id}: CH₄ at ${c12.ch4_lel.toFixed(1)}% LEL. Do NOT enter. Await supervisor instructions.`);
        } else {
          setAlert(null);
        }
      } catch {}
    };
    load();
    const i = setInterval(load, 5000);
    return () => clearInterval(i);
  }, []);

  return (
    <div className="max-w-sm mx-auto min-h-screen bg-bg-base p-4">
      <div className="text-center mb-6 pt-4">
        <h1 className="text-lg font-bold">PRAHARI Worker</h1>
        <p className="text-xs text-text-secondary">Zone Safety Status</p>
      </div>

      {alert ? (
        <div className="bg-sev-critical/20 border-2 border-sev-critical rounded-xl p-6 mb-4 text-center">
          <AlertTriangle className="mx-auto text-sev-critical mb-3" size={48} />
          <div className="text-lg font-bold text-sev-critical mb-2">ZONE UNSAFE</div>
          <p className="text-sm">{alert}</p>
          <button className="mt-4 w-full bg-sev-critical text-white font-bold py-3 rounded-lg text-sm">
            EVACUATE NOW → Exit via Route A
          </button>
        </div>
      ) : (
        <div className="bg-sev-ok/20 border-2 border-sev-ok rounded-xl p-6 mb-4 text-center">
          <CheckCircle className="mx-auto text-sev-ok mb-3" size={48} />
          <div className="text-lg font-bold text-sev-ok mb-2">ZONE SAFE</div>
          <p className="text-sm text-text-secondary">No active hazards in your zone</p>
        </div>
      )}

      {zone && (
        <div className="bg-bg-surface rounded-xl border border-gray-800 p-4 space-y-3">
          <div className="flex items-center gap-2">
            <MapPin size={16} className="text-accent" />
            <span className="font-medium">{zone.zone_id}</span>
            <span className="text-xs text-text-secondary">{zone.name}</span>
          </div>
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div className="bg-bg-base rounded p-2">
              <div className="text-[10px] text-text-secondary">CH₄</div>
              <div className="tabular-nums font-medium">{zone.ch4_lel.toFixed(1)}% LEL</div>
            </div>
            <div className="bg-bg-base rounded p-2">
              <div className="text-[10px] text-text-secondary">Workers</div>
              <div className="tabular-nums font-medium">{zone.occupancy}</div>
            </div>
          </div>
          <div className="text-[10px] text-text-secondary">
            Last updated: {new Date().toLocaleTimeString()} · As-of timestamp shown for RF-dead zones
          </div>
        </div>
      )}

      <div className="mt-4 bg-bg-surface rounded-xl border border-gray-800 p-4">
        <h3 className="text-xs font-medium text-text-secondary uppercase mb-2">Your Permits</h3>
        <div className="text-sm">PTW-2240 — Confined Space Entry</div>
        <div className="text-xs text-sev-critical mt-1">⚠ HOLD — Do not proceed until hazard cleared</div>
      </div>
    </div>
  );
}
