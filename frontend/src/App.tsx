import { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { Layout } from './components/Layout';
import { Login } from './pages/Login';
import { Dashboard } from './pages/Dashboard';
import { Heatmap } from './pages/Heatmap';
import { RiskDetail } from './pages/RiskDetail';
import { Mobile } from './pages/Mobile';
import { CopilotPage } from './pages/Copilot';
import { IncidentResponsePage } from './pages/IncidentResponse';
import { PermitIntelligencePage } from './pages/PermitIntelligence';
import { HistoricalAnalyticsPage } from './pages/HistoricalAnalytics';
import { ReportsLibraryPage } from './pages/ReportsLibrary';
import { NotificationCenterPage } from './pages/NotificationCenter';
import { ExecutiveDashboardPage } from './pages/ExecutiveDashboard';
import { UserManagementPage } from './pages/UserManagement';
import { SettingsPage } from './pages/Settings';
import { homeForRole } from './config/nav';
import type { User } from './types';

function RoleRedirect({ user }: { user: User }) {
  const navigate = useNavigate();
  useEffect(() => {
    if (user.role === 'worker') navigate('/mobile', { replace: true });
  }, [user, navigate]);
  return <Navigate to={homeForRole(user.role)} replace />;
}

function AppRoutes({ user, onLogout }: { user: User; onLogout: () => void }) {
  return (
    <Layout user={user} onLogout={onLogout}>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/heatmap" element={<Heatmap />} />
        <Route path="/risk/:id" element={<RiskDetail />} />
        <Route path="/copilot" element={<CopilotPage />} />
        <Route path="/incident" element={<IncidentResponsePage />} />
        <Route path="/permits" element={<PermitIntelligencePage />} />
        <Route path="/analytics" element={<HistoricalAnalyticsPage />} />
        <Route path="/reports" element={<ReportsLibraryPage />} />
        <Route path="/notifications" element={<NotificationCenterPage />} />
        <Route path="/executive" element={<ExecutiveDashboardPage />} />
        <Route path="/admin/users" element={<UserManagementPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/mobile" element={<Mobile />} />
        <Route path="*" element={<RoleRedirect user={user} />} />
      </Routes>
    </Layout>
  );
}

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

  if (user.role === 'worker') {
    return (
      <BrowserRouter>
        <Routes>
          <Route path="/mobile" element={<Mobile user={user} onLogout={handleLogout} />} />
          <Route path="*" element={<Navigate to="/mobile" replace />} />
        </Routes>
      </BrowserRouter>
    );
  }

  return (
    <BrowserRouter>
      <AppRoutes user={user} onLogout={handleLogout} />
    </BrowserRouter>
  );
}

export default App;
