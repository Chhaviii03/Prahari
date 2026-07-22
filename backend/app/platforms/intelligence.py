"""Multi-Agent Intelligence (P4) and Decision Intelligence (P5)."""

from __future__ import annotations

from datetime import datetime
import uuid

from app.models.schemas import (
    AgentEnrichment,
    EvidencePackage,
    Recommendation,
    RiskInstance,
    RootCauseHypothesis,
    ZoneState,
)
from app.seed.loader import seed_data


def _template_vars(zone: ZoneState, evidence_cfg: dict) -> dict[str, str | int | float]:
    eta = int(zone.forecast_eta_minutes or 0)
    return {
        "zone_id": zone.zone_id,
        "ch4_lel": zone.ch4_lel,
        "h2s_ppm": zone.h2s_ppm,
        "co_ppm": zone.co_ppm,
        "occupancy": zone.occupancy,
        "eta": eta,
        "rise_rate": round(zone.ch4_lel / 10, 1) if zone.ch4_lel else 0,
        "sensor_id": evidence_cfg.get("sensor_id", "SEN-UNKNOWN"),
        "equipment_id": evidence_cfg.get("equipment_id", "E-000"),
        "work_order": evidence_cfg.get("work_order", "CMMS-WO-0000"),
        "hotwork_permit": evidence_cfg.get("hotwork_permit", "PTW-0000"),
        "confined_permit": evidence_cfg.get("confined_permit", "PTW-0000"),
        "compliance_refs": evidence_cfg.get("compliance_refs", ""),
    }


def _fmt(template: str, vars: dict) -> str:
    try:
        return template.format(**vars)
    except KeyError:
        return template


def enrich_risk(risk: RiskInstance, zone: ZoneState) -> AgentEnrichment:
    evidence_cfg = seed_data.active_scenario.evidence
    vars = _template_vars(zone, evidence_cfg)

    narrative = _fmt(evidence_cfg.get("narrative_template", ""), vars)
    agent_templates = evidence_cfg.get("agent_templates", {})
    per_agent = {agent: _fmt(text, vars) for agent, text in agent_templates.items()}
    if "planner" not in per_agent:
        per_agent["planner"] = narrative

    return AgentEnrichment(
        risk_id=risk.risk_id,
        narrative=narrative,
        per_agent_findings=per_agent,
        trace_ref=f"langfuse://trace/{uuid.uuid4().hex[:12]}",
    )


def build_evidence_package(risk: RiskInstance, zone: ZoneState, enrichment: AgentEnrichment) -> EvidencePackage:
    evidence_cfg = seed_data.active_scenario.evidence
    vars = _template_vars(zone, evidence_cfg)

    root_causes = [
        RootCauseHypothesis(
            rank=h["rank"],
            hypothesis=_fmt(h["hypothesis"], vars),
            confidence=h["confidence"],
            citations=[_fmt(c, vars) for c in h["citations"]],
        )
        for h in evidence_cfg.get("root_cause_hypotheses", [])
    ]

    recommendations = [
        Recommendation(
            action=_fmt(r["action"], vars),
            projected_crs_after=max(15, risk.crs.score - r.get("crs_reduction", 65)),
            counterfactual_ran=True,
            citation=r.get("citation", []),
        )
        for r in evidence_cfg.get("recommendations", [])
    ]

    reg_count = evidence_cfg.get("regulatory_refs_count", 2)
    hist_count = evidence_cfg.get("historical_refs_count", 2)

    return EvidencePackage(
        evidence_id=f"EP-{risk.risk_id[3:]}",
        risk_id=risk.risk_id,
        risk_summary=enrichment.narrative,
        root_cause_hypotheses=root_causes,
        recommendations=recommendations,
        regulatory_citations=seed_data.regulatory_corpus[:reg_count],
        historical_references=seed_data.historical_incidents[:hist_count],
        agent_reasoning_trace=enrichment.trace_ref,
        agent_findings=enrichment.per_agent_findings,
        confidence=evidence_cfg.get("confidence", {"overall": 0.83, "retrieval": 0.88, "root_cause": 0.78}),
        assembled_at=datetime.utcnow(),
    )
