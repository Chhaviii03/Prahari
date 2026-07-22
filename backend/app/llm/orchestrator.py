"""Sequential multi-agent orchestrator (P4) — slow lane only."""

from __future__ import annotations

import json
import time
from typing import Any, Callable

from app.llm import agents
from app.llm.resilient_client import ResilientLLMClient


def run_agent_pipeline(
    zone_state: dict,
    permits: list,
    maintenance_records: list,
    retrieved_clauses: list,
    risk_summary: str,
) -> dict[str, Any]:
    """
    Runs Sensor → Permit → Equipment → Compliance → Planner sequentially.
    Returns findings trace + planner narrative/recommendations for evidence_packages.
    """
    llm = ResilientLLMClient()
    trace: list[dict[str, Any]] = []

    def timed_call(name: str, fn: Callable, *args) -> dict[str, Any]:
        start = time.time()
        result = fn(llm, *args)
        latency = int((time.time() - start) * 1000)
        trace.append(
            {
                "agent": name,
                "output": result,
                "latency_ms": latency,
                "provider": llm.last_provider,
                "model": llm.last_model,
            }
        )
        return result

    sensor = timed_call("sensor_agent", agents.run_sensor_agent, zone_state)
    permit = timed_call("permit_agent", agents.run_permit_agent, permits, zone_state)

    # Short-circuit lighter path if permit agent finds no conflict AND gas is quiet
    equipment = timed_call(
        "equipment_agent", agents.run_equipment_agent, maintenance_records
    )
    compliance = timed_call(
        "compliance_agent",
        agents.run_compliance_agent,
        retrieved_clauses,
        risk_summary,
    )
    planner = timed_call(
        "planner_agent",
        agents.run_planner_agent,
        sensor,
        permit,
        equipment,
        compliance,
    )

    recommendations = planner.get("recommendations") or []
    if not isinstance(recommendations, list):
        recommendations = []

    narrative = planner.get("narrative") or _fallback_narrative(sensor, permit, equipment)

    # Flat findings map for EvidencePackage.agent_findings
    findings_map = {
        entry["agent"].replace("_agent", ""): _finding_text(entry["output"])
        for entry in trace
    }
    findings_map["planner"] = narrative

    return {
        "findings_trace": trace,
        "findings": findings_map,
        "narrative": narrative,
        "recommendations": recommendations,
        "confidence": float(planner.get("confidence") or 0.75),
        "provider": llm.last_provider,
        "model": llm.last_model,
        "llm_involved": llm.last_provider != "mock",
    }


def _finding_text(output: dict[str, Any]) -> str:
    if not isinstance(output, dict):
        return str(output)
    for key in (
        "assessment",
        "conflict_description",
        "note",
        "citation_text",
        "narrative",
    ):
        if output.get(key):
            return str(output[key])
    return json.dumps(output, ensure_ascii=False)


def _fallback_narrative(sensor: dict, permit: dict, equipment: dict) -> str:
    return (
        f"Sensor: {sensor.get('assessment', 'n/a')}. "
        f"Permit: {permit.get('conflict_description', 'n/a')}. "
        f"Equipment: {equipment.get('note', 'n/a')}."
    )
