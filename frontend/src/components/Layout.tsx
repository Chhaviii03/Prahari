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
    <div className="min-h-screen flex bg-bg-base">
      <aside className="w-56 bg-bg-surface border-r border-gray-800 flex flex-col shrink-0">
        <div className="p-4 border-b border-gray-800">
          <div className="flex items-center gap-2">
            <Shield className="text-accent" size={24} />
            <div>
              <div className="font-bold text-sm tracking-wide">PRAHARI</div>
              <div className="text-[10px] text-text-secondary">Safety Intelligence</div>
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
                `flex items-center gap-2.5 px-3 py-2 rounded text-sm transition-colors ${
                  isActive ? 'bg-accent/15 text-accent' : 'text-text-secondary hover:text-text-primary hover:bg-bg-elevated'
                }`
              }
            >
              <Icon size={16} />
              <span className="truncate">{label}</span>
            </NavLink>
          ))}
        </nav>
        {user && (
          <div className="p-3 border-t border-gray-800">
            <div className="flex items-center gap-1 text-[10px] mb-2">
              {connected ? (
                <><Wifi size={10} className="text-sev-ok" /><span className="text-sev-ok">Live</span></>
              ) : (
                <><WifiOff size={10} className="text-sev-active" /><span className="text-sev-active">{reconnecting ? 'Reconnecting…' : 'Offline'}</span></>
              )}
            </div>
            <div className="text-xs text-text-secondary">Signed in as</div>
            <div className="text-sm font-medium truncate">{user.name}</div>
            <div className="text-[10px] text-text-secondary capitalize">{user.role.replace(/_/g, ' ')}</div>
            <button onClick={onLogout} className="mt-2 flex items-center gap-1 text-xs text-text-secondary hover:text-sev-critical">
              <LogOut size={12} /> Sign out
            </button>
          </div>
        )}
      </aside>
      <main className="flex-1 overflow-auto">{children}</main>
    </div>
  );
}
