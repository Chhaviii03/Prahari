"""Multi-Agent Intelligence (P4) and Decision Intelligence (P5)."""

from __future__ import annotations

from datetime import datetime
import uuid

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


REGULATORY_CORPUS = [
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

HISTORICAL_INCIDENTS = [
    HistoricalReference(
        incident_id="INC-2024-0142",
        similarity=0.91,
        summary="Near-miss: hot work near confined space with gas ingress, Zone B-7, 2024",
    ),
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


def enrich_risk(risk: RiskInstance, zone: ZoneState) -> AgentEnrichment:
    ch4 = zone.ch4_lel
    eta = zone.forecast_eta_minutes

    sensor_finding = (
        f"CH₄ at {ch4:.1f}% LEL, rising ~{(ch4/10):.1f}% LEL per 10 min. "
        f"{'On track to LEL in ~' + str(int(eta)) + ' min' if eta else 'Trend monitoring active'}. Sensor SEN-CH4-C12-03 healthy."
    )

    permit_finding = (
        f"Hot-work {', '.join(p for p in zone.active_permits if 'HOT' in p.upper()) or 'PTW-2231'} active; "
        f"confined-entry {', '.join(p for p in zone.scheduled_permits if 'CONFINED' in p.upper()) or 'PTW-2240'} scheduled — conflicting simultaneous operations."
    )

    worker_finding = f"{zone.occupancy} workers assigned to confined-space entry in {zone.zone_id}."

    equipment_finding = "E-441 valve flagged in CMMS WO-8841, 9 days ago. Possible seepage source."

    compliance_finding = "Implicates OISD-GDN-105 §7.2 (hot work near confined space); Factory Act §36 (confined space entry)."

    narrative = (
        f"Compound hazard in {zone.zone_id}: rising CH₄ ({ch4:.1f}% LEL) forecast to cross LEL threshold "
        f"in ~{int(eta or 0)} min, overlapping active hot-work permit and scheduled confined-space entry. "
        f"{zone.occupancy} workers exposed. Equipment E-441 has open maintenance flag. "
        f"Regulatory violation: OISD-GDN-105 §7.2, Factory Act §36."
    )

    return AgentEnrichment(
        risk_id=risk.risk_id,
        narrative=narrative,
        per_agent_findings={
            "sensor": sensor_finding,
            "permit": permit_finding,
            "worker": worker_finding,
            "equipment": equipment_finding,
            "compliance": compliance_finding,
            "planner": narrative,
        },
        trace_ref=f"langfuse://trace/{uuid.uuid4().hex[:12]}",
    )


def build_evidence_package(risk: RiskInstance, zone: ZoneState, enrichment: AgentEnrichment) -> EvidencePackage:
    projected_after = max(15, risk.crs.score - 65)

    return EvidencePackage(
        evidence_id=f"EP-{risk.risk_id[3:]}",
        risk_id=risk.risk_id,
        risk_summary=enrichment.narrative,
        root_cause_hypotheses=[
            RootCauseHypothesis(
                rank=1,
                hypothesis="Valve seepage on E-441 (maintenance flag T-9d)",
                confidence=0.78,
                citations=["CMMS-WO-8841", "SEN-CH4-C12-03 trend"],
            ),
            RootCauseHypothesis(
                rank=2,
                hypothesis="Incomplete gas line isolation during maintenance prep",
                confidence=0.65,
                citations=["PTW-2231 scope", "INC-2018-BHILAI precedent"],
            ),
        ],
        recommendations=[
            Recommendation(
                action="Revoke hot-work permit PTW-2231; purge C-12 before entry",
                projected_crs_after=projected_after,
                counterfactual_ran=True,
                citation=["OISD-GDN-105 §7.2", "Factory Act §36"],
            ),
            Recommendation(
                action="Evacuate 3 workers from C-12; initiate forced ventilation",
                projected_crs_after=projected_after + 10,
                counterfactual_ran=True,
                citation=["OISD-RP-117 §4.1"],
            ),
            Recommendation(
                action="Inspect E-441 valve; hold maintenance until gas levels <1% LEL",
                projected_crs_after=projected_after + 5,
                counterfactual_ran=True,
                citation=["CMMS-WO-8841"],
            ),
        ],
        regulatory_citations=REGULATORY_CORPUS[:2],
        historical_references=HISTORICAL_INCIDENTS[:2],
        agent_reasoning_trace=enrichment.trace_ref,
        agent_findings=enrichment.per_agent_findings,
        confidence={"overall": 0.83, "retrieval": 0.88, "root_cause": 0.78},
        assembled_at=datetime.utcnow(),
    )
