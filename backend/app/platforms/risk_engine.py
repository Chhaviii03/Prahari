"""Deterministic Compound Risk Engine - Platform 3."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from app.models.schemas import (
    ContributingSignal,
    CRS,
    CRSBand,
    CRSComponents,
    DetectionInfo,
    RiskInstance,
    RiskStatus,
    TimelineEvent,
    ZoneState,
)


@dataclass
class Motif:
    motif_id: str
    version: str
    name: str
    description: str
    severity: float
    required_signals: list[str]
    hazard_icons: list[str]


MOTIFS: dict[str, Motif] = {
    "CS-HOTWORK-GAS": Motif(
        motif_id="CS-HOTWORK-GAS",
        version="v3",
        name="Gas + Hot Work + Confined Space",
        description="Rising combustible gas with active hot-work and confined-space entry",
        severity=0.95,
        required_signals=["rising_gas", "hot_work_permit", "confined_space"],
        hazard_icons=["gas", "hotwork", "confined"],
    ),
    "MAINT-GAS-OCCUPIED": Motif(
        motif_id="MAINT-GAS-OCCUPIED",
        version="v2",
        name="Maintenance + Rising Gas + Occupied Zone",
        description="Scheduled maintenance with rising combustible gas and workers in zone",
        severity=0.92,
        required_signals=["rising_gas", "maintenance_active", "occupancy"],
        hazard_icons=["gas", "maintenance", "workers"],
    ),
    "HOTWORK-PERMIT-CONFLICT": Motif(
        motif_id="HOTWORK-PERMIT-CONFLICT",
        version="v1",
        name="Simultaneous Operations Conflict",
        description="Conflicting permits in same zone with hazardous conditions",
        severity=0.75,
        required_signals=["hot_work_permit", "confined_space", "permit_conflict"],
        hazard_icons=["hotwork", "confined"],
    ),
    "PPE-GAS-ENTRY": Motif(
        motif_id="PPE-GAS-ENTRY",
        version="v1",
        name="PPE Missing + Rising Gas + Entry",
        description="Worker without PPE in zone with rising gas during confined entry",
        severity=0.85,
        required_signals=["ppe_missing", "rising_gas", "confined_space"],
        hazard_icons=["ppe", "gas", "confined"],
    ),
    "EQUIP-FAULT-GAS": Motif(
        motif_id="EQUIP-FAULT-GAS",
        version="v1",
        name="Equipment Fault + Gas Rise",
        description="Equipment maintenance flag with rising gas readings",
        severity=0.80,
        required_signals=["equipment_fault", "rising_gas"],
        hazard_icons=["equipment", "gas"],
    ),
}


def crs_band(score: float) -> CRSBand:
    if score >= 75:
        return CRSBand.CRITICAL
    if score >= 40:
        return CRSBand.ACTIVE
    return CRSBand.WATCH


def compute_crs(motif: Motif, confidences: list[float], recencies: list[float], weights: list[float] | None = None) -> CRS:
    if not confidences:
        confidences = [0.8]
    if not recencies:
        recencies = [1.0]
    if weights is None:
        weights = [1.0] * len(confidences)

    weighted_sum = sum(w * c * r for w, c, r in zip(weights, confidences, recencies))
    weight_total = sum(weights) or 1.0
    support = weighted_sum / weight_total
    score = min(100.0, 100.0 * motif.severity * support)

    return CRS(
        score=round(score, 1),
        band=crs_band(score),
        components=CRSComponents(
            severity=motif.severity,
            confidence=round(sum(confidences) / len(confidences), 2),
            recency=round(sum(recencies) / len(recencies), 2),
        ),
    )


def evaluate_zone(zone: ZoneState, maintenance_active: bool = False, equipment_fault: bool = False, ppe_missing: bool = False) -> list[tuple[Motif, CRS, list[ContributingSignal], int | None]]:
    """Evaluate all motifs against zone state. Returns list of (motif, crs, signals, lead_time)."""
    results: list[tuple[Motif, CRS, list[ContributingSignal], int | None]] = []

    rising_gas = zone.ch4_lel > 2 or (zone.forecast_eta_minutes is not None and zone.forecast_eta_minutes < 120)
    hot_work = any("HOTWORK" in p or "HOT-WORK" in p.upper() for p in zone.active_permits)
    confined_active = any("CONFINED" in p.upper() for p in zone.active_permits)
    confined_scheduled = any("CONFINED" in p.upper() for p in zone.scheduled_permits)
    confined_space = confined_active or confined_scheduled
    occupancy = zone.occupancy > 0
    permit_conflict = hot_work and confined_space

    lead_time_seconds: int | None = None
    if zone.forecast_eta_minutes is not None:
        lead_time_seconds = int(zone.forecast_eta_minutes * 60)

    signal_map: dict[str, bool] = {
        "rising_gas": rising_gas,
        "hot_work_permit": hot_work,
        "confined_space": confined_space,
        "maintenance_active": maintenance_active,
        "occupancy": occupancy,
        "permit_conflict": permit_conflict,
        "ppe_missing": ppe_missing,
        "equipment_fault": equipment_fault,
    }

    for motif in MOTIFS.values():
        if not all(signal_map.get(s, False) for s in motif.required_signals):
            continue

        signals: list[ContributingSignal] = []
        if rising_gas:
            eta = zone.forecast_eta_minutes
            if eta and eta > 200:
                eta = int(zone.ch4_lel * 5) if zone.ch4_lel > 0 else None
            eta_str = f"→100% LEL in ~{int(eta or 0)}m" if eta else f"{zone.ch4_lel:.1f}% LEL"
            signals.append(ContributingSignal(type="CH4_FORECAST" if eta else "CH4_LEL", value=eta_str))
        if hot_work:
            permit = next((p for p in zone.active_permits if "HOT" in p.upper()), "HOTWORK active")
            signals.append(ContributingSignal(type="PERMIT", value=f"HOTWORK {permit} active"))
        if confined_space:
            permit = next((p for p in zone.active_permits + zone.scheduled_permits if "CONFINED" in p.upper()), "CONFINED_ENTRY scheduled")
            signals.append(ContributingSignal(type="PERMIT", value=f"CONFINED_ENTRY {permit}"))
        if maintenance_active:
            signals.append(ContributingSignal(type="MAINTENANCE", value="Scheduled maintenance job active in-zone"))
        if occupancy:
            signals.append(ContributingSignal(type="OCCUPANCY", value=f"{zone.occupancy} workers in hazard zone"))
        if equipment_fault:
            signals.append(ContributingSignal(type="EQUIPMENT", value="E-441 valve maintenance flag (9 days ago)"))
        if ppe_missing:
            signals.append(ContributingSignal(type="CV_DETECTION", value="PPE_MISSING detected via CCTV"))

        confidences = [0.86 if zone.data_quality == "GOOD" else 0.5]
        crs = compute_crs(motif, confidences, [0.98])
        results.append((motif, crs, signals, lead_time_seconds))

    results.sort(key=lambda x: x[1].score, reverse=True)
    return results


def status_from_crs(band: CRSBand) -> RiskStatus:
    if band == CRSBand.CRITICAL:
        return RiskStatus.CRITICAL
    if band == CRSBand.ACTIVE:
        return RiskStatus.ACTIVE
    return RiskStatus.WATCH


def create_risk_instance(
    motif: Motif,
    crs: CRS,
    zone: ZoneState,
    signals: list[ContributingSignal],
    lead_time: int | None,
    org_id: str,
    plant_id: str,
    risk_id: str,
    now: datetime | None = None,
) -> RiskInstance:
    now = now or datetime.utcnow()
    return RiskInstance(
        risk_id=risk_id,
        org_id=org_id,
        plant_id=plant_id,
        zone_id=zone.zone_id,
        status=status_from_crs(crs.band),
        motif_id=motif.motif_id,
        motif_version=motif.version,
        crs=crs,
        lead_time_seconds=lead_time,
        contributing_signals=signals,
        detection=DetectionInfo(),
        timeline=[TimelineEvent(ts=now, event="CREATED", actor="P3")],
        created_at=now,
        updated_at=now,
    )


def single_sensor_baseline_detect(zone: ZoneState) -> bool:
    """Simulate SCADA single-threshold alarming."""
    return zone.ch4_lel >= 10 or zone.h2s_ppm >= 10 or zone.co_ppm >= 35
