import { useEffect, useState } from 'react';
import { Settings, Wifi, WifiOff, RefreshCw } from 'lucide-react';
import { api } from '../api';

type Integration = { id: string; name: string; status: string; last_event: string | null };

type SettingsData = {
  integrations: Integration[];
  thresholds_view: Record<string, number>;
  active_scenario: string;
  forecast_horizon_min: number;
};

const STATUS_COLOR: Record<string, string> = {
  HEALTHY: 'text-sev-ok',
  DEGRADED: 'text-sev-active',
  STALE: 'text-text-secondary',
  DOWN: 'text-sev-critical',
};

export function SettingsPage() {
  const [settings, setSettings] = useState<SettingsData | null>(null);
  const [reloading, setReloading] = useState(false);

  const load = () => api.getSettings().then(setSettings);

  useEffect(() => { load(); }, []);

  const reloadSeed = async () => {
    setReloading(true);
    try {
      await api.reloadSeed();
      await load();
    } finally {
      setReloading(false);
    }
  };

  if (!settings) return <div className="p-4 text-text-secondary">Loading settings...</div>;

  return (
    <div className="p-4 h-full flex flex-col max-w-3xl">
      <header className="mb-4">
        <h1 className="text-lg font-semibold flex items-center gap-2">
          <Settings className="text-accent" size={20} /> Settings
        </h1>
        <p className="text-xs text-text-secondary">
          Integrations, threshold view, scenario preferences (§19)
        </p>
      </header>

      <section className="bg-bg-surface border border-gray-800 rounded-lg p-4 mb-4">
        <h3 className="text-xs font-medium text-text-secondary uppercase mb-3">Connector Health (P1)</h3>
        <div className="space-y-2">
          {settings.integrations.map((int) => (
            <div key={int.id} className="flex items-center justify-between bg-bg-base rounded p-3 text-sm">
              <div className="flex items-center gap-2">
                {int.status === 'HEALTHY' ? <Wifi size={14} className="text-sev-ok" /> : <WifiOff size={14} className="text-sev-active" />}
                <span>{int.name}</span>
              </div>
              <div className="text-right">
                <span className={`text-xs font-medium ${STATUS_COLOR[int.status] || ''}`}>{int.status}</span>
                {int.last_event && (
                  <div className="text-[10px] text-text-secondary">{new Date(int.last_event).toLocaleString()}</div>
                )}
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="bg-bg-surface border border-gray-800 rounded-lg p-4 mb-4">
        <h3 className="text-xs font-medium text-text-secondary uppercase mb-3">Threshold View (read-only)</h3>
        <div className="grid grid-cols-2 gap-2 text-xs">
          {Object.entries(settings.thresholds_view).map(([key, val]) => (
            <div key={key} className="bg-bg-base rounded p-2 flex justify-between">
              <span className="text-text-secondary">{key.replace(/_/g, ' ')}</span>
              <span className="tabular-nums font-medium">{val}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="bg-bg-surface border border-gray-800 rounded-lg p-4">
        <h3 className="text-xs font-medium text-text-secondary uppercase mb-3">Demo Configuration</h3>
        <div className="text-sm mb-3">
          Active scenario: <span className="text-accent font-mono">{settings.active_scenario}</span>
        </div>
        <div className="text-sm mb-3">
          Forecast horizon: <span className="tabular-nums">{settings.forecast_horizon_min} min</span>
        </div>
        <button
          onClick={reloadSeed}
          disabled={reloading}
          className="flex items-center gap-1 text-xs bg-bg-base border border-gray-700 px-3 py-1.5 rounded hover:border-accent"
        >
          <RefreshCw size={12} className={reloading ? 'animate-spin' : ''} />
          Reload seed data
        </button>
      </section>
    </div>
  );
}
