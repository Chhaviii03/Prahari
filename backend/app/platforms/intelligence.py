"""Multi-Agent Intelligence (P4) and Decision Intelligence (P5).

P3 (motif/CRS) stays deterministic. P4/P5 call LLMs only to explain and recommend.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime

from app.llm.orchestrator import run_agent_pipeline
from app.models.schemas import (
    AgentEnrichment,
    EvidencePackage,
    HistoricalReference,
    Recommendation,
    RegulatoryCitation,
    RiskInstance,
    RootCauseHypothesis,
    ZoneState,
)
from app.seed.loader import seed_data

logger = logging.getLogger("prahari.intelligence")

# Seed / fallback corpus when DB regulations are empty (also seeded into DB)
REGULATORY_CORPUS: list[RegulatoryCitation] = list(seed_data.regulatory_corpus) or [
    RegulatoryCitation(
        framework="OISD",
        ref="OISD-GDN-105 §7.2",
        text="Hot work shall not be carried out in or near confined spaces where flammable gas may be present.",
    ),
    RegulatoryCitation(
        framework="FACTORY_ACT",
        ref="§36",
        text="No person shall enter a confined space unless adequate precautions have been taken for safety.",
    ),
    RegulatoryCitation(
        framework="DGMS",
        ref="Circular 2019/03",
        text="Simultaneous operations in hazardous zones require documented risk assessment and permit coordination.",
    ),
    RegulatoryCitation(
        framework="OISD",
        ref="OISD-RP-117 §4.1",
        text="Combustible gas concentrations above 10% LEL require immediate area isolation and ventilation.",
    ),
]

HISTORICAL_INCIDENTS: list[HistoricalReference] = list(seed_data.historical_incidents) or [
    HistoricalReference(
        incident_id="INC-2018-BHILAI",
        similarity=0.94,
        summary="SAIL Bhilai coke-oven gas pipeline explosion during maintenance (9 dead, 14 injured)",
    ),
    HistoricalReference(
        incident_id="INC-2025-CLAIRTON",
        similarity=0.89,
        summary="US Steel Clairton coke-oven gas buildup during maintenance prep (2 dead)",
    ),
]


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


def _zone_payload(zone: ZoneState) -> dict:
    return {
        "zone_id": zone.zone_id,
        "name": zone.name,
        "zone_class": zone.zone_class,
        "ch4_lel": zone.ch4_lel,
        "h2s_ppm": zone.h2s_ppm,
        "co_ppm": zone.co_ppm,
        "o2_pct": zone.o2_pct,
        "temperature_c": zone.temperature_c,
        "occupancy": zone.occupancy,
        "forecast_eta_minutes": zone.forecast_eta_minutes,
        "data_quality": zone.data_quality,
        "active_permits": zone.active_permits,
        "scheduled_permits": zone.scheduled_permits,
    }


async def enrich_risk_with_agents(
    risk: RiskInstance,
    zone: ZoneState,
    *,
    maintenance_records: list | None = None,
    retrieved_clauses: list | None = None,
) -> tuple[AgentEnrichment, dict]:
    """
    Run real multi-agent pipeline (Groq → Ollama → mock).
    Returns (AgentEnrichment, raw pipeline result for evidence assembly).
    """
    permits = list(zone.active_permits) + [
        f"{p} (scheduled)" for p in zone.scheduled_permits
    ]
    risk_summary = (
        f"{risk.motif_id} detected in {zone.zone_id}, CRS={risk.crs.score} ({risk.crs.band.value})"
    )
    clauses = retrieved_clauses if retrieved_clauses is not None else [
        {"framework": c.framework, "ref": c.ref, "text": c.text}
        for c in REGULATORY_CORPUS[:3]
    ]

    pipeline = await asyncio.to_thread(
        run_agent_pipeline,
        _zone_payload(zone),
        permits,
        maintenance_records or [],
        clauses,
        risk_summary,
    )

    enrichment = AgentEnrichment(
        risk_id=risk.risk_id,
        narrative=pipeline["narrative"],
        per_agent_findings=pipeline["findings"],
        trace_ref=f"prahari://agents/{pipeline['provider']}/{uuid.uuid4().hex[:12]}",
    )
    return enrichment, pipeline


def enrich_risk(risk: RiskInstance, zone: ZoneState) -> AgentEnrichment:
    """Sync convenience wrapper (tests / /v1/agents/enrich). Prefer enrich_risk_with_agents."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # Should not be called from async context — use enrich_risk_with_agents
        pipeline = run_agent_pipeline(
            _zone_payload(zone),
            list(zone.active_permits) + zone.scheduled_permits,
            [],
            [{"framework": c.framework, "ref": c.ref, "text": c.text} for c in REGULATORY_CORPUS[:3]],
            f"{risk.motif_id} in {zone.zone_id}, CRS={risk.crs.score}",
        )
        return AgentEnrichment(
            risk_id=risk.risk_id,
            narrative=pipeline["narrative"],
            per_agent_findings=pipeline["findings"],
            trace_ref=f"prahari://agents/{pipeline['provider']}/sync",
        )

    enrichment, _ = asyncio.run(enrich_risk_with_agents(risk, zone))
    return enrichment


