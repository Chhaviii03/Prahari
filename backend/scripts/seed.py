"""Seed plant topology, sensors, motifs, users, and RAG corpus."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Allow `python -m scripts.seed` from backend/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from passlib.context import CryptContext
from sqlalchemy import select

from app.config import settings
from app.db import models as m
from app.db.session import async_session_factory, engine
from app.platforms.digital_twin import PLANT_ZONES
from app.platforms.enterprise import DEMO_USERS
from app.platforms.intelligence import HISTORICAL_INCIDENTS, REGULATORY_CORPUS
from app.platforms.risk_engine import MOTIFS

try:
    import bcrypt as _bcrypt

    def _hash_password(password: str) -> str:
        return _bcrypt.hashpw(password.encode("utf-8"), _bcrypt.gensalt()).decode("utf-8")
except Exception:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def _hash_password(password: str) -> str:
        return pwd_context.hash(password)

SENSOR_SPECS = [
    ("CH4", "%LEL"),
    ("H2S", "ppm"),
    ("CO", "ppm"),
    ("O2", "%"),
    ("TEMP", "C"),
]


async def seed() -> None:
    async with async_session_factory() as session:
        # Plant
        if not await session.get(m.Plant, settings.demo_plant_id):
            session.add(
                m.Plant(
                    id=settings.demo_plant_id,
                    name="Visakhapatnam Steel Plant",
                    location="Visakhapatnam, India",
                )
            )

        # Zones + sensors
        for z in PLANT_ZONES:
            if not await session.get(m.Zone, z["zone_id"]):
                session.add(
                    m.Zone(
                        id=z["zone_id"],
                        plant_id=settings.demo_plant_id,
                        name=z["name"],
                        hazard_class=z["zone_class"],
                        geo_bounds=z["geo"],
                    )
                )
            for stype, unit in SENSOR_SPECS:
                sid = f"SEN-{stype}-{z['zone_id']}-01"
                if stype == "CH4" and z["zone_id"] == "C-12":
                    sid = "SEN-CH4-C12-03"
                if not await session.get(m.Sensor, sid):
                    session.add(
                        m.Sensor(
                            id=sid,
                            zone_id=z["zone_id"],
                            sensor_type=stype,
                            unit=unit,
                            status="healthy",
                        )
                    )

        # Equipment for C-12
        if not await session.get(m.Equipment, "E-441"):
            session.add(
                m.Equipment(
                    id="E-441",
                    zone_id="C-12",
                    equipment_type="valve",
                    health_score=0.55,
                )
            )

        # Motifs
        for motif in MOTIFS.values():
            existing = await session.get(m.Motif, motif.motif_id)
            if existing:
                existing.name = motif.name
                existing.severity = motif.severity
                existing.required_signals = motif.required_signals
                existing.description = motif.description
                existing.version = motif.version
                existing.hazard_icons = motif.hazard_icons
            else:
                session.add(
                    m.Motif(
                        id=motif.motif_id,
                        name=motif.name,
                        severity=motif.severity,
                        required_signals=motif.required_signals,
                        description=motif.description,
                        version=motif.version,
                        hazard_icons=motif.hazard_icons,
                    )
                )

        # Demo users (bcrypt)
        for username, data in DEMO_USERS.items():
            row = (
                await session.execute(select(m.UserRow).where(m.UserRow.username == username))
            ).scalar_one_or_none()
            zone_scope = [data["zone_id"]] if data.get("zone_id") else None
            if not row:
                session.add(
                    m.UserRow(
                        username=username,
                        password_hash=_hash_password(data["password"]),
                        role=data["role"].value if hasattr(data["role"], "value") else str(data["role"]),
                        name=data["name"],
                        zone_scope=zone_scope,
                    )
                )

        # Regulations corpus
        for cite in REGULATORY_CORPUS:
            reg_id = cite.ref.replace(" ", "").replace("§", "-S")
            if not await session.get(m.Regulation, reg_id):
                session.add(
                    m.Regulation(id=reg_id, source=cite.framework, clause_text=cite.text)
                )

        # Historical incidents
        for hist in HISTORICAL_INCIDENTS:
            existing = (
                await session.execute(
                    select(m.IncidentCorpus).where(m.IncidentCorpus.external_id == hist.incident_id)
                )
            ).scalar_one_or_none()
            if not existing:
                session.add(
                    m.IncidentCorpus(
                        external_id=hist.incident_id,
                        title=hist.summary[:120],
                        report_text=hist.summary,
                    )
                )

        # Zone adjacency (process flow around coke batteries)
        adj = [
            ("C-10", "C-11", "proximity"),
            ("C-11", "C-12", "process_flow_upstream"),
            ("C-12", "C-13", "process_flow_downstream"),
            ("C-12", "C-14", "proximity"),
        ]
        for a, b, rel in adj:
            existing = (
                await session.execute(
                    select(m.ZoneAdjacency).where(
                        m.ZoneAdjacency.zone_id == a,
                        m.ZoneAdjacency.adjacent_zone_id == b,
                        m.ZoneAdjacency.relationship_type == rel,
                    )
                )
            ).scalar_one_or_none()
            if not existing:
                session.add(
                    m.ZoneAdjacency(zone_id=a, adjacent_zone_id=b, relationship_type=rel)
                )

        await session.commit()
        print("Seed complete: plant, zones, sensors, motifs, users, corpus.")


async def main() -> None:
    try:
        await seed()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
