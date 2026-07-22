import { NavLink } from 'react-router-dom';
import { Shield, LogOut, Wifi, WifiOff } from 'lucide-react';
import type { User } from '../types';
import { navForRole } from '../config/nav';
import { useWebSocket } from '../hooks/useWebSocket';

export function Layout({
  children,
  user,
  onLogout,
  onRealtimeEvent,
}: {
  children: React.ReactNode;
  user: User | null;
  onLogout: () => void;
  onRealtimeEvent?: () => void;
}) {
  const { connected, reconnecting } = useWebSocket((event) => {
    if (event.type === 'risk_updated' || event.type === 'emergency' || event.type === 'replay_step') {
      onRealtimeEvent?.();
    }
  });

  const items = user ? navForRole(user.role) : [];

  return (
    <div className="min-h-screen flex app-watermark">
      <aside className="w-56 bg-bg-surface border-r border-line flex flex-col shrink-0 shadow-card z-10">
        <div className="p-4 border-b border-line">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-accent-soft flex items-center justify-center">
              <Shield className="text-accent" size={20} />
            </div>
            <div>
              <div className="font-bold text-sm tracking-wide text-ink-primary">PRAHARI</div>
              <div className="text-[10px] text-ink-secondary">Safety Intelligence</div>
            </div>
          </div>
        </div>
        <nav className="flex-1 p-2 space-y-0.5 overflow-y-auto">
          {items.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors ${
                  isActive
                    ? 'bg-accent-soft text-ink-primary font-medium [&_svg]:text-accent'
                    : 'text-ink-secondary hover:text-ink-primary hover:bg-bg-elevated'
                }`
              }
            >
              <Icon size={16} />
              <span className="truncate">{label}</span>
            </NavLink>
          ))}
        </nav>
        {user && (
          <div className="p-3 border-t border-line bg-bg-surface">
            <div className="flex items-center gap-1 text-[10px] mb-2">
              {connected ? (
                <><Wifi size={10} className="text-sev-ok" /><span className="text-sev-ok">Live</span></>
              ) : (
                <><WifiOff size={10} className="text-sev-active" /><span className="text-sev-active">{reconnecting ? 'Reconnecting…' : 'Offline'}</span></>
              )}
            </div>
            <div className="text-xs text-ink-secondary">Signed in as</div>
            <div className="text-sm font-medium truncate text-ink-primary">{user.name}</div>
            <div className="text-[10px] text-ink-secondary capitalize">{user.role.replace(/_/g, ' ')}</div>
            <button onClick={onLogout} className="mt-2 flex items-center gap-1 text-xs text-ink-secondary hover:text-sev-critical transition-colors">
              <LogOut size={12} /> Sign out
            </button>
          </div>
        )}
      </aside>
      <main className="flex-1 overflow-auto relative">{children}</main>
    </div>
  );
}