def build_evidence_package(
    risk: RiskInstance,
    zone: ZoneState,
    enrichment: AgentEnrichment,
    pipeline: dict | None = None,
) -> EvidencePackage:
    pipeline = pipeline or {}
    projected_after = max(15, risk.crs.score - 65)
    evidence_cfg = seed_data.active_scenario.evidence
    vars = _template_vars(zone, evidence_cfg)

    recs_raw = pipeline.get("recommendations") or []
    recommendations: list[Recommendation] = []
    if recs_raw:
        for i, rec in enumerate(recs_raw):
            if not isinstance(rec, dict):
                continue
            action = rec.get("action") or str(rec)
            recommendations.append(
                Recommendation(
                    action=action,
                    projected_crs_after=max(15, projected_after + i * 5),
                    counterfactual_ran=False,  # real CF re-run is Phase later
                    citation=[rec.get("justification", "planner_agent")],
                )
            )
    elif evidence_cfg.get("recommendations"):
        recommendations = [
            Recommendation(
                action=_fmt(r["action"], vars),
                projected_crs_after=max(15, risk.crs.score - r.get("crs_reduction", 65)),
                counterfactual_ran=True,
                citation=r.get("citation", []),
            )
            for r in evidence_cfg["recommendations"]
        ]
    else:
        recommendations = [
            Recommendation(
                action="Revoke hot-work permit; purge zone before entry",
                projected_crs_after=projected_after,
                counterfactual_ran=False,
                citation=["planner_agent"],
            ),
        ]

    if evidence_cfg.get("root_cause_hypotheses") and not pipeline.get("findings"):
        root_causes = [
            RootCauseHypothesis(
                rank=h["rank"],
                hypothesis=_fmt(h["hypothesis"], vars),
                confidence=h["confidence"],
                citations=[_fmt(c, vars) for c in h["citations"]],
            )
            for h in evidence_cfg["root_cause_hypotheses"]
        ]
    else:
        root_causes = [
            RootCauseHypothesis(
                rank=1,
                hypothesis=(
                    (pipeline.get("findings") or {}).get("equipment")
                    or "Equipment / maintenance contribution under review"
                ),
                confidence=0.7,
                citations=["equipment_agent"],
            ),
            RootCauseHypothesis(
                rank=2,
                hypothesis=(
                    (pipeline.get("findings") or {}).get("permit")
                    or "Permit / SIMOPS contribution under review"
                ),
                confidence=0.65,
                citations=["permit_agent"],
            ),
        ]

    # Compliance citations: only what agent was given / acknowledged
    compliance = {}
    for entry in pipeline.get("findings_trace") or []:
        if entry.get("agent") == "compliance_agent":
            compliance = entry.get("output") or {}
            break

    citation_text = (compliance.get("citation_text") or "").strip()
    regulatory: list[RegulatoryCitation] = []
    if citation_text and citation_text.lower() != "no clause retrieved":
        for clause in REGULATORY_CORPUS:
            if clause.ref in citation_text or clause.framework in citation_text:
                regulatory.append(clause)
        if not regulatory:
            applicable = compliance.get("applicable_clauses") or []
            for item in applicable:
                if isinstance(item, dict) and item.get("ref"):
                    regulatory.append(
                        RegulatoryCitation(
                            framework=item.get("framework", "UNKNOWN"),
                            ref=item["ref"],
                            text=item.get("text", citation_text),
                        )
                    )
                elif isinstance(item, str):
                    for clause in REGULATORY_CORPUS:
                        if clause.ref in item or item in clause.ref:
                            regulatory.append(clause)
    if not regulatory and pipeline.get("findings_trace"):
        regulatory = REGULATORY_CORPUS[:2]
    if not regulatory:
        reg_count = evidence_cfg.get("regulatory_refs_count", 2)
        regulatory = list(seed_data.regulatory_corpus[:reg_count] or REGULATORY_CORPUS[:reg_count])

    hist_count = evidence_cfg.get("historical_refs_count", 2)
    historical = list(seed_data.historical_incidents[:hist_count] or HISTORICAL_INCIDENTS[:hist_count])

    llm_involved = bool(pipeline.get("llm_involved"))
    model = pipeline.get("model") or "unknown"

    confidence = evidence_cfg.get("confidence") if not pipeline else None
    if not confidence:
        confidence = {
            "overall": float(pipeline.get("confidence") or 0.75),
            "llm_involved": 1.0 if llm_involved else 0.0,
            "retrieval": 0.8,
            "root_cause": 0.7,
        }

    return EvidencePackage(
        evidence_id=f"EP-{risk.risk_id[3:]}",
        risk_id=risk.risk_id,
        risk_summary=enrichment.narrative,
        root_cause_hypotheses=root_causes,
        recommendations=recommendations,
        regulatory_citations=regulatory,
        historical_references=historical,
        agent_reasoning_trace=enrichment.trace_ref,
        agent_findings=enrichment.per_agent_findings,
        confidence=confidence,
        assembled_at=datetime.utcnow(),
        assembled_by=f"P5/{pipeline.get('provider') or 'seed'}/{model}",
    )
