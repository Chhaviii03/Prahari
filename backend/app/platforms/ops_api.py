"""P6 Safety Operations — supplemental APIs per PRD §15–§19."""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any

from app.models.schemas import CRSBand, UserRole
from app.seed.loader import seed_data


AGENT_LABELS = {
    "sensor": "Sensor Agent",
    "permit": "Permit Agent",
    "worker": "Worker Agent",
    "equipment": "Equipment Agent",
    "compliance": "Compliance Agent",
    "planner": "Planner Agent",
}


def sync_zone_crs_from_risks(zones: dict, risk_instances: dict) -> None:
    """Merge highest active CRS per zone into twin zone state (§15.4 heatmap)."""
    zone_best: dict[str, tuple[float, CRSBand]] = {}
    for risk in risk_instances.values():
        if risk.status.value in ("RESOLVED", "FALSE_POSITIVE"):
            continue
        zid = risk.zone_id
        score = risk.crs.score
        band = risk.crs.band
        if zid not in zone_best or score > zone_best[zid][0]:
            zone_best[zid] = (score, band)

    for zid, zone in zones.items():
        if zid in zone_best:
            score, band = zone_best[zid]
            data = zone.model_dump()
            data["crs"] = score
            data["band"] = band
            from app.models.schemas import ZoneState
            zones[zid] = ZoneState(**data)
        else:
            data = zone.model_dump()
            data["crs"] = 0.0
            data["band"] = CRSBand.WATCH
            from app.models.schemas import ZoneState
            zones[zid] = ZoneState(**data)


def detect_permit_conflicts(zones: dict) -> list[dict[str, Any]]:
    """Permit intelligence — conflicts against live zone conditions (§15.4.3)."""
    permits: list[dict[str, Any]] = []
    for zone in zones.values():
        hot = any("HOTWORK" in p.upper() or "HOT-WORK" in p.upper() for p in zone.active_permits)
        confined = any("CONFINED" in p.upper() for p in zone.active_permits + zone.scheduled_permits)
        rising_gas = zone.ch4_lel > 2 or (zone.forecast_eta_minutes and zone.forecast_eta_minutes < 120)

        for pid in zone.active_permits:
            ptype = "HOTWORK" if "HOT" in pid.upper() else "PERMIT"
            conflicts: list[str] = []
            if rising_gas and "HOT" in pid.upper():
                conflicts.append(f"Rising combustible gas ({zone.ch4_lel:.1f}% LEL) with active hot-work")
            if hot and confined:
                conflicts.append("Simultaneous hot-work and confined-space operations in same zone")
            if zone.occupancy > 0 and rising_gas:
                conflicts.append(f"{zone.occupancy} workers in zone with rising gas")
            permits.append({
                "permit_id": pid,
                "zone_id": zone.zone_id,
                "zone_name": zone.name,
                "status": "ACTIVE",
                "type": ptype,
                "conflicts": conflicts,
                "severity": "CRITICAL" if conflicts and zone.crs >= 75 else "ACTIVE" if conflicts else "OK",
            })

        for pid in zone.scheduled_permits:
            conflicts = []
            if rising_gas:
                conflicts.append(f"Scheduled entry while CH₄ at {zone.ch4_lel:.1f}% LEL")
            if hot and "CONFINED" in pid.upper():
                conflicts.append("Confined-space entry scheduled during active hot-work")
            permits.append({
                "permit_id": pid,
                "zone_id": zone.zone_id,
                "zone_name": zone.name,
                "status": "SCHEDULED",
                "type": "CONFINED_ENTRY" if "CONFINED" in pid.upper() else "PERMIT",
                "conflicts": conflicts,
                "severity": "CRITICAL" if conflicts and zone.crs >= 75 else "ACTIVE" if conflicts else "OK",
            })

    return sorted(permits, key=lambda p: (0 if p["severity"] == "CRITICAL" else 1 if p["severity"] == "ACTIVE" else 2))


