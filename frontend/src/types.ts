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
  geo: { x: number; y: number; level: string };
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

export interface Scorecard {
  scenario_name: string;
  baseline_detected: boolean;
  baseline_lead_time_minutes: number;
  prahari_detected: boolean;
  prahari_lead_time_minutes: number;
  prahari_crs: number;
  prahari_motif: string;
  regulatory_citations: string[];
  fnr_reduction_pct: number;
  precision: number;
  recall: number;
  baseline_recall: number;
  timeline: { offset: number; description: string; baseline: string; prahari: string }[];
}

export interface User {
  user_id: string;
  username: string;
  role: string;
  name: string;
  zone_id?: string;
}
