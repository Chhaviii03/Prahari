const API = '/v1';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const token = localStorage.getItem('prahari_token');
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options?.headers as Record<string, string>),
  };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${API}${path}`, { ...options, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Request failed');
  }
  return res.json();
}

export const api = {
  login: (username: string, password: string) =>
    request<{ access_token: string; user: import('./types').User }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),

  getDashboard: () => request<{ items: import('./types').DashboardItem[]; emergency: unknown }>('/ops/dashboard'),

  getHeatmap: () => request<{ zones: import('./types').ZoneState[]; workers: unknown[]; permits: unknown[] }>('/ops/heatmap'),

  getRisk: (id: string) => request<import('./types').RiskInstance>(`/risk/instances/${id}`),

  getEvidence: (riskId: string) => request<import('./types').EvidencePackage>(`/decision/evidence/by-risk/${riskId}`),

  getTopology: () => request<{ zones: import('./types').ZoneState[] }>('/twin/topology'),

  getScorecard: () => request<import('./types').Scorecard>('/demo/scorecard'),

  loadScenario: () => request('/demo/load-scenario', { method: 'POST' }),

  startReplay: () => request('/demo/replay/start', { method: 'POST' }),

  stepReplay: (offset?: number) =>
    request(`/demo/replay/step${offset !== undefined ? `?offset=${offset}` : ''}`, { method: 'POST' }),

  resetDemo: () => request('/demo/reset', { method: 'POST' }),

  acknowledgeRisk: (id: string, note?: string) =>
    request(`/ops/risk/${id}/acknowledge`, { method: 'POST', body: JSON.stringify({ action: 'acknowledge', note }) }),

  declareEmergency: (zoneId: string, riskId?: string) =>
    request('/ops/emergency/declare', { method: 'POST', body: JSON.stringify({ zone_id: zoneId, risk_id: riskId }) }),

  getMotifs: () => request<unknown[]>('/motifs'),
};
