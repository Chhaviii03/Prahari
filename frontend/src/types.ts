export interface CRS {
  score: number;
  band: 'WATCH' | 'ACTIVE' | 'CRITICAL';
  components: { severity: number; confidence: number; recency: number };
}

export interface RiskInstance {
  risk_id: string;
  org_id: string;
  plant_id: string;
  zone_id: string;
  status: string;
  motif_id: string;
  motif_version: string;
  crs: CRS;
  lead_time_seconds: number | null;
  contributing_signals: { type: string; value: string }[];
  detection: { method: string; deterministic: boolean; llm_involved: boolean };
  evidence_package_id: string | null;
  narrative: string | null;
  timeline: { ts: string; event: string; actor: string; note?: string }[];
  created_at: string;
  updated_at: string;
}

export interface DashboardItem {
  risk: RiskInstance;
  summary: string;
  hazard_icons: string[];
}

export interface ZoneState {
  zone_id: string;
  name: string;
  zone_class: string;
  crs: number;
  band: string;
  ch4_lel: number;
  h2s_ppm: number;
  co_ppm: number;
  o2_pct: number;
  temperature_c: number;
  occupancy: number;
  active_permits: string[];
  scheduled_permits: string[];
  forecast_eta_minutes: number | null;
  data_quality: string;
  geo: {
    lat?: number;
    lng?: number;
    x?: number;
    y?: number;
    level?: string;
    polygon?: [number, number][];
  };
}

export interface EvidencePackage {
  evidence_id: string;
  risk_id: string;
  risk_summary: string;
  root_cause_hypotheses: { rank: number; hypothesis: string; confidence: number; citations: string[] }[];
  recommendations: { action: string; projected_crs_after: number; counterfactual_ran: boolean; citation: string[] }[];
  regulatory_citations: { framework: string; ref: string; text: string }[];
  historical_references: { incident_id: string; similarity: number; summary: string }[];
  agent_findings: Record<string, string>;
  confidence: Record<string, number>;
  assembled_at: string;
}

export interface User {
  user_id: string;
  username: string;
  role: string;
  name: string;
  zone_id?: string;
}

export interface PermitRecord {
  permit_id: string;
  zone_id: string;
  zone_name: string;
  status: string;
  type: string;
  conflicts: string[];
  severity: string;
}

export interface NotificationItem {
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
}

export interface AnalyticsData {
  scenario_name: string;
  replay_offset: number;
  metrics: Record<string, number>;
  motif_performance: { motif_id: string; name: string; version: string; fires_in_session: number; avg_lead_time_min: number | null; precision: number | null }[];
  crs_timeline: { offset: number; crs: string }[];
  active_risks: number;
}

export interface ExecutiveData {
  plant_name: string;
  period: string;
  kpis: Record<string, number>;
  trends: { month: string; incidents: number; near_misses: number; prahari_catches: number }[];
  motif_breakdown: { motif: string; count: number }[];
  regulatory_exposure: string[];
}

export interface ReportRecord {
  report_id: string;
  type: string;
  title: string;
  zone_id?: string;
  risk_id?: string;
  status: string;
  created_at: string;
  exportable: boolean;
}

export interface CopilotResponse {
  question: string;
  answer: string;
  citations: { framework: string; ref: string; text: string }[];
  sources: string[];
  grounded: boolean;
  risk_id?: string;
}

export interface AdminUser {
  user_id: string;
  username: string;
  name: string;
  role: string;
  zone_id?: string;
}

export interface SettingsData {
  integrations: { id: string; name: string; status: string; last_event: string | null }[];
  thresholds_view: Record<string, number>;
  active_scenario: string;
  forecast_horizon_min: number;
}
