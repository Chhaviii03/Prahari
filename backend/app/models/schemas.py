from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RiskStatus(str, Enum):
    WATCH = "WATCH"
    ACTIVE = "ACTIVE"
    CRITICAL = "CRITICAL"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    ESCALATED = "ESCALATED"
    RESOLVED = "RESOLVED"
    FALSE_POSITIVE = "FALSE_POSITIVE"


class CRSBand(str, Enum):
    WATCH = "WATCH"
    ACTIVE = "ACTIVE"
    CRITICAL = "CRITICAL"


class UserRole(str, Enum):
    SAFETY_OFFICER = "safety_officer"
    PERMIT_OFFICER = "permit_officer"
    SUPERVISOR = "supervisor"
    COMPLIANCE_OFFICER = "compliance_officer"
    EXECUTIVE = "executive"
    WORKER = "worker"
    ADMIN = "admin"


class ContributingSignal(BaseModel):
    type: str
    value: str
    source_event: str | None = None


class CRSComponents(BaseModel):
    severity: float
    confidence: float
    recency: float


class CRS(BaseModel):
    score: float
    band: CRSBand
    components: CRSComponents


class DetectionInfo(BaseModel):
    method: str = "MOTIF"
    deterministic: bool = True
    llm_involved: bool = False


class TimelineEvent(BaseModel):
    ts: datetime
    event: str
    actor: str
    note: str | None = None


class RiskInstance(BaseModel):
    risk_id: str
    org_id: str
    plant_id: str
    zone_id: str
    status: RiskStatus
    motif_id: str
    motif_version: str
    crs: CRS
    lead_time_seconds: int | None = None
    contributing_signals: list[ContributingSignal]
    detection: DetectionInfo
    evidence_package_id: str | None = None
    narrative: str | None = None
    timeline: list[TimelineEvent] = []
    created_at: datetime
    updated_at: datetime


class RegulatoryCitation(BaseModel):
    framework: str
    ref: str
    text: str


class RootCauseHypothesis(BaseModel):
    rank: int
    hypothesis: str
    confidence: float
    citations: list[str]


class Recommendation(BaseModel):
    action: str
    projected_crs_after: float
    counterfactual_ran: bool
    citation: list[str]


class HistoricalReference(BaseModel):
    incident_id: str
    similarity: float
    summary: str


class EvidencePackage(BaseModel):
    evidence_id: str
    risk_id: str
    risk_summary: str
    root_cause_hypotheses: list[RootCauseHypothesis]
    recommendations: list[Recommendation]
    regulatory_citations: list[RegulatoryCitation]
    historical_references: list[HistoricalReference]
    agent_reasoning_trace: str | None = None
    agent_findings: dict[str, str] = {}
    confidence: dict[str, float]
    assembled_at: datetime
    assembled_by: str = "P5"


class ZoneState(BaseModel):
    zone_id: str
    name: str
    zone_class: str
    crs: float = 0
    band: CRSBand = CRSBand.WATCH
    ch4_lel: float = 0
    h2s_ppm: float = 0
    co_ppm: float = 0
    o2_pct: float = 20.9
    temperature_c: float = 25
    occupancy: int = 0
    active_permits: list[str] = []
    scheduled_permits: list[str] = []
    forecast_eta_minutes: float | None = None
    data_quality: str = "GOOD"
    geo: dict[str, float | str] = {}


class PlantTopology(BaseModel):
    plant_id: str
    name: str
    zones: list[ZoneState]


class CanonicalEvent(BaseModel):
    event_id: str
    org_id: str
    plant_id: str
    entity_type: str
    entity_id: str
    zone_id: str
    measurement_type: str
    value: float
    unit: str
    quality: str = "GOOD"
    event_time: datetime
    ingest_time: datetime


class AgentEnrichment(BaseModel):
    risk_id: str
    narrative: str
    per_agent_findings: dict[str, str]
    trace_ref: str


class ScorecardResult(BaseModel):
    scenario_name: str
    baseline_detected: bool
    baseline_lead_time_minutes: float
    prahari_detected: bool
    prahari_lead_time_minutes: float
    prahari_crs: float
    prahari_motif: str
    regulatory_citations: list[str]
    fnr_reduction_pct: float
    precision: float
    recall: float
    baseline_recall: float
    timeline: list[dict[str, Any]]


class DashboardItem(BaseModel):
    risk: RiskInstance
    summary: str
    hazard_icons: list[str]


class HeatmapData(BaseModel):
    plant_id: str
    zones: list[ZoneState]
    workers: list[dict[str, Any]]
    permits: list[dict[str, Any]]
    evacuation_routes: list[dict[str, Any]]


class User(BaseModel):
    user_id: str
    username: str
    role: UserRole
    name: str
    zone_id: str | None = None


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: User


class TriageAction(BaseModel):
    action: str
    note: str | None = None
    justification: str | None = None


class EmergencyDeclare(BaseModel):
    zone_id: str
    risk_id: str | None = None


class EmergencyStatus(BaseModel):
    active: bool
    zone_id: str | None = None
    risk_id: str | None = None
    steps: list[dict[str, Any]]
    declared_at: datetime | None = None


class OutcomeRecord(BaseModel):
    risk_id: str
    classification: str
    recommendation_rating: int = Field(ge=1, le=5)
    root_cause_rating: int = Field(ge=1, le=5)
    notes: str | None = None


class ReplayState(BaseModel):
    running: bool
    current_time_offset: int
    total_duration: int
    scenario_name: str
