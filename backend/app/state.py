"""Central application state and orchestration — DB-backed persistence."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Any

from app.config import settings
from app.db.repositories import OpsRepository, RiskRepository, ZoneRepository
from app.db.session import async_session_factory
from app.demo.scenario import get_scenario_at_offset, reload_seed, set_scenario
from app.models.schemas import (
    EmergencyStatus,
    HeatmapData,
    OutcomeRecord,
    ReplayState,
    RiskInstance,
    RiskStatus,
    TimelineEvent,
    ZoneState,
)
from app.platforms.digital_twin import DigitalTwin
from app.platforms.intelligence import build_evidence_package, enrich_risk_from_seed_templates, enrich_risk_with_agents
from app.platforms.ops_api import sync_zone_crs_from_risks
from app.platforms.risk_engine import MOTIFS, create_risk_instance, evaluate_zone, reload_motifs
from app.seed.loader import seed_data


class PrahariState:
    """Ephemeral orchestration (replay, websockets) + DB-backed persistence."""

    def __init__(self):
        self._init_from_seed()

    def _init_from_seed(self) -> None:
        scenario = seed_data.active_scenario
        plant = seed_data.plant
        self.twin = DigitalTwin(plant.get("plant_id"), plant.get("plant_name"))
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
        # In-memory caches kept in sync with DB for fast dashboard reads
        self.risk_instances: dict[str, RiskInstance] = {}
        self.evidence_packages: dict[str, Any] = {}
        self.emergency = EmergencyStatus(active=False, steps=[])
        self.audit_log: list[dict[str, Any]] = []
        self.outcomes: list[OutcomeRecord] = []
        self.notifications: list[dict[str, Any]] = []
        self._db_ready = False
        self._db_unavailable = False

    async def _ensure_db(self) -> bool:
        """Return True if Postgres is reachable; cache negative result for this process."""
        if self._db_unavailable:
            return False
        if self._db_ready:
            return True
        try:
            from sqlalchemy import text
            async with async_session_factory() as session:
                await session.execute(text("SELECT 1"))
            self._db_ready = True
            return True
        except Exception:
            self._db_unavailable = True
            return False

    def subscribe(self, queue: asyncio.Queue) -> None:
        self._subscribers.append(queue)

    async def broadcast(self, event: dict) -> None:
        for q in self._subscribers:
            try:
                await q.put(event)
            except Exception:
                pass

    def _audit(self, action: str, actor: str, details: dict | None = None) -> None:
        self.audit_log.append(
            {
                "ts": datetime.utcnow().isoformat(),
                "action": action,
                "actor": actor,
                "details": details or {},
            }
        )

    async def _emit_notification(self, notif: dict[str, Any]) -> None:
        self.notifications.insert(0, notif)
        self.notifications = self.notifications[:50]
        await self.broadcast({"type": "notification", "data": notif})

    @property
    def active_zone_id(self) -> str:
        return seed_data.active_scenario.zone_id

    def _plant_zone_ids(self) -> list[str]:
        return [z["zone_id"] for z in seed_data.plant.get("zones", [])]

    async def hydrate_from_db(self) -> None:
        """Load open risks / twin / emergency from Postgres into caches."""
        try:
            async with async_session_factory() as session:
                zone_repo = ZoneRepository(session)
                risk_repo = RiskRepository(session)
                ops_repo = OpsRepository(session)

                for zone_id in self._plant_zone_ids():
                    history = await zone_repo.get_ch4_history(zone_id, minutes=240)
                    self.twin.history[zone_id] = history
                    zs = await zone_repo.get_zone_state(zone_id)
                    if zs:
                        self.twin.zones[zone_id] = zs

                risks = await risk_repo.list_open_risks()
                self.risk_instances = {r.risk_id: r for r in risks}
                for r in risks:
                    if r.evidence_package_id:
                        ep = await risk_repo.get_evidence(r.evidence_package_id)
                        if ep:
                            self.evidence_packages[ep.evidence_id] = ep

                self.emergency = await ops_repo.get_emergency()
                self.audit_log = await ops_repo.list_audit(50)
                self._db_ready = True
        except Exception:
            self._db_unavailable = True
            raise

    async def _apply_scenario_event_local(self, event) -> RiskInstance | None:
        """In-memory demo path when Postgres is unavailable."""
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
            (
                r for r in self.risk_instances.values()
                if r.zone_id == zone_id and r.motif_id == motif.motif_id
                and r.status not in (RiskStatus.RESOLVED, RiskStatus.FALSE_POSITIVE)
            ),
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
            existing.timeline.append(
                TimelineEvent(ts=datetime.utcnow(), event="UPDATED", actor="P3", note=f"CRS {crs.score}")
            )
            risk = existing
        else:
            risk_id = f"RI-{uuid.uuid4().hex[:10].upper()}"
            risk = create_risk_instance(
                motif, crs, zone, signals, lead_time,
                settings.demo_org_id, settings.demo_plant_id, risk_id,
            )
            self.risk_instances[risk_id] = risk

        enrichment = enrich_risk_from_seed_templates(risk, zone)
        risk.narrative = enrichment.narrative
        evidence = build_evidence_package(risk, zone, enrichment)
        risk.evidence_package_id = evidence.evidence_id
        self.evidence_packages[evidence.evidence_id] = evidence
        sync_zone_crs_from_risks(self.twin.zones, self.risk_instances)
        return risk

    async def apply_scenario_event(self, event) -> RiskInstance | None:
        if not await self._ensure_db():
            return await self._apply_scenario_event_local(event)
        try:
            return await self._apply_scenario_event_db(event)
        except Exception as exc:
            print(f"[PRAHARI] DB scenario apply failed, in-memory fallback: {exc}")
            self._db_unavailable = True
            return await self._apply_scenario_event_local(event)

    async def _apply_scenario_event_db(self, event) -> RiskInstance | None:
        updates = event.updates
        zone_id = self.active_zone_id
        now = datetime.utcnow()

        if "maintenance_active" in updates:
            self._maintenance_active = updates["maintenance_active"]
        if "equipment_fault" in updates:
            self._equipment_fault = updates.get("equipment_fault", False)
        if "ppe_missing" in updates:
            self._ppe_missing = updates.get("ppe_missing", False)

        async with async_session_factory() as session:
            zone_repo = ZoneRepository(session)
            risk_repo = RiskRepository(session)

            # Persist sensor / permit / occupancy / maintenance to DB
            if "ch4_lel" in updates:
                ch4 = float(updates["ch4_lel"])
                history_points = [
                    (now - timedelta(minutes=100), max(0.5, ch4 - 6)),
                    (now - timedelta(minutes=75), max(1.0, ch4 - 4.5)),
                    (now - timedelta(minutes=50), max(1.5, ch4 - 3)),
                    (now - timedelta(minutes=25), max(2.0, ch4 - 1.5)),
                    (now, ch4),
                ]
                await zone_repo.write_ch4_history_points(zone_id, history_points)
                self.twin.history[zone_id] = history_points

            for key, sensor_type in (
                ("h2s_ppm", "H2S"),
                ("co_ppm", "CO"),
                ("o2_pct", "O2"),
                ("temperature_c", "TEMP"),
            ):
                if key in updates:
                    await zone_repo.write_sensor_reading(zone_id, sensor_type, float(updates[key]), ts=now)

            if "active_permits" in updates:
                for pid in updates["active_permits"]:
                    ptype = "HOTWORK" if "HOT" in pid.upper() else (
                        "CONFINED_ENTRY" if "CONFINED" in pid.upper() else "GENERAL"
                    )
                    await zone_repo.upsert_permit(pid, zone_id, ptype, "active", valid_from=now)
            if "scheduled_permits" in updates:
                for pid in updates["scheduled_permits"]:
                    ptype = "CONFINED_ENTRY" if "CONFINED" in pid.upper() else "GENERAL"
                    await zone_repo.upsert_permit(pid, zone_id, ptype, "scheduled", valid_from=now)

            if "occupancy" in updates:
                await zone_repo.set_occupancy(zone_id, int(updates["occupancy"]))

            if "maintenance_active" in updates or "equipment_fault" in updates:
                active = bool(updates.get("maintenance_active") or updates.get("equipment_fault"))
                await zone_repo.set_maintenance_flag(zone_id, active)

            # Mirror into in-memory twin for motif eval + API parity
            zone_updates = {k: v for k, v in updates.items() if k in ZoneState.model_fields}
            if zone_updates:
                self.twin.update_zone(zone_id, **zone_updates)

            if event.offset_minutes < 0:
                lead_override = abs(event.offset_minutes)
                self.twin.update_zone(zone_id, forecast_eta_minutes=float(lead_override))
            else:
                db_history = await zone_repo.get_ch4_history(zone_id, minutes=240)
                if db_history:
                    self.twin.history[zone_id] = db_history
                self.twin.refresh_forecasts()

            zone = self.twin.get_zone(zone_id)
            if not zone:
                await session.commit()
                return None

            maintenance = self._maintenance_active or await zone_repo.has_open_maintenance(zone_id)
            equipment_fault = self._equipment_fault or await zone_repo.has_equipment_fault(zone_id)

            detections = evaluate_zone(
                zone,
                maintenance_active=maintenance,
                equipment_fault=equipment_fault,
                ppe_missing=self._ppe_missing,
            )

            if not detections:
                await session.commit()
                return None

            motif, crs, signals, lead_time = detections[0]
            if event.offset_minutes < 0:
                lead_time = abs(event.offset_minutes) * 60

            existing = await risk_repo.get_open_risk(zone_id, motif.motif_id)
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
                existing.timeline.append(
                    TimelineEvent(ts=datetime.utcnow(), event="UPDATED", actor="P3", note=f"CRS {crs.score}")
                )
                risk = existing
                await risk_repo.update_risk_instance(risk)
            else:
                risk_id = f"RI-{uuid.uuid4().hex[:10].upper()}"
                risk = create_risk_instance(
                    motif, crs, zone,
                    signals, lead_time,
                    settings.demo_org_id, settings.demo_plant_id,
                    risk_id,
                )
                await risk_repo.create_risk_instance(risk)

            maintenance_records = await zone_repo.get_open_maintenance_records(zone_id)
            clauses = await zone_repo.get_regulation_clauses()
            enrichment, pipeline = await enrich_risk_with_agents(
                risk,
                zone,
                maintenance_records=maintenance_records,
                retrieved_clauses=clauses or None,
            )
            risk.narrative = enrichment.narrative
            risk.detection.llm_involved = bool(pipeline.get("llm_involved"))
            evidence = build_evidence_package(risk, zone, enrichment, pipeline)
            risk.evidence_package_id = evidence.evidence_id

            agent_meta = {}
            for entry in pipeline.get("findings_trace") or []:
                short = entry["agent"].replace("_agent", "")
                agent_meta[short] = entry
                agent_meta[entry["agent"]] = entry

            await risk_repo.save_evidence(evidence, agent_meta=agent_meta)
            await risk_repo.update_risk_instance(risk)

            await session.commit()

            self.risk_instances[risk.risk_id] = risk
            self.evidence_packages[evidence.evidence_id] = evidence
            sync_zone_crs_from_risks(self.twin.zones, self.risk_instances)
            return risk

    async def step_replay(self, offset: int) -> dict:
        self.replay.current_time_offset = offset
        event = get_scenario_at_offset(offset)
        risk = None
        if event:
            risk = await self.apply_scenario_event(event)

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
        await self.broadcast({"type": "replay_complete", "data": {"replay_offset": self.replay.current_time_offset}})

    def stop_replay(self) -> None:
        self.replay.running = False

    def get_dashboard_risks(self) -> list[RiskInstance]:
        risks = [r for r in self.risk_instances.values() if r.status not in (RiskStatus.RESOLVED, RiskStatus.FALSE_POSITIVE)]
        return sorted(risks, key=lambda r: (-r.crs.score, -(r.lead_time_seconds or 0)))

    def get_heatmap(self) -> HeatmapData:
        sync_zone_crs_from_risks(self.twin.zones, self.risk_instances)
        return HeatmapData(**self.twin.get_heatmap_data())

    async def triage_risk(
        self,
        risk_id: str,
        action: str,
        actor: str,
        note: str | None = None,
        justification: str | None = None,
    ) -> RiskInstance | None:
        risk = self.risk_instances.get(risk_id)
        if not risk:
            async with async_session_factory() as session:
                risk_repo = RiskRepository(session)
                risk = await risk_repo.get_risk(risk_id)
                if not risk:
                    return None

        status_map = {
            "acknowledge": RiskStatus.ACKNOWLEDGED,
            "escalate": RiskStatus.ESCALATED,
            "dismiss": RiskStatus.FALSE_POSITIVE,
            "resolve": RiskStatus.RESOLVED,
        }
        risk.status = status_map.get(action, risk.status)
        risk.timeline.append(
            TimelineEvent(ts=datetime.utcnow(), event=action.upper(), actor=actor, note=note or justification)
        )
        risk.updated_at = datetime.utcnow()

        async with async_session_factory() as session:
            risk_repo = RiskRepository(session)
            ops_repo = OpsRepository(session)
            await risk_repo.update_risk_instance(risk)
            await ops_repo.write_audit(
                f"risk_{action}",
                actor,
                "risk",
                risk_id,
                justification=justification,
                details={"note": note},
            )
            await session.commit()
            self.audit_log = await ops_repo.list_audit(50)

        self.risk_instances[risk_id] = risk

        if action == "acknowledge":
            await self._emit_notification({
                "id": f"notif-ack-{risk_id}-{int(datetime.utcnow().timestamp())}",
                "type": "ACKNOWLEDGEMENT",
                "priority": risk.crs.band.value,
                "title": f"Risk acknowledged — {risk.zone_id} · {risk.motif_id}",
                "body": note or f"{actor} acknowledged CRS {risk.crs.score:.0f} in {risk.zone_id}",
                "zone_id": risk.zone_id,
                "risk_id": risk.risk_id,
                "acknowledged": False,
                "status": "ACKNOWLEDGED",
                "ts": datetime.utcnow().isoformat(),
                "actor": actor,
                "routes_to": ["supervisor", "permit_officer", "compliance_officer", "executive", "safety_officer"],
            })

        return risk

    async def declare_emergency(self, zone_id: str, risk_id: str | None, actor: str) -> EmergencyStatus:
        async with async_session_factory() as session:
            ops_repo = OpsRepository(session)
            emergency = await ops_repo.declare_emergency(zone_id, risk_id, actor)
            await session.commit()
            self.audit_log = await ops_repo.list_audit(50)
        self.emergency = emergency
        if risk_id and risk_id in self.risk_instances:
            self.risk_instances[risk_id].timeline.append(
                TimelineEvent(ts=datetime.utcnow(), event="EMERGENCY", actor=actor, note="Evidence chain locked")
            )
        return emergency

    def override_permit(self, permit_id: str, justification: str, actor: str) -> dict:
        self._audit("permit_override", actor, {"permit_id": permit_id, "justification": justification})
        return {"permit_id": permit_id, "status": "OVERRIDDEN", "justification": justification, "audited": True}

    async def record_outcome(self, outcome: OutcomeRecord) -> None:
        self.outcomes.append(outcome)
        async with async_session_factory() as session:
            ops_repo = OpsRepository(session)
            await ops_repo.record_outcome(
                outcome.risk_id,
                outcome.classification,
                outcome.recommendation_rating,
                outcome.root_cause_rating,
                outcome.notes,
            )
            await session.commit()
            self.audit_log = await ops_repo.list_audit(50)

    async def reset_demo(self) -> None:
        self.stop_replay()
        if await self._ensure_db():
            try:
                async with async_session_factory() as session:
                    zone_repo = ZoneRepository(session)
                    risk_repo = RiskRepository(session)
                    await risk_repo.clear_risks_and_evidence()
                    for zone_id in self._plant_zone_ids():
                        await zone_repo.clear_zone_runtime(zone_id)
                    await session.commit()
            except Exception as exc:
                print(f"[PRAHARI] DB reset skipped, in-memory only: {exc}")
                self._db_unavailable = True
        self._init_from_seed()

    async def load_scenario(self, scenario_id: str | None = None) -> dict:
        if scenario_id:
            set_scenario(scenario_id)
        await self.reset_demo()
        scenario = seed_data.active_scenario
        offset = scenario.load_at_offset_minutes
        event = get_scenario_at_offset(offset)
        risk = await self.apply_scenario_event(event) if event else None
        zone = self.twin.get_zone(self.active_zone_id)
        return {
            "scenario_id": scenario.id,
            "scenario_name": scenario.name,
            "offset": offset,
            "risk": risk.model_dump(mode="json") if risk else None,
            "zone": zone.model_dump(mode="json") if zone else None,
        }

    def reload_seed_data(self) -> dict:
        reload_seed()
        reload_motifs()
        self._init_from_seed()
        return {
            "status": "reloaded",
            "active_scenario": seed_data.active_scenario.id,
            "scenarios": seed_data.list_scenarios(),
        }


state = PrahariState()
