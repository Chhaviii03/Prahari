import { NavLink } from 'react-router-dom';
import { Shield, LayoutDashboard, Map, BarChart3, Smartphone, LogOut } from 'lucide-react';
import type { User } from '../types';

const nav = [
  { to: '/', label: 'Safety Dashboard', icon: LayoutDashboard },
  { to: '/heatmap', label: 'Geospatial Heatmap', icon: Map },
  { to: '/scorecard', label: 'Demo Scorecard', icon: BarChart3 },
  { to: '/mobile', label: 'Worker Mobile', icon: Smartphone },
];

export function Layout({ children, user, onLogout }: { children: React.ReactNode; user: User | null; onLogout: () => void }) {
  return (
    <div className="min-h-screen flex bg-bg-base">
      <aside className="w-56 bg-bg-surface border-r border-gray-800 flex flex-col">
        <div className="p-4 border-b border-gray-800">
          <div className="flex items-center gap-2">
            <Shield className="text-accent" size={24} />
            <div>
              <div className="font-bold text-sm tracking-wide">PRAHARI</div>
              <div className="text-[10px] text-text-secondary">Safety Intelligence</div>
            </div>
          </div>
        </div>
        <nav className="flex-1 p-2 space-y-0.5">
          {nav.map(({ to, label, icon: Icon }) => (
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
              {label}
            </NavLink>
          ))}
        </nav>
        {user && (
          <div className="p-3 border-t border-gray-800">
            <div className="text-xs text-text-secondary">Signed in as</div>
            <div className="text-sm font-medium truncate">{user.name}</div>
            <div className="text-[10px] text-text-secondary capitalize">{user.role.replace('_', ' ')}</div>
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
