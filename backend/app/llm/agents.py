"""P4 agent prompts and callables — LLM narrates only; never sets CRS."""

from __future__ import annotations

from typing import Any

from app.llm.client import Completer

SENSOR_AGENT_SYSTEM = """You are a Sensor Interpretation Agent for an industrial safety system.
You receive raw sensor readings and a trend. Output ONLY facts derivable from the data —
no speculation about cause. Be concise, plant-operator register, not academic."""

PERMIT_AGENT_SYSTEM = """You are a Permit Conflict Agent. Given active/scheduled permits and
zone conditions, identify any dangerous simultaneous operations (e.g. hot work near rising
gas, confined entry without isolation). If no conflict exists, say so plainly — do not invent one."""

EQUIPMENT_AGENT_SYSTEM = """You are an Equipment Risk Agent. Given maintenance records and
equipment health data, assess whether open work orders or flagged equipment plausibly relate
to the current risk. Cite the work order ID if relevant. If records are empty, say so."""

COMPLIANCE_AGENT_SYSTEM = """You are a Regulatory Compliance Agent. Given retrieved regulation
clauses, identify which apply to the current risk instance and state the citation exactly as
provided — never fabricate a clause you were not given. If the retrieved list is empty,
set citation_text to exactly "no clause retrieved" and applicable_clauses to []."""

PLANNER_AGENT_SYSTEM = """You are the Planner Agent. You receive findings from four upstream
agents (Sensor, Permit, Equipment, Compliance). Synthesize ONE coherent situational narrative
(3-4 sentences, plant-operator register) plus a ranked list of recommended actions, each with
a brief justification. Do not repeat all four findings verbatim — synthesize.
You do NOT decide risk scores — only explain and recommend."""


def run_sensor_agent(llm: Completer, zone_state: dict) -> dict[str, Any]:
    return llm.complete_json(
        system=SENSOR_AGENT_SYSTEM,
        user=f"Zone state: {zone_state}",
        schema_hint='{"assessment": str, "trend_direction": str, "confidence": float}',
    )


def run_permit_agent(llm: Completer, permits: list, zone_state: dict) -> dict[str, Any]:
    return llm.complete_json(
        system=PERMIT_AGENT_SYSTEM,
        user=f"Active/scheduled permits: {permits}\nZone conditions: {zone_state}",
        schema_hint='{"conflict_found": bool, "conflict_description": str, "permits_involved": list}',
    )


def run_equipment_agent(llm: Completer, maintenance_records: list) -> dict[str, Any]:
    return llm.complete_json(
        system=EQUIPMENT_AGENT_SYSTEM,
        user=f"Maintenance records: {maintenance_records}",
        schema_hint='{"relevant": bool, "note": str, "work_order_ref": str}',
    )


def run_compliance_agent(
    llm: Completer, retrieved_clauses: list, risk_summary: str
) -> dict[str, Any]:
    return llm.complete_json(
        system=COMPLIANCE_AGENT_SYSTEM,
        user=f"Risk: {risk_summary}\nRetrieved clauses: {retrieved_clauses}",
        schema_hint='{"applicable_clauses": list, "citation_text": str}',
    )


def run_planner_agent(
    llm: Completer,
    sensor: dict,
    permit: dict,
    equipment: dict,
    compliance: dict,
) -> dict[str, Any]:
    return llm.complete_json(
        system=PLANNER_AGENT_SYSTEM,
        user=(
            f"Sensor: {sensor}\nPermit: {permit}\n"
            f"Equipment: {equipment}\nCompliance: {compliance}"
        ),
        schema_hint=(
            '{"narrative": str, "recommendations": [{"action": str, "justification": str}], '
            '"confidence": float}'
        ),
    )
