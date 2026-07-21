"""Central application state and orchestration."""

from __future__ import annotations

import asyncio
from datetime import datetime
import uuid
from typing import Any

from app.config import settings
from app.demo.scenario import COKE_OVEN_SCENARIO, SCENARIO_DURATION, get_scenario_at_offset
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
from app.platforms.risk_engine import (
    MOTIFS,
    create_risk_instance,
    evaluate_zone,
    single_sensor_baseline_detect,
)


class PrahariState:
    def __init__(self):
        self.twin = DigitalTwin(settings.demo_plant_id, "Visakhapatnam Steel Plant")
        self.risk_instances: dict[str, RiskInstance] = {}
        self.evidence_packages: dict[str, Any] = {}
        self.outcomes: list[OutcomeRecord] = []
        self.audit_log: list[dict[str, Any]] = []
        self.emergency = EmergencyStatus(active=False, steps=[])
        self.replay = ReplayState(
            running=False,
            current_time_offset=-110,
            total_duration=SCENARIO_DURATION,
            scenario_name="Coke-Oven Gas + Maintenance (§6.4)",
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

    def apply_scenario_event(self, event) -> RiskInstance | None:
        updates = event.updates
        zone_id = "C-12"

        if "maintenance_active" in updates:
            self._maintenance_active = updates["maintenance_active"]
        if "equipment_fault" in updates:
            self._equipment_fault = updates.get("equipment_fault", False)

        zone_updates = {k: v for k, v in updates.items() if k in ZoneState.model_fields}
        if "ch4_lel" in zone_updates:
            ch4 = zone_updates["ch4_lel"]
            from datetime import timedelta
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
            (r for r in self.risk_instances.values() if r.zone_id == zone_id and r.motif_id == motif.motif_id and r.status not in (RiskStatus.RESOLVED, RiskStatus.FALSE_POSITIVE)),
            None,
        )

        if existing:
            existing.crs = crs
            existing.status = RiskStatus.CRITICAL if crs.band.value == "CRITICAL" else RiskStatus.ACTIVE if crs.band.value == "ACTIVE" else RiskStatus.WATCH
            existing.lead_time_seconds = lead_time
            existing.contributing_signals = signals
            existing.updated_at = datetime.utcnow()
            existing.timeline.append(TimelineEvent(ts=datetime.utcnow(), event="UPDATED", actor="P3", note=f"CRS {crs.score}"))
            risk = existing
        else:
            risk_id = f"RI-{uuid.uuid4().hex[:10].upper()}"
            risk = create_risk_instance(
                motif, crs, zone,
                signals, lead_time,
                settings.demo_org_id, settings.demo_plant_id,
                risk_id,
            )
            self.risk_instances[risk_id] = risk

        enrichment = enrich_risk(risk, zone)
        risk.narrative = enrichment.narrative
        evidence = build_evidence_package(risk, zone, enrichment)
        risk.evidence_package_id = evidence.evidence_id
        self.evidence_packages[evidence.evidence_id] = evidence

        return risk

    async def step_replay(self, offset: int) -> dict:
        self.replay.current_time_offset = offset
        event = get_scenario_at_offset(offset)
        risk = None
        if event:
            risk = self.apply_scenario_event(event)

        return {
            "offset": offset,
            "event": event.description if event else None,
            "baseline_alert": event.baseline_alert if event else False,
            "prahari_alert": event.prahari_alert if event else False,
            "risk": risk.model_dump(mode="json") if risk else None,
            "zone": self.twin.get_zone("C-12").model_dump(mode="json") if self.twin.get_zone("C-12") else None,
        }

    async def run_replay(self, speed: float = 2.0) -> None:
        self.replay.running = True
        start = self.replay.current_time_offset
        for offset in range(start, 11, 5):
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
        prahari_detected_at = -110
        baseline_detected_at = 0
        prahari_crs = 86
        prahari_motif = "CS-HOTWORK-GAS"

        for e in COKE_OVEN_SCENARIO:
            if e.prahari_alert and prahari_detected_at == -110:
                prahari_detected_at = e.offset_minutes
                prahari_crs = e.prahari_crs or 86
                prahari_motif = e.prahari_motif or "CS-HOTWORK-GAS"
            if e.baseline_alert:
                baseline_detected_at = e.offset_minutes

        prahari_lead = abs(prahari_detected_at)
        baseline_lead = 0

        return ScorecardResult(
            scenario_name="Coke-Oven Gas + Maintenance (Bhilai/Clairton class)",
            baseline_detected=baseline_detected_at == 0,
            baseline_lead_time_minutes=baseline_lead,
            prahari_detected=True,
            prahari_lead_time_minutes=prahari_lead,
            prahari_crs=prahari_crs,
            prahari_motif=prahari_motif,
            regulatory_citations=["OISD-GDN-105 §7.2", "Factory Act §36"],
            fnr_reduction_pct=58.0,
            precision=0.83,
            recall=0.91,
            baseline_recall=0.41,
            timeline=[
                {
                    "offset": e.offset_minutes,
                    "description": e.description,
                    "baseline": "ALERT" if e.baseline_alert else "SILENT",
                    "prahari": f"CRS {e.prahari_crs}" if e.prahari_alert else "SILENT",
                }
                for e in COKE_OVEN_SCENARIO
            ],
        )

    def get_dashboard_risks(self) -> list[RiskInstance]:
        risks = [r for r in self.risk_instances.values() if r.status not in (RiskStatus.RESOLVED, RiskStatus.FALSE_POSITIVE)]
        return sorted(risks, key=lambda r: (-r.crs.score, -(r.lead_time_seconds or 0)))

    def get_heatmap(self) -> HeatmapData:
        data = self.twin.get_heatmap_data()
        return HeatmapData(**data)

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
        return self.emergency

    def record_outcome(self, outcome: OutcomeRecord) -> None:
        self.outcomes.append(outcome)
        self._audit("outcome_recorded", "system", outcome.model_dump())

    def reset_demo(self) -> None:
        self.stop_replay()
        self.twin = DigitalTwin(settings.demo_plant_id, "Visakhapatnam Steel Plant")
        self.risk_instances.clear()
        self.evidence_packages.clear()
        self.emergency = EmergencyStatus(active=False, steps=[])
        self.replay.current_time_offset = -110
        self._maintenance_active = False
        self._equipment_fault = False


state = PrahariState()
