import { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from './components/Layout';
import { Login } from './pages/Login';
import { Dashboard } from './pages/Dashboard';
import { Heatmap } from './pages/Heatmap';
import { RiskDetail } from './pages/RiskDetail';
import { ScorecardPage } from './pages/Scorecard';
import { Mobile } from './pages/Mobile';
import type { User } from './types';

function App() {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem('prahari_token');
    const userJson = localStorage.getItem('prahari_user');
    if (token && userJson) {
      try { setUser(JSON.parse(userJson)); } catch {}
    }
    setReady(true);
  }, []);

  const handleLogin = (u: User, token: string) => {
    localStorage.setItem('prahari_token', token);
    localStorage.setItem('prahari_user', JSON.stringify(u));
    setUser(u);
  };

  const handleLogout = () => {
    localStorage.removeItem('prahari_token');
    localStorage.removeItem('prahari_user');
    setUser(null);
  };

  if (!ready) return null;

  if (!user) {
    return (
      <BrowserRouter>
        <Routes>
          <Route path="*" element={<Login onLogin={handleLogin} />} />
        </Routes>
      </BrowserRouter>
    );
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/mobile" element={<Mobile />} />
        <Route
          path="*"
          element={
            <Layout user={user} onLogout={handleLogout}>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/heatmap" element={<Heatmap />} />
                <Route path="/risk/:id" element={<RiskDetail />} />
                <Route path="/scorecard" element={<ScorecardPage />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </Layout>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
