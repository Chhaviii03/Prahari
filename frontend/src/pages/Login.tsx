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
    <div className="min-h-screen bg-bg-base flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <Shield className="mx-auto text-accent mb-3" size={48} />
          <h1 className="text-2xl font-bold">PRAHARI</h1>
          <p className="text-text-secondary text-sm mt-1">Industrial Safety Intelligence Platform</p>
          <p className="text-text-secondary text-xs mt-1">प्रहरी — the sentinel who watches so others may work</p>
        </div>

        <form onSubmit={handleSubmit} className="bg-bg-surface rounded-lg border border-gray-800 p-6 space-y-4">
          <div>
            <label className="block text-xs text-text-secondary mb-1">Username</label>
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full bg-bg-base border border-gray-700 rounded px-3 py-2 text-sm focus:outline-none focus:border-accent"
            />
          </div>
          <div>
            <label className="block text-xs text-text-secondary mb-1">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-bg-base border border-gray-700 rounded px-3 py-2 text-sm focus:outline-none focus:border-accent"
            />
          </div>
          {error && <p className="text-sev-critical text-sm">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-accent hover:bg-accent/90 text-white font-medium py-2 rounded text-sm disabled:opacity-50"
          >
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        <div className="mt-6">
          <p className="text-xs text-text-secondary mb-2 text-center">Quick demo accounts (password: prahari)</p>
          <div className="grid grid-cols-2 gap-2">
            {DEMO_ACCOUNTS.map((a) => (
              <button
                key={a.username}
                onClick={() => { setUsername(a.username); setPassword('prahari'); }}
                className="bg-bg-surface border border-gray-800 rounded p-2 text-left hover:border-accent/50 transition-colors"
              >
                <div className="text-xs font-medium">{a.label}</div>
                <div className="text-[10px] text-text-secondary">{a.role}</div>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