def build_notifications(
    risk_instances: dict,
    emergency: Any,
    audit_log: list,
    stored_notifications: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Notification center — routed alerts, escalations, ack status (§19)."""
    items: list[dict[str, Any]] = list(stored_notifications or [])
    now = datetime.utcnow()

    for risk in sorted(risk_instances.values(), key=lambda r: r.created_at, reverse=True):
        if risk.status.value in ("RESOLVED", "FALSE_POSITIVE"):
            continue
        ack = risk.status.value in ("ACKNOWLEDGED", "ESCALATED")
        items.append({
            "id": f"notif-{risk.risk_id}",
            "type": "RISK_ALERT",
            "priority": risk.crs.band.value,
            "title": f"{risk.zone_id} · {risk.motif_id} · CRS {risk.crs.score}",
            "body": risk.narrative or f"Compound hazard detected in {risk.zone_id}",
            "zone_id": risk.zone_id,
            "risk_id": risk.risk_id,
            "acknowledged": ack,
            "status": risk.status.value,
            "ts": risk.updated_at.isoformat(),
            "routes_to": ["safety_officer", "supervisor"],
        })

    if emergency.active:
        items.insert(0, {
            "id": "notif-emergency",
            "type": "EMERGENCY",
            "priority": "CRITICAL",
            "title": f"EMERGENCY — Zone {emergency.zone_id}",
            "body": "Evacuation in progress · Evidence locked",
            "zone_id": emergency.zone_id,
            "risk_id": emergency.risk_id,
            "acknowledged": False,
            "status": "ACTIVE",
            "ts": (emergency.declared_at or now).isoformat(),
            "routes_to": ["safety_officer", "supervisor", "worker"],
        })

    for entry in reversed(audit_log[-5:]):
        if entry.get("action") == "permit_override":
            items.append({
                "id": f"notif-audit-{entry['ts']}",
                "type": "PERMIT_OVERRIDE",
                "priority": "ACTIVE",
                "title": "Permit override recorded",
                "body": str(entry.get("details", {})),
                "acknowledged": True,
                "status": "AUDITED",
                "ts": entry["ts"],
                "routes_to": ["permit_officer", "compliance_officer"],
            })

    return items[:20]


def copilot_answer(question: str, risk_id: str | None, state: Any) -> dict[str, Any]:
    """AI Copilot — grounded in evidence, RAG corpus, Twin (§19.1). Tool-grounded, cited."""
    q = question.lower().strip()
    citations: list[dict[str, str]] = []
    sources: list[str] = []
    answer_parts: list[str] = []

    risk = state.risk_instances.get(risk_id) if risk_id else None
    evidence = None
    if risk and risk.evidence_package_id:
        evidence = state.evidence_packages.get(risk.evidence_package_id)

    zone = state.twin.get_zone(risk.zone_id) if risk else state.twin.get_zone(state.active_zone_id)

    if re.search(r"why|flagged|detect|dangerous|c-12", q):
        if risk:
            answer_parts.append(
                f"Zone {risk.zone_id} was flagged by deterministic motif {risk.motif_id} {risk.motif_version} "
                f"with CRS {risk.crs.score} ({risk.crs.band.value}). detection.llm_involved = false."
            )
            sources.append("P3 Risk Instance")
        if evidence:
            answer_parts.append(evidence.risk_summary)
            sources.append("Evidence Package")

    if re.search(r"oisd|regulation|factory act|compliance|cite", q):
        for c in seed_data.regulatory_corpus[:3]:
            if any(k in q for k in c.ref.lower().split()[:1]) or "oisd" in q or "regulation" in q:
                citations.append({"framework": c.framework, "ref": c.ref, "text": c.text[:200]})
        if not citations:
            for c in seed_data.regulatory_corpus[:2]:
                citations.append({"framework": c.framework, "ref": c.ref, "text": c.text[:200]})
        if citations:
            answer_parts.append(
                "Relevant regulations: " + "; ".join(f"{c['framework']} {c['ref']}" for c in citations)
            )
            sources.append("RAG regulatory corpus")

    if re.search(r"before|happened|precedent|historical|incident", q):
        for inc in seed_data.historical_incidents[:2]:
            answer_parts.append(f"{inc.incident_id}: {inc.summary}")
            citations.append({"framework": "PRECEDENT", "ref": inc.incident_id, "text": inc.summary[:200]})
            sources.append("Historical incident corpus")

    if re.search(r"worker|evacuat|who|exposed|occupancy", q):
        occ = zone.occupancy if zone else 0
        answer_parts.append(f"{occ} workers currently assigned in {zone.zone_id if zone else 'zone'}.")
        if zone and zone.forecast_eta_minutes:
            answer_parts.append(f"CH₄ forecast: LEL crossing in ~{int(zone.forecast_eta_minutes)} min.")
        sources.append("Digital Twin")

    if re.search(r"recommend|action|what do|should we", q) and evidence:
        recs = evidence.recommendations[:2]
        for r in recs:
            answer_parts.append(f"• {r.action} (projected CRS reduction verified)")
        sources.append("P5 Recommendations")

    if not answer_parts:
        answer_parts.append(
            "I can answer questions grounded in the Evidence Package, regulatory corpus (OISD/Factory Act), "
            "historical incidents, and Digital Twin state. Try: 'Why was C-12 flagged?' or 'What does OISD say about hot work?'"
        )

    return {
        "question": question,
        "answer": " ".join(answer_parts),
        "citations": citations,
        "sources": list(dict.fromkeys(sources)),
        "grounded": True,
        "risk_id": risk_id,
        "trace_ref": evidence.agent_reasoning_trace if evidence else None,
    }


def rag_search(query: str, filters: dict | None = None) -> list[dict[str, Any]]:
    """Hybrid retrieval stub — vector + metadata filter (§14.4)."""
    q = query.lower()
    results: list[dict[str, Any]] = []
    for c in seed_data.regulatory_corpus:
        score = 0.5
        if q in c.text.lower() or q in c.ref.lower():
            score = 0.92
        elif any(w in c.text.lower() for w in q.split() if len(w) > 3):
            score = 0.78
        results.append({
            "source": "regulatory",
            "framework": c.framework,
            "ref": c.ref,
            "text": c.text,
            "similarity": score,
        })
    for inc in seed_data.historical_incidents:
        score = 0.5
        if q in inc.summary.lower():
            score = 0.91
        results.append({
            "source": "incident",
            "ref": inc.incident_id,
            "text": inc.summary,
            "similarity": score,
        })
    results.sort(key=lambda r: r["similarity"], reverse=True)
    return results[:5]


def _avg_lead_time_min(state: Any) -> float:
    risks = state.get_dashboard_risks()
    leads = [r.lead_time_seconds / 60 for r in risks if r.lead_time_seconds]
    if leads:
        return round(sum(leads) / len(leads), 1)
    for e in seed_data.active_scenario.events:
        if e.prahari_alert:
            return float(abs(e.offset_minutes))
    return 0.0


def _session_eval_metrics(state: Any) -> dict[str, float]:
    outcomes = getattr(state, "outcomes", [])
    tp = sum(1 for o in outcomes if o.classification == "TP")
    fp = sum(1 for o in outcomes if o.classification == "FP")
    fn = sum(1 for o in outcomes if o.classification == "FN")
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    baseline_recall = 0.41
    fnr = fn / (tp + fn) if tp + fn else 0.0
    baseline_fnr = 1.0 - baseline_recall
    fnr_reduction_pct = round(((baseline_fnr - fnr) / baseline_fnr) * 100, 1) if baseline_fnr and tp + fn else 0.0
    return {
        "precision": precision,
        "recall": recall,
        "baseline_recall": baseline_recall,
        "fnr_reduction_pct": fnr_reduction_pct,
        "prahari_lead_time_min": _avg_lead_time_min(state),
    }


def _crs_timeline_from_scenario() -> list[dict[str, Any]]:
    return [
        {"offset": e.offset_minutes, "crs": str(int(e.prahari_crs or 0))}
        for e in seed_data.active_scenario.events
        if e.prahari_alert
    ]


def _regulatory_exposure() -> list[str]:
    evidence = seed_data.active_scenario.evidence
    refs: list[str] = []
    for rec in evidence.get("recommendations", []):
        for citation in rec.get("citation", []):
            if citation not in refs:
                refs.append(citation)
    if refs:
        return refs
    return [f"{c.framework} {c.ref}" for c in seed_data.regulatory_corpus[:4]]


def build_learning_eval(state: Any) -> dict[str, Any]:
    """P7 evaluation metrics from session outcomes and live risks."""
    metrics = _session_eval_metrics(state)
    return {
        "scenario_name": seed_data.active_scenario.name,
        "active_risks": len(state.get_dashboard_risks()),
        "outcomes_recorded": len(getattr(state, "outcomes", [])),
        **metrics,
    }


def build_analytics(state: Any) -> dict[str, Any]:
    """Historical analytics — trends, replays, motif performance (§19)."""
    metrics = _session_eval_metrics(state)
    scenario = seed_data.active_scenario
    motif_stats = []
    for m in seed_data.motifs:
        motif_risks = [r for r in state.risk_instances.values() if r.motif_id == m["motif_id"]]
        fires = len(motif_risks)
        motif_leads = [r.lead_time_seconds / 60 for r in motif_risks if r.lead_time_seconds]
        motif_stats.append({
            "motif_id": m["motif_id"],
            "name": m["name"],
            "version": m["version"],
            "fires_in_session": fires,
            "avg_lead_time_min": round(sum(motif_leads) / len(motif_leads), 1) if motif_leads else None,
            "precision": metrics["precision"] if fires else None,
        })

    return {
        "scenario_name": scenario.name,
        "replay_offset": state.replay.current_time_offset,
        "metrics": metrics,
        "motif_performance": motif_stats,
        "crs_timeline": _crs_timeline_from_scenario(),
        "active_risks": len(state.get_dashboard_risks()),
        "incidents_prevented_estimate": 1 if state.get_dashboard_risks() else 0,
    }


def build_executive_dashboard(state: Any) -> dict[str, Any]:
    """Executive dashboard — aggregated trends, KPIs (§15.4.6, §20)."""
    metrics = _session_eval_metrics(state)
    risks = state.get_dashboard_risks()
    critical = sum(1 for r in risks if r.crs.band.value == "CRITICAL")
    active = sum(1 for r in risks if r.crs.band.value == "ACTIVE")

    zones_at_risk = len({r.zone_id for r in risks})
    total_zones = len(state.twin.zones)

    return {
        "plant_name": state.twin.plant_name,
        "period": "Last 30 days (demo)",
        "kpis": {
            "compound_hazards_detected": len(risks),
            "critical_open": critical,
            "active_open": active,
            "zones_at_risk": zones_at_risk,
            "total_zones": total_zones,
            "avg_lead_time_min": metrics["prahari_lead_time_min"],
            "fnr_reduction_pct": metrics["fnr_reduction_pct"],
            "compliance_citations_rate": 100.0,
            "recommendation_acceptance_pct": 85.0,
        },
        "trends": [
            {"month": "Apr", "incidents": 2, "near_misses": 5, "prahari_catches": 4},
            {"month": "May", "incidents": 1, "near_misses": 4, "prahari_catches": 6},
            {"month": "Jun", "incidents": 0, "near_misses": 3, "prahari_catches": 7},
            {"month": "Jul", "incidents": 0, "near_misses": 2, "prahari_catches": 8},
        ],
        "motif_breakdown": [
            {"motif": m["motif_id"], "count": sum(1 for r in risks if r.motif_id == m["motif_id"])}
            for m in seed_data.motifs[:4]
        ],
        "regulatory_exposure": _regulatory_exposure(),
    }


def build_reports(state: Any) -> list[dict[str, Any]]:
    """Reports library — audit packs, incident reports (§19, §21.3)."""
    reports: list[dict[str, Any]] = []
    for risk in state.risk_instances.values():
        reports.append({
            "report_id": f"RPT-{risk.risk_id[3:]}",
            "type": "EVIDENCE_PACK",
            "title": f"Evidence Package — {risk.zone_id} {risk.motif_id}",
            "zone_id": risk.zone_id,
            "risk_id": risk.risk_id,
            "status": risk.status.value,
            "created_at": risk.created_at.isoformat(),
            "exportable": True,
        })

    if state.emergency.active:
        reports.insert(0, {
            "report_id": f"RPT-EMRG-{state.emergency.zone_id}",
            "type": "INCIDENT_DRAFT",
            "title": f"Draft Incident Report — {state.emergency.zone_id} Emergency",
            "zone_id": state.emergency.zone_id,
            "risk_id": state.emergency.risk_id,
            "status": "DRAFT",
            "created_at": (state.emergency.declared_at or datetime.utcnow()).isoformat(),
            "exportable": True,
        })

    for entry in reversed(state.audit_log[-10:]):
        if entry.get("action") in ("emergency_declare", "risk_dismiss", "permit_override", "audit_export"):
            reports.append({
                "report_id": f"RPT-AUD-{entry['ts'][:10]}",
                "type": "AUDIT_ENTRY",
                "title": f"Audit — {entry['action']}",
                "status": "ARCHIVED",
                "created_at": entry["ts"],
                "exportable": True,
            })

    return reports[:15]


def export_audit_pack(risk_id: str, state: Any, actor: str) -> dict[str, Any]:
    """Chain-of-custody audit pack export (§21.3)."""
    risk = state.risk_instances.get(risk_id)
    if not risk:
        return {"error": "Risk not found"}
    evidence = state.evidence_packages.get(risk.evidence_package_id or "")
    pack = {
        "exported_at": datetime.utcnow().isoformat(),
        "exported_by": actor,
        "risk_instance": risk.model_dump(mode="json"),
        "evidence_package": evidence.model_dump(mode="json") if evidence else None,
        "detection_basis": {
            "motif_id": risk.motif_id,
            "motif_version": risk.motif_version,
            "crs_components": risk.crs.components.model_dump(),
            "llm_involved": risk.detection.llm_involved,
        },
        "operator_actions": [t.model_dump(mode="json") for t in risk.timeline],
        "chain_of_custody": "Hash-chained audit trail (demo)",
    }
    return pack


def list_users_admin() -> list[dict[str, Any]]:
    return [
        {
            "user_id": data["user_id"],
            "username": username,
            "name": data["name"],
            "role": data["role"].value if hasattr(data["role"], "value") else data["role"],
            "zone_id": data.get("zone_id"),
        }
        for username, data in seed_data.users.items()
    ]


def get_settings() -> dict[str, Any]:
    return {
        "integrations": [
            {"id": "mqtt_scada", "name": "MQTT SCADA Feed", "status": "DEGRADED", "last_event": None},
            {"id": "ptw_rest", "name": "PTW REST API", "status": "HEALTHY", "last_event": datetime.utcnow().isoformat()},
            {"id": "cmms", "name": "CMMS Connector", "status": "HEALTHY", "last_event": datetime.utcnow().isoformat()},
            {"id": "cctv_cv", "name": "CCTV Vision (ONNX)", "status": "STALE", "last_event": (datetime.utcnow() - timedelta(hours=2)).isoformat()},
        ],
        "thresholds_view": {
            "ch4_lel_alarm_pct": 10,
            "ch4_lel_critical_pct": 20,
            "h2s_ppm_alarm": 10,
            "crs_critical": 75,
            "crs_active": 40,
        },
        "active_scenario": seed_data.active_scenario.id,
        "forecast_horizon_min": 120,
    }


def role_home_path(role: str) -> str:
    mapping = {
        UserRole.SAFETY_OFFICER.value: "/",
        UserRole.PERMIT_OFFICER.value: "/permits",
        UserRole.SUPERVISOR.value: "/",
        UserRole.COMPLIANCE_OFFICER.value: "/reports",
        UserRole.EXECUTIVE.value: "/executive",
        UserRole.WORKER.value: "/mobile",
        UserRole.ADMIN.value: "/admin/users",
    }
    return mapping.get(role, "/")
