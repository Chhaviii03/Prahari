import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Shield } from 'lucide-react';
import { api } from '../api';
import { homeForRole } from '../config/nav';
import type { User } from '../types';

const DEMO_ACCOUNTS = [
  { username: 'safety', label: 'Safety Officer', role: 'Dashboard home' },
  { username: 'permit', label: 'Permit Officer', role: 'Permit Intelligence' },
  { username: 'compliance', label: 'Compliance Officer', role: 'Reports Library' },
  { username: 'executive', label: 'Executive', role: 'KPI roll-up' },
  { username: 'worker', label: 'Worker', role: 'Mobile view' },
  { username: 'admin', label: 'Admin', role: 'User management' },
];

export function Login({ onLogin }: { onLogin: (user: User, token: string) => void }) {
  const [username, setUsername] = useState('safety');
  const [password, setPassword] = useState('prahari');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const res = await api.login(username, password);
      onLogin(res.user, res.access_token);
      const home = homeForRole(res.user.role);
      if (res.user.role === 'worker') navigate('/mobile');
      else navigate(home);
    } catch {
      setError('Invalid credentials');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen app-watermark flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="mx-auto mb-4 w-14 h-14 rounded-2xl bg-accent-soft flex items-center justify-center shadow-soft">
            <Shield className="text-accent" size={32} />
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-ink-primary">PRAHARI</h1>
          <p className="text-ink-secondary text-sm mt-2">Industrial Safety Intelligence Platform</p>
          <p className="text-ink-secondary text-xs mt-1">प्रहरी — the sentinel who watches so others may work</p>
        </div>

        <form onSubmit={handleSubmit} className="bg-bg-surface rounded-2xl border border-line p-6 space-y-4 shadow-card">
          <div>
            <label className="block text-xs text-ink-secondary mb-1.5 font-medium">Username</label>
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full bg-bg-surface border border-line rounded-xl px-3 py-2.5 text-sm text-ink-primary placeholder:text-ink-secondary focus:outline-none focus:border-accent focus:ring-2 focus:ring-accent/30"
            />
          </div>
          <div>
            <label className="block text-xs text-ink-secondary mb-1.5 font-medium">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-bg-surface border border-line rounded-xl px-3 py-2.5 text-sm text-ink-primary placeholder:text-ink-secondary focus:outline-none focus:border-accent focus:ring-2 focus:ring-accent/30"
            />
          </div>
          {error && <p className="text-sev-critical text-sm">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-accent-peach hover:bg-accent-muted text-ink-primary font-semibold py-2.5 rounded-xl text-sm disabled:opacity-50 transition-colors shadow-soft"
          >
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        <div className="mt-6">
          <p className="text-xs text-ink-secondary mb-2 text-center">Quick demo accounts (password: prahari)</p>
          <div className="grid grid-cols-2 gap-2">
            {DEMO_ACCOUNTS.map((a) => (
              <button
                key={a.username}
                onClick={() => { setUsername(a.username); setPassword('prahari'); }}
                className="bg-bg-surface border border-line rounded-xl p-2.5 text-left hover:border-accent hover:bg-accent-soft/60 transition-colors shadow-card"
              >
                <div className="text-xs font-medium text-ink-primary">{a.label}</div>
                <div className="text-[10px] text-ink-secondary">{a.role}</div>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
