"""Central application state and orchestration."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import uuid
from typing import Any

from app.config import settings
from app.demo.scenario import get_scenario_at_offset, reload_seed, set_scenario
from app.models.schemas import (
    EmergencyStatus,
    HeatmapData,
    OutcomeRecord,
    ReplayState,
    RiskInstance,
    RiskStatus,
    ScorecardResult,
    TimelineEvent,
    ZoneState,
)
from app.platforms.digital_twin import DigitalTwin
from app.platforms.intelligence import build_evidence_package, enrich_risk
from app.platforms.ops_api import sync_zone_crs_from_risks
from app.platforms.risk_engine import MOTIFS, create_risk_instance, evaluate_zone
from app.seed.loader import seed_data


class PrahariState:
    def __init__(self):
        self._init_from_seed()

    def _init_from_seed(self) -> None:
        scenario = seed_data.active_scenario
        plant = seed_data.plant
        self.twin = DigitalTwin(plant.get("plant_id"), plant.get("plant_name"))
        self.risk_instances: dict[str, RiskInstance] = {}
        self.evidence_packages: dict[str, Any] = {}
        self.outcomes: list[OutcomeRecord] = []
        self.audit_log: list[dict[str, Any]] = []
        self.emergency = EmergencyStatus(active=False, steps=[])
        self.replay = ReplayState(
            running=False,
            current_time_offset=scenario.events[0].offset_minutes if scenario.events else -110,
            total_duration=scenario.duration_minutes,
            scenario_name=scenario.name,
        )
        self._replay_task: asyncio.Task | None = None
        self._subscribers: list[Any] = []
        self._maintenance_active = False
        self._equipment_fault = False
        self._ppe_missing = False

    def subscribe(self, queue: asyncio.Queue) -> None:
        self._subscribers.append(queue)

    async def broadcast(self, event: dict) -> None:
        for q in self._subscribers:
            try:
                await q.put(event)
            except Exception:
                pass

    def _audit(self, action: str, actor: str, details: dict) -> None:
        self.audit_log.append({
            "ts": datetime.utcnow().isoformat(),
            "action": action,
            "actor": actor,
            "details": details,
        })

    @property
    def active_zone_id(self) -> str:
        return seed_data.active_scenario.zone_id

    def apply_scenario_event(self, event) -> RiskInstance | None:
        updates = event.updates
        zone_id = self.active_zone_id

        if "maintenance_active" in updates:
            self._maintenance_active = updates["maintenance_active"]
        if "equipment_fault" in updates:
            self._equipment_fault = updates.get("equipment_fault", False)
        if "ppe_missing" in updates:
            self._ppe_missing = updates.get("ppe_missing", False)

        zone_updates = {k: v for k, v in updates.items() if k in ZoneState.model_fields}
        if "ch4_lel" in zone_updates:
            ch4 = zone_updates["ch4_lel"]
            now = datetime.utcnow()
            self.twin.history[zone_id] = [
                (now - timedelta(minutes=100), max(0.5, ch4 - 6)),
                (now - timedelta(minutes=75), max(1.0, ch4 - 4.5)),
                (now - timedelta(minutes=50), max(1.5, ch4 - 3)),
                (now - timedelta(minutes=25), max(2.0, ch4 - 1.5)),
                (now, ch4),
            ]

        if zone_updates:
            self.twin.update_zone(zone_id, **zone_updates)

        if event.offset_minutes < 0:
            lead_override = abs(event.offset_minutes)
            self.twin.update_zone(zone_id, forecast_eta_minutes=float(lead_override))
        else:
            self.twin.refresh_forecasts()

        zone = self.twin.get_zone(zone_id)
        if not zone:
            return None

        detections = evaluate_zone(
            zone,
            maintenance_active=self._maintenance_active,
            equipment_fault=self._equipment_fault,
            ppe_missing=self._ppe_missing,
        )

        if not detections:
            return None

        motif, crs, signals, lead_time = detections[0]
        if event.offset_minutes < 0:
            lead_time = abs(event.offset_minutes) * 60

        existing = next(
            (r for r in self.risk_instances.values()
             if r.zone_id == zone_id and r.motif_id == motif.motif_id
             and r.status not in (RiskStatus.RESOLVED, RiskStatus.FALSE_POSITIVE)),
            None,
        )

        if existing:
            existing.crs = crs
            existing.status = (
                RiskStatus.CRITICAL if crs.band.value == "CRITICAL"
                else RiskStatus.ACTIVE if crs.band.value == "ACTIVE"
                else RiskStatus.WATCH
            )
            existing.lead_time_seconds = lead_time
            existing.contributing_signals = signals
            existing.updated_at = datetime.utcnow()
            existing.timeline.append(TimelineEvent(ts=datetime.utcnow(), event="UPDATED", actor="P3", note=f"CRS {crs.score}"))
            risk = existing
        else:
            risk_id = f"RI-{uuid.uuid4().hex[:10].upper()}"
            risk = create_risk_instance(
                motif, crs, zone, signals, lead_time,
                settings.demo_org_id, settings.demo_plant_id, risk_id,
            )
            self.risk_instances[risk_id] = risk

        enrichment = enrich_risk(risk, zone)
        risk.narrative = enrichment.narrative
        evidence = build_evidence_package(risk, zone, enrichment)
        risk.evidence_package_id = evidence.evidence_id
        self.evidence_packages[evidence.evidence_id] = evidence
        sync_zone_crs_from_risks(self.twin.zones, self.risk_instances)

        return risk

    async def step_replay(self, offset: int) -> dict:
        self.replay.current_time_offset = offset
        event = get_scenario_at_offset(offset)
        risk = None
        if event:
            risk = self.apply_scenario_event(event)

        zone = self.twin.get_zone(self.active_zone_id)
        return {
            "offset": offset,
            "event": event.description if event else None,
            "baseline_alert": event.baseline_alert if event else False,
            "prahari_alert": event.prahari_alert if event else False,
            "risk": risk.model_dump(mode="json") if risk else None,
            "zone": zone.model_dump(mode="json") if zone else None,
        }

    async def run_replay(self, speed: float = 2.0) -> None:
        self.replay.running = True
        scenario = seed_data.active_scenario
        start = self.replay.current_time_offset
        end = max(e.offset_minutes for e in scenario.events) + 5 if scenario.events else 10
        for offset in range(start, end + 1, 5):
            if not self.replay.running:
                break
            result = await self.step_replay(offset)
            await self.broadcast({"type": "replay_step", "data": result})
            await asyncio.sleep(speed)
        self.replay.running = False
        await self.broadcast({"type": "replay_complete", "data": {"scorecard": self.get_scorecard().model_dump(mode="json")}})

    def stop_replay(self) -> None:
        self.replay.running = False

    def get_scorecard(self) -> ScorecardResult:
        scenario = seed_data.active_scenario
        sc = scenario.scorecard
        prahari_detected_at = None
        baseline_detected_at = None
        prahari_crs = 86.0
        prahari_motif = "CS-HOTWORK-GAS"

        for e in scenario.events:
            if e.prahari_alert and prahari_detected_at is None:
                prahari_detected_at = e.offset_minutes
                prahari_crs = e.prahari_crs or 86
                prahari_motif = e.prahari_motif or prahari_motif
            if e.baseline_alert:
                baseline_detected_at = e.offset_minutes

        prahari_lead = abs(prahari_detected_at) if prahari_detected_at is not None else 0

        return ScorecardResult(
            scenario_name=scenario.name,
            baseline_detected=baseline_detected_at is not None,
            baseline_lead_time_minutes=0,
            prahari_detected=True,
            prahari_lead_time_minutes=prahari_lead,
            prahari_crs=prahari_crs,
            prahari_motif=prahari_motif,
            regulatory_citations=sc.get("regulatory_citations", []),
            fnr_reduction_pct=sc.get("fnr_reduction_pct", 58.0),
            precision=sc.get("precision", 0.83),
            recall=sc.get("recall", 0.91),
            baseline_recall=sc.get("baseline_recall", 0.41),
            timeline=[
                {
                    "offset": e.offset_minutes,
                    "description": e.description,
                    "baseline": "ALERT" if e.baseline_alert else "SILENT",
                    "prahari": f"CRS {e.prahari_crs}" if e.prahari_alert else "SILENT",
                }
                for e in scenario.events
            ],
        )

    def get_dashboard_risks(self) -> list[RiskInstance]:
        risks = [r for r in self.risk_instances.values() if r.status not in (RiskStatus.RESOLVED, RiskStatus.FALSE_POSITIVE)]
        return sorted(risks, key=lambda r: (-r.crs.score, -(r.lead_time_seconds or 0)))

    def get_heatmap(self) -> HeatmapData:
        sync_zone_crs_from_risks(self.twin.zones, self.risk_instances)
        return HeatmapData(**self.twin.get_heatmap_data())

    def triage_risk(self, risk_id: str, action: str, actor: str, note: str | None = None, justification: str | None = None) -> RiskInstance | None:
        risk = self.risk_instances.get(risk_id)
        if not risk:
            return None

        status_map = {
            "acknowledge": RiskStatus.ACKNOWLEDGED,
            "escalate": RiskStatus.ESCALATED,
            "dismiss": RiskStatus.FALSE_POSITIVE,
            "resolve": RiskStatus.RESOLVED,
        }
        risk.status = status_map.get(action, risk.status)
        risk.timeline.append(TimelineEvent(ts=datetime.utcnow(), event=action.upper(), actor=actor, note=note or justification))
        risk.updated_at = datetime.utcnow()
        self._audit(f"risk_{action}", actor, {"risk_id": risk_id, "note": note, "justification": justification})
        return risk

    def declare_emergency(self, zone_id: str, risk_id: str | None, actor: str) -> EmergencyStatus:
        now = datetime.utcnow()
        self.emergency = EmergencyStatus(
            active=True,
            zone_id=zone_id,
            risk_id=risk_id,
            declared_at=now,
            steps=[
                {"step": "Emergency confirmed", "status": "complete", "ts": now.isoformat()},
                {"step": "Evacuation initiated", "status": "complete", "ts": now.isoformat()},
                {"step": "3 workers notified (2 ack, 1 pending)", "status": "in_progress", "ts": now.isoformat()},
                {"step": "Response team paged", "status": "complete", "ts": now.isoformat()},
                {"step": "Evidence locked", "status": "complete", "ts": now.isoformat()},
                {"step": "Draft incident report generating", "status": "in_progress", "ts": now.isoformat()},
            ],
        )
        self._audit("emergency_declare", actor, {"zone_id": zone_id, "risk_id": risk_id})
        if risk_id and risk_id in self.risk_instances:
            self.risk_instances[risk_id].timeline.append(
                TimelineEvent(ts=now, event="EMERGENCY", actor=actor, note="Evidence chain locked")
            )
        return self.emergency

    def override_permit(self, permit_id: str, justification: str, actor: str) -> dict:
        self._audit("permit_override", actor, {"permit_id": permit_id, "justification": justification})
        return {"permit_id": permit_id, "status": "OVERRIDDEN", "justification": justification, "audited": True}

    def record_outcome(self, outcome: OutcomeRecord) -> None:
        self.outcomes.append(outcome)
        self._audit("outcome_recorded", "system", outcome.model_dump())

    def reset_demo(self) -> None:
        self.stop_replay()
        self._init_from_seed()

    def load_scenario(self, scenario_id: str | None = None) -> dict:
        if scenario_id:
            set_scenario(scenario_id)
        self.reset_demo()
        scenario = seed_data.active_scenario
        offset = scenario.load_at_offset_minutes
        event = get_scenario_at_offset(offset)
        risk = self.apply_scenario_event(event) if event else None
        zone = self.twin.get_zone(self.active_zone_id)
        return {
            "scenario_id": scenario.id,
            "scenario_name": scenario.name,
            "offset": offset,
            "risk": risk.model_dump(mode="json") if risk else None,
            "zone": zone.model_dump(mode="json") if zone else None,
        }

    def reload_seed_data(self) -> dict:
        from app.platforms.risk_engine import reload_motifs
        reload_seed()
        reload_motifs()
        self.reset_demo()
        return {
            "status": "reloaded",
            "active_scenario": seed_data.active_scenario.id,
            "scenarios": seed_data.list_scenarios(),
        }


state = PrahariState()
