"""Repository layer — all persistence goes through here, not PrahariState dicts."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import delete, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import models as m
from app.models.schemas import (
    CRS,
    CRSBand,
    CRSComponents,
    ContributingSignal,
    DetectionInfo,
    EmergencyStatus,
    EvidencePackage,
    HistoricalReference,
    Recommendation,
    RegulatoryCitation,
    RiskInstance,
    RiskStatus,
    RootCauseHypothesis,
    TimelineEvent,
    ZoneState,
)
from app.platforms.risk_engine import MOTIFS, crs_band


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


SENSOR_TYPE_TO_ZONE_FIELD = {
    "CH4": "ch4_lel",
    "H2S": "h2s_ppm",
    "CO": "co_ppm",
    "O2": "o2_pct",
    "TEMP": "temperature_c",
}


class ZoneRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_zone_row(self, zone_id: str) -> m.Zone | None:
        return await self.session.get(m.Zone, zone_id)

    async def list_zones(self, plant_id: str) -> list[m.Zone]:
        result = await self.session.execute(select(m.Zone).where(m.Zone.plant_id == plant_id))
        return list(result.scalars().all())

    async def get_latest_sensor_values(self, zone_id: str) -> dict[str, float]:
        sensors = (
            await self.session.execute(select(m.Sensor).where(m.Sensor.zone_id == zone_id))
        ).scalars().all()
        values: dict[str, float] = {}
        for sensor in sensors:
            row = (
                await self.session.execute(
                    select(m.SensorReading)
                    .where(m.SensorReading.sensor_id == sensor.id)
                    .order_by(m.SensorReading.ts.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()
            if row is not None:
                field = SENSOR_TYPE_TO_ZONE_FIELD.get(sensor.sensor_type)
                if field:
                    values[field] = row.value
        return values

    async def get_ch4_history(
        self, zone_id: str, minutes: int = 120
    ) -> list[tuple[datetime, float]]:
        sensor = (
            await self.session.execute(
                select(m.Sensor).where(
                    m.Sensor.zone_id == zone_id,
                    m.Sensor.sensor_type == "CH4",
                )
            )
        ).scalar_one_or_none()
        if not sensor:
            return []

        since = _utcnow() - timedelta(minutes=minutes)
        rows = (
            await self.session.execute(
                select(m.SensorReading)
                .where(
                    m.SensorReading.sensor_id == sensor.id,
                    m.SensorReading.ts >= since,
                )
                .order_by(m.SensorReading.ts.asc())
            )
        ).scalars().all()
        return [(r.ts.replace(tzinfo=None) if r.ts.tzinfo else r.ts, r.value) for r in rows]

    async def get_active_permits(self, zone_id: str) -> list[str]:
        rows = (
            await self.session.execute(
                select(m.Permit).where(
                    m.Permit.zone_id == zone_id,
                    m.Permit.status == "active",
                )
            )
        ).scalars().all()
        return [p.id for p in rows]

    async def get_scheduled_permits(self, zone_id: str) -> list[str]:
        rows = (
            await self.session.execute(
                select(m.Permit).where(
                    m.Permit.zone_id == zone_id,
                    m.Permit.status == "scheduled",
                )
            )
        ).scalars().all()
        return [p.id for p in rows]

    async def get_occupancy(self, zone_id: str) -> int:
        rows = (
            await self.session.execute(
                select(m.WorkerZoneLog).where(
                    m.WorkerZoneLog.zone_id == zone_id,
                    m.WorkerZoneLog.exited_at.is_(None),
                )
            )
        ).scalars().all()
        return len(rows)

    async def has_open_maintenance(self, zone_id: str) -> bool:
        equip = (
            await self.session.execute(select(m.Equipment).where(m.Equipment.zone_id == zone_id))
        ).scalars().all()
        if not equip:
            return False
        ids = [e.id for e in equip]
        row = (
            await self.session.execute(
                select(m.MaintenanceRecord)
                .where(
                    m.MaintenanceRecord.equipment_id.in_(ids),
                    m.MaintenanceRecord.status.in_(["open", "in_progress"]),
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        return row is not None

    async def has_equipment_fault(self, zone_id: str) -> bool:
        return await self.has_open_maintenance(zone_id)

    async def get_open_maintenance_records(self, zone_id: str) -> list[dict]:
        equip = (
            await self.session.execute(select(m.Equipment).where(m.Equipment.zone_id == zone_id))
        ).scalars().all()
        if not equip:
            return []
        ids = [e.id for e in equip]
        rows = (
            await self.session.execute(
                select(m.MaintenanceRecord).where(
                    m.MaintenanceRecord.equipment_id.in_(ids),
                    m.MaintenanceRecord.status.in_(["open", "in_progress"]),
                )
            )
        ).scalars().all()
        return [
            {
                "equipment_id": r.equipment_id,
                "work_order_ref": r.work_order_ref,
                "status": r.status,
                "note": r.note,
                "opened_at": r.opened_at.isoformat() if r.opened_at else None,
            }
            for r in rows
        ]

    async def get_regulation_clauses(self, limit: int = 10) -> list[dict]:
        rows = (
            await self.session.execute(select(m.Regulation).limit(limit))
        ).scalars().all()
        return [
            {"id": r.id, "framework": r.source, "ref": r.id, "text": r.clause_text}
            for r in rows
        ]

    async def get_zone_state(self, zone_id: str, forecast_eta_minutes: float | None = None) -> ZoneState | None:
        zone = await self.get_zone_row(zone_id)
        if not zone:
            return None

        sensors = await self.get_latest_sensor_values(zone_id)
        active = await self.get_active_permits(zone_id)
        scheduled = await self.get_scheduled_permits(zone_id)
        occupancy = await self.get_occupancy(zone_id)

        geo = zone.geo_bounds or {}
        return ZoneState(
            zone_id=zone.id,
            name=zone.name,
            zone_class=zone.hazard_class or "PROCESS",
            ch4_lel=sensors.get("ch4_lel", 0.0),
            h2s_ppm=sensors.get("h2s_ppm", 0.0),
            co_ppm=sensors.get("co_ppm", 0.0),
            o2_pct=sensors.get("o2_pct", 20.9),
            temperature_c=sensors.get("temperature_c", 25.0),
            occupancy=occupancy,
            active_permits=active,
            scheduled_permits=scheduled,
            forecast_eta_minutes=forecast_eta_minutes,
            data_quality="GOOD",
            geo=geo,
        )

    async def write_sensor_reading(
        self, zone_id: str, sensor_type: str, value: float, ts: datetime | None = None
    ) -> None:
        sensor = (
            await self.session.execute(
                select(m.Sensor).where(
                    m.Sensor.zone_id == zone_id,
                    m.Sensor.sensor_type == sensor_type,
                )
            )
        ).scalar_one_or_none()
        if not sensor:
            return
        reading_ts = ts or _utcnow()
        # Upsert-ish: delete exact ts collision then insert
        await self.session.execute(
            delete(m.SensorReading).where(
                m.SensorReading.sensor_id == sensor.id,
                m.SensorReading.ts == reading_ts,
            )
        )
        self.session.add(
            m.SensorReading(sensor_id=sensor.id, ts=reading_ts, value=value)
        )

    async def write_ch4_history_points(
        self, zone_id: str, points: list[tuple[datetime, float]]
    ) -> None:
        for ts, value in points:
            await self.write_sensor_reading(zone_id, "CH4", value, ts=ts)

    async def upsert_permit(
        self,
        permit_id: str,
        zone_id: str,
        permit_type: str,
        status: str,
        valid_from: datetime | None = None,
    ) -> None:
        existing = await self.session.get(m.Permit, permit_id)
        if existing:
            existing.status = status
            existing.zone_id = zone_id
            existing.permit_type = permit_type
        else:
            self.session.add(
                m.Permit(
                    id=permit_id,
                    zone_id=zone_id,
                    permit_type=permit_type,
                    status=status,
                    valid_from=valid_from or _utcnow(),
                )
            )

    async def set_occupancy(self, zone_id: str, count: int) -> None:
        # Close current occupancy
        current = (
            await self.session.execute(
                select(m.WorkerZoneLog).where(
                    m.WorkerZoneLog.zone_id == zone_id,
                    m.WorkerZoneLog.exited_at.is_(None),
                )
            )
        ).scalars().all()
        now = _utcnow()
        for row in current:
            row.exited_at = now

        if count <= 0:
            return

        # Ensure we have enough worker rows
        workers = (await self.session.execute(select(m.Worker).limit(count))).scalars().all()
        while len(workers) < count:
            w = m.Worker(name=f"Worker {len(workers) + 1}", certifications=["confined_space"])
            self.session.add(w)
            await self.session.flush()
            workers = list(workers) + [w]

        for i in range(count):
            self.session.add(
                m.WorkerZoneLog(worker_id=workers[i].id, zone_id=zone_id, entered_at=now)
            )

    async def set_maintenance_flag(self, zone_id: str, active: bool, equipment_id: str = "E-441") -> None:
        equip = await self.session.get(m.Equipment, equipment_id)
        if not equip:
            self.session.add(
                m.Equipment(id=equipment_id, zone_id=zone_id, equipment_type="valve", health_score=0.4)
            )
            await self.session.flush()

        open_rows = (
            await self.session.execute(
                select(m.MaintenanceRecord).where(
                    m.MaintenanceRecord.equipment_id == equipment_id,
                    m.MaintenanceRecord.status.in_(["open", "in_progress"]),
                )
            )
        ).scalars().all()

        if active and not open_rows:
            self.session.add(
                m.MaintenanceRecord(
                    equipment_id=equipment_id,
                    work_order_ref="WO-8841",
                    status="open",
                    note="possible seepage source",
                )
            )
        elif not active:
            for row in open_rows:
                row.status = "closed"
                row.closed_at = _utcnow()

    async def clear_zone_runtime(self, zone_id: str) -> None:
        """Clear demo runtime data for a zone (readings, permits, occupancy)."""
        sensors = (
            await self.session.execute(select(m.Sensor).where(m.Sensor.zone_id == zone_id))
        ).scalars().all()
        sensor_ids = [s.id for s in sensors]
        if sensor_ids:
            await self.session.execute(
                delete(m.SensorReading).where(m.SensorReading.sensor_id.in_(sensor_ids))
            )
        await self.session.execute(delete(m.Permit).where(m.Permit.zone_id == zone_id))
        await self.session.execute(
            update(m.WorkerZoneLog)
            .where(m.WorkerZoneLog.zone_id == zone_id, m.WorkerZoneLog.exited_at.is_(None))
            .values(exited_at=_utcnow())
        )
        await self.set_maintenance_flag(zone_id, False)


class RiskRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _row_to_schema(self, row: m.RiskInstanceRow) -> RiskInstance:
        components = row.crs_components or {"severity": 0.9, "confidence": 0.86, "recency": 0.98}
        band = CRSBand(row.crs_band) if row.crs_band in CRSBand.__members__ else crs_band(row.crs)
        signals = [
            ContributingSignal(type=s.signal_key, value=s.signal_value)
            for s in sorted(row.signals, key=lambda x: x.recorded_at)
        ]
        timeline = [
            TimelineEvent(
                ts=t.ts.replace(tzinfo=None) if t.ts.tzinfo else t.ts,
                event=t.event_type,
                actor=t.actor_id or "system",
                note=t.justification,
            )
            for t in sorted(row.timeline, key=lambda x: x.ts)
        ]
        return RiskInstance(
            risk_id=row.id,
            org_id=row.org_id,
            plant_id=row.plant_id,
            zone_id=row.zone_id,
            status=RiskStatus(row.status),
            motif_id=row.motif_id,
            motif_version=row.motif_version,
            crs=CRS(
                score=row.crs,
                band=band,
                components=CRSComponents(**components),
            ),
            lead_time_seconds=row.lead_time_seconds,
            contributing_signals=signals,
            detection=DetectionInfo(
                method=row.detection_method,
                deterministic=True,
                llm_involved=row.llm_involved,
            ),
            evidence_package_id=row.evidence_package_id,
            narrative=row.narrative,
            timeline=timeline,
            created_at=row.created_at.replace(tzinfo=None) if row.created_at.tzinfo else row.created_at,
            updated_at=row.updated_at.replace(tzinfo=None) if row.updated_at.tzinfo else row.updated_at,
        )

    async def get_risk(self, risk_id: str) -> RiskInstance | None:
        result = await self.session.execute(
            select(m.RiskInstanceRow)
            .where(m.RiskInstanceRow.id == risk_id)
            .options(
                selectinload(m.RiskInstanceRow.signals),
                selectinload(m.RiskInstanceRow.timeline),
            )
        )
        row = result.scalar_one_or_none()
        return self._row_to_schema(row) if row else None

    async def get_open_risk(self, zone_id: str, motif_id: str) -> RiskInstance | None:
        closed = {RiskStatus.RESOLVED.value, RiskStatus.FALSE_POSITIVE.value}
        result = await self.session.execute(
            select(m.RiskInstanceRow)
            .where(
                m.RiskInstanceRow.zone_id == zone_id,
                m.RiskInstanceRow.motif_id == motif_id,
                m.RiskInstanceRow.status.notin_(closed),
            )
            .options(
                selectinload(m.RiskInstanceRow.signals),
                selectinload(m.RiskInstanceRow.timeline),
            )
            .order_by(m.RiskInstanceRow.created_at.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        return self._row_to_schema(row) if row else None

    async def list_open_risks(self) -> list[RiskInstance]:
        closed = {RiskStatus.RESOLVED.value, RiskStatus.FALSE_POSITIVE.value}
        result = await self.session.execute(
            select(m.RiskInstanceRow)
            .where(m.RiskInstanceRow.status.notin_(closed))
            .options(
                selectinload(m.RiskInstanceRow.signals),
                selectinload(m.RiskInstanceRow.timeline),
            )
        )
        risks = [self._row_to_schema(r) for r in result.scalars().all()]
        return sorted(risks, key=lambda r: (-r.crs.score, -(r.lead_time_seconds or 0)))

    async def create_risk_instance(self, risk: RiskInstance) -> RiskInstance:
        row = m.RiskInstanceRow(
            id=risk.risk_id,
            zone_id=risk.zone_id,
            motif_id=risk.motif_id,
            org_id=risk.org_id,
            plant_id=risk.plant_id,
            crs=risk.crs.score,
            crs_band=risk.crs.band.value,
            crs_components=risk.crs.components.model_dump(),
            status=risk.status.value,
            motif_version=risk.motif_version,
            detection_method=risk.detection.method,
            llm_involved=risk.detection.llm_involved,
            forecast_eta_minutes=(risk.lead_time_seconds / 60.0) if risk.lead_time_seconds else None,
            lead_time_seconds=risk.lead_time_seconds,
            narrative=risk.narrative,
            evidence_package_id=risk.evidence_package_id,
            created_at=risk.created_at,
            updated_at=risk.updated_at,
        )
        self.session.add(row)
        for sig in risk.contributing_signals:
            self.session.add(
                m.RiskSignal(
                    risk_instance_id=risk.risk_id,
                    signal_key=sig.type,
                    signal_value=sig.value,
                )
            )
        for ev in risk.timeline:
            self.session.add(
                m.RiskTimeline(
                    risk_instance_id=risk.risk_id,
                    event_type=ev.event,
                    actor_id=ev.actor,
                    justification=ev.note,
                    ts=ev.ts,
                )
            )
        await self.session.flush()
        return risk

    async def update_risk_instance(self, risk: RiskInstance) -> RiskInstance:
        row = await self.session.get(m.RiskInstanceRow, risk.risk_id)
        if not row:
            return await self.create_risk_instance(risk)

        row.crs = risk.crs.score
        row.crs_band = risk.crs.band.value
        row.crs_components = risk.crs.components.model_dump()
        row.status = risk.status.value
        row.lead_time_seconds = risk.lead_time_seconds
        row.forecast_eta_minutes = (risk.lead_time_seconds / 60.0) if risk.lead_time_seconds else None
        row.narrative = risk.narrative
        row.evidence_package_id = risk.evidence_package_id
        row.llm_involved = risk.detection.llm_involved
        row.detection_method = risk.detection.method
        row.updated_at = risk.updated_at

        await self.session.execute(
            delete(m.RiskSignal).where(m.RiskSignal.risk_instance_id == risk.risk_id)
        )
        for sig in risk.contributing_signals:
            self.session.add(
                m.RiskSignal(
                    risk_instance_id=risk.risk_id,
                    signal_key=sig.type,
                    signal_value=sig.value,
                )
            )

        # Append only new timeline events (by count)
        existing_tl = (
            await self.session.execute(
                select(m.RiskTimeline).where(m.RiskTimeline.risk_instance_id == risk.risk_id)
            )
        ).scalars().all()
        for ev in risk.timeline[len(existing_tl) :]:
            self.session.add(
                m.RiskTimeline(
                    risk_instance_id=risk.risk_id,
                    event_type=ev.event,
                    actor_id=ev.actor,
                    justification=ev.note,
                    ts=ev.ts,
                )
            )
        await self.session.flush()
        return risk

    async def save_evidence(
        self,
        evidence: EvidencePackage,
        agent_meta: dict | None = None,
    ) -> EvidencePackage:
        existing = await self.session.get(m.EvidencePackageRow, evidence.evidence_id)
        if existing:
            existing.narrative = evidence.risk_summary
            existing.confidence = evidence.confidence
            existing.agent_reasoning_trace = evidence.agent_reasoning_trace
            await self.session.execute(
                delete(m.AgentFinding).where(m.AgentFinding.evidence_package_id == evidence.evidence_id)
            )
            await self.session.execute(
                delete(m.RootCauseHypothesisRow).where(
                    m.RootCauseHypothesisRow.evidence_package_id == evidence.evidence_id
                )
            )
            await self.session.execute(
                delete(m.RecommendationRow).where(
                    m.RecommendationRow.evidence_package_id == evidence.evidence_id
                )
            )
            await self.session.execute(
                delete(m.EvidenceCitation).where(
                    m.EvidenceCitation.evidence_package_id == evidence.evidence_id
                )
            )
        else:
            self.session.add(
                m.EvidencePackageRow(
                    id=evidence.evidence_id,
                    risk_instance_id=evidence.risk_id,
                    narrative=evidence.risk_summary,
                    confidence=evidence.confidence,
                    agent_reasoning_trace=evidence.agent_reasoning_trace,
                    created_at=evidence.assembled_at,
                )
            )
            await self.session.flush()

        for name, text in evidence.agent_findings.items():
            finding_meta = (agent_meta or {}).get(name) or (agent_meta or {}).get(f"{name}_agent") or {}
            self.session.add(
                m.AgentFinding(
                    evidence_package_id=evidence.evidence_id,
                    agent_name=name if name.endswith("_agent") else f"{name}_agent" if name != "planner" else "planner_agent",
                    finding_text=text,
                    raw_response_json=finding_meta.get("output"),
                    model_used=finding_meta.get("model") or evidence.confidence.get("model"),
                    latency_ms=finding_meta.get("latency_ms"),
                )
            )
        for hyp in evidence.root_cause_hypotheses:
            self.session.add(
                m.RootCauseHypothesisRow(
                    evidence_package_id=evidence.evidence_id,
                    hypothesis=hyp.hypothesis,
                    confidence=hyp.confidence,
                    rank=hyp.rank,
                    citations=hyp.citations,
                )
            )
        for i, rec in enumerate(evidence.recommendations, start=1):
            self.session.add(
                m.RecommendationRow(
                    evidence_package_id=evidence.evidence_id,
                    action_text=rec.action,
                    projected_crs=rec.projected_crs_after,
                    rank=i,
                    citations=rec.citation,
                    counterfactual_ran=rec.counterfactual_ran,
                )
            )
        for cite in evidence.regulatory_citations:
            reg_id = cite.ref.replace(" ", "").replace("§", "-S")
            # Ensure regulation exists
            if not await self.session.get(m.Regulation, reg_id):
                self.session.add(
                    m.Regulation(id=reg_id, source=cite.framework, clause_text=cite.text)
                )
            self.session.add(
                m.EvidenceCitation(
                    evidence_package_id=evidence.evidence_id,
                    regulation_id=reg_id,
                    similarity_score=1.0,
                )
            )
        for hist in evidence.historical_references:
            existing_inc = (
                await self.session.execute(
                    select(m.IncidentCorpus).where(m.IncidentCorpus.external_id == hist.incident_id)
                )
            ).scalar_one_or_none()
            if not existing_inc:
                existing_inc = m.IncidentCorpus(
                    external_id=hist.incident_id,
                    title=hist.summary[:120],
                    report_text=hist.summary,
                )
                self.session.add(existing_inc)
                await self.session.flush()
            self.session.add(
                m.EvidenceCitation(
                    evidence_package_id=evidence.evidence_id,
                    incident_id=existing_inc.id,
                    similarity_score=hist.similarity,
                )
            )

        risk_row = await self.session.get(m.RiskInstanceRow, evidence.risk_id)
        if risk_row:
            risk_row.evidence_package_id = evidence.evidence_id

        await self.session.flush()
        return evidence

    async def get_evidence(self, evidence_id: str) -> EvidencePackage | None:
        row = await self.session.get(m.EvidencePackageRow, evidence_id)
        if not row:
            return None
        return await self._assemble_evidence(row)

    async def get_evidence_by_risk(self, risk_id: str) -> EvidencePackage | None:
        result = await self.session.execute(
            select(m.EvidencePackageRow)
            .where(m.EvidencePackageRow.risk_instance_id == risk_id)
            .order_by(m.EvidencePackageRow.created_at.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        if not row:
            return None
        return await self._assemble_evidence(row)

    async def _assemble_evidence(self, row: m.EvidencePackageRow) -> EvidencePackage:
        findings = (
            await self.session.execute(
                select(m.AgentFinding).where(m.AgentFinding.evidence_package_id == row.id)
            )
        ).scalars().all()
        hyps = (
            await self.session.execute(
                select(m.RootCauseHypothesisRow)
                .where(m.RootCauseHypothesisRow.evidence_package_id == row.id)
                .order_by(m.RootCauseHypothesisRow.rank)
            )
        ).scalars().all()
        recs = (
            await self.session.execute(
                select(m.RecommendationRow)
                .where(m.RecommendationRow.evidence_package_id == row.id)
                .order_by(m.RecommendationRow.rank)
            )
        ).scalars().all()
        cites = (
            await self.session.execute(
                select(m.EvidenceCitation).where(m.EvidenceCitation.evidence_package_id == row.id)
            )
        ).scalars().all()

        regulatory: list[RegulatoryCitation] = []
        historical: list[HistoricalReference] = []
        for c in cites:
            if c.regulation_id:
                reg = await self.session.get(m.Regulation, c.regulation_id)
                if reg:
                    regulatory.append(
                        RegulatoryCitation(framework=reg.source, ref=reg.id, text=reg.clause_text)
                    )
            if c.incident_id:
                inc = await self.session.get(m.IncidentCorpus, c.incident_id)
                if inc:
                    historical.append(
                        HistoricalReference(
                            incident_id=inc.external_id or str(inc.id),
                            similarity=c.similarity_score or 0.0,
                            summary=inc.report_text,
                        )
                    )

        return EvidencePackage(
            evidence_id=row.id,
            risk_id=row.risk_instance_id,
            risk_summary=row.narrative or "",
            root_cause_hypotheses=[
                RootCauseHypothesis(
                    rank=h.rank,
                    hypothesis=h.hypothesis,
                    confidence=h.confidence,
                    citations=h.citations or [],
                )
                for h in hyps
            ],
            recommendations=[
                Recommendation(
                    action=r.action_text,
                    projected_crs_after=r.projected_crs or 0,
                    counterfactual_ran=r.counterfactual_ran,
                    citation=r.citations or [],
                )
                for r in recs
            ],
            regulatory_citations=regulatory,
            historical_references=historical,
            agent_reasoning_trace=row.agent_reasoning_trace,
            agent_findings={f.agent_name: f.finding_text for f in findings},
            confidence=row.confidence or {},
            assembled_at=row.created_at.replace(tzinfo=None) if row.created_at.tzinfo else row.created_at,
        )

    async def clear_risks_and_evidence(self) -> None:
        await self.session.execute(delete(m.EvidenceCitation))
        await self.session.execute(delete(m.AgentFinding))
        await self.session.execute(delete(m.RootCauseHypothesisRow))
        await self.session.execute(delete(m.RecommendationRow))
        await self.session.execute(delete(m.EvidencePackageRow))
        await self.session.execute(delete(m.RiskSignal))
        await self.session.execute(delete(m.RiskTimeline))
        await self.session.execute(delete(m.OutcomeRecordRow))
        await self.session.execute(delete(m.EmergencyEvent))
        await self.session.execute(delete(m.RiskInstanceRow))


class OpsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def write_audit(
        self,
        action: str,
        actor: str,
        target_type: str,
        target_id: str,
        justification: str | None = None,
        details: dict | None = None,
    ) -> None:
        self.session.add(
            m.AuditLog(
                actor_username=actor,
                action=action,
                target_entity_type=target_type,
                target_entity_id=target_id,
                justification=justification,
                details=details,
            )
        )

    async def list_audit(self, limit: int = 50) -> list[dict[str, Any]]:
        rows = (
            await self.session.execute(
                select(m.AuditLog).order_by(m.AuditLog.ts.desc()).limit(limit)
            )
        ).scalars().all()
        return [
            {
                "ts": (r.ts.replace(tzinfo=None) if r.ts.tzinfo else r.ts).isoformat(),
                "action": r.action,
                "actor": r.actor_username or "system",
                "details": r.details or {
                    "target_type": r.target_entity_type,
                    "target_id": r.target_entity_id,
                    "justification": r.justification,
                },
            }
            for r in rows
        ]

    async def declare_emergency(
        self, zone_id: str, risk_id: str | None, actor: str
    ) -> EmergencyStatus:
        now = _utcnow()
        steps = [
            {"step": "Emergency confirmed", "status": "complete", "ts": now.isoformat()},
            {"step": "Evacuation initiated", "status": "complete", "ts": now.isoformat()},
            {"step": "3 workers notified (2 ack, 1 pending)", "status": "in_progress", "ts": now.isoformat()},
            {"step": "Response team paged", "status": "complete", "ts": now.isoformat()},
            {"step": "Evidence locked", "status": "complete", "ts": now.isoformat()},
            {"step": "Draft incident report generating", "status": "in_progress", "ts": now.isoformat()},
        ]
        # Resolve prior active emergencies
        active = (
            await self.session.execute(
                select(m.EmergencyEvent).where(m.EmergencyEvent.status == "active")
            )
        ).scalars().all()
        for ev in active:
            ev.status = "resolved"
            ev.resolved_at = now

        self.session.add(
            m.EmergencyEvent(
                risk_instance_id=risk_id,
                zone_id=zone_id,
                declared_by_username=actor,
                status="active",
                checklist_json=steps,
                declared_at=now,
            )
        )
        await self.write_audit(
            "emergency_declare",
            actor,
            "zone",
            zone_id,
            details={"risk_id": risk_id},
        )
        await self.session.flush()
        return EmergencyStatus(
            active=True,
            zone_id=zone_id,
            risk_id=risk_id,
            steps=steps,
            declared_at=now,
        )

    async def get_emergency(self) -> EmergencyStatus:
        row = (
            await self.session.execute(
                select(m.EmergencyEvent)
                .where(m.EmergencyEvent.status == "active")
                .order_by(m.EmergencyEvent.declared_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if not row:
            return EmergencyStatus(active=False, steps=[])
        return EmergencyStatus(
            active=True,
            zone_id=row.zone_id,
            risk_id=row.risk_instance_id,
            steps=row.checklist_json if isinstance(row.checklist_json, list) else [],
            declared_at=row.declared_at.replace(tzinfo=None) if row.declared_at.tzinfo else row.declared_at,
        )

    async def record_outcome(
        self,
        risk_id: str,
        classification: str,
        recommendation_rating: int | None = None,
        root_cause_rating: int | None = None,
        notes: str | None = None,
    ) -> None:
        self.session.add(
            m.OutcomeRecordRow(
                risk_instance_id=risk_id,
                actual_outcome=classification,
                recommendation_rating=recommendation_rating,
                root_cause_rating=root_cause_rating,
                notes=notes,
            )
        )
        await self.write_audit(
            "outcome_recorded",
            "system",
            "risk",
            risk_id,
            details={"classification": classification},
        )
