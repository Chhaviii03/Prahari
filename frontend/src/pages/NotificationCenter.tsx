import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Bell, CheckCircle, AlertTriangle, Siren } from 'lucide-react';
import { api } from '../api';
import { bandColor } from '../components/ui';

type Notification = {
  id: string;
  type: string;
  priority: string;
  title: string;
  body: string;
  zone_id?: string;
  risk_id?: string;
  acknowledged: boolean;
  status: string;
  ts: string;
};

export function NotificationCenterPage() {
  const [items, setItems] = useState<Notification[]>([]);
  const [unread, setUnread] = useState(0);
  const navigate = useNavigate();

  const load = () => api.getNotifications().then((d) => {
    setItems(d.items);
    setUnread(d.unread);
  });

  useEffect(() => { load(); const i = setInterval(load, 5000); return () => clearInterval(i); }, []);

  const icon = (type: string) => {
    if (type === 'EMERGENCY') return Siren;
    if (type === 'RISK_ALERT') return AlertTriangle;
    return Bell;
  };

  return (
    <div className="p-4 h-full flex flex-col max-w-3xl">
      <header className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold flex items-center gap-2">
            <Bell className="text-accent" size={20} /> Notification Center
          </h1>
          <p className="text-xs text-text-secondary">
            Routed alerts, escalations, acknowledgement status (§19)
          </p>
        </div>
        {unread > 0 && (
          <span className="bg-sev-critical text-white text-xs font-bold px-2 py-1 rounded-full">
            {unread} unread
          </span>
        )}
      </header>

      <div className="flex-1 overflow-y-auto space-y-2">
        {items.length === 0 && (
          <p className="text-sm text-text-secondary text-center py-8">No notifications. System nominal.</p>
        )}
        {items.map((n) => {
          const Icon = icon(n.type);
          return (
            <button
              key={n.id}
              onClick={() => n.risk_id && navigate(`/risk/${n.risk_id}`)}
              className={`w-full text-left bg-bg-surface border rounded-lg p-4 transition-colors hover:border-accent/50 ${
                n.acknowledged ? 'border-gray-800 opacity-75' : 'border-accent/30'
              }`}
            >
              <div className="flex items-start gap-3">
                <Icon size={18} className={n.priority === 'CRITICAL' ? 'text-sev-critical' : 'text-sev-active'} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="text-sm font-medium truncate">{n.title}</span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded border shrink-0 ${bandColor(n.priority)}`}>
                      {n.priority}
                    </span>
                  </div>
                  <p className="text-xs text-text-secondary line-clamp-2">{n.body}</p>
                  <div className="flex items-center gap-3 mt-1 text-[10px] text-text-secondary">
                    <span>{new Date(n.ts).toLocaleString()}</span>
                    <span>{n.type}</span>
                    {n.acknowledged && (
                      <span className="flex items-center gap-0.5 text-sev-ok">
                        <CheckCircle size={10} /> Acknowledged
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
