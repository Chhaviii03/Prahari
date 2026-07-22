"""SQLAlchemy 2.0 ORM models — maps 1:1 to the persistent schema."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    PrimaryKeyConstraint,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Core plant structure
# ---------------------------------------------------------------------------


class Plant(Base):
    __tablename__ = "plants"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # e.g. vsp_1
    name: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    zones: Mapped[list[Zone]] = relationship(back_populates="plant")


class Zone(Base):
    __tablename__ = "zones"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # e.g. C-12
    plant_id: Mapped[str] = mapped_column(String(64), ForeignKey("plants.id"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    hazard_class: Mapped[Optional[str]] = mapped_column(Text)
    geo_bounds: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    plant: Mapped[Plant] = relationship(back_populates="zones")
    sensors: Mapped[list[Sensor]] = relationship(back_populates="zone")


class ZoneAdjacency(Base):
    __tablename__ = "zone_adjacency"
    __table_args__ = (
        PrimaryKeyConstraint("zone_id", "adjacent_zone_id", "relationship"),
    )

    zone_id: Mapped[str] = mapped_column(String(32), ForeignKey("zones.id"), nullable=False)
    adjacent_zone_id: Mapped[str] = mapped_column(String(32), ForeignKey("zones.id"), nullable=False)
    relationship_type: Mapped[str] = mapped_column("relationship", Text, nullable=False)


# ---------------------------------------------------------------------------
# Sensors (time-series)
# ---------------------------------------------------------------------------


class Sensor(Base):
    __tablename__ = "sensors"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    zone_id: Mapped[str] = mapped_column(String(32), ForeignKey("zones.id"), nullable=False)
    sensor_type: Mapped[str] = mapped_column(Text, nullable=False)
    unit: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="healthy")
    installed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    zone: Mapped[Zone] = relationship(back_populates="sensors")


class SensorReading(Base):
    __tablename__ = "sensor_readings"
    __table_args__ = (PrimaryKeyConstraint("sensor_id", "ts"),)

    sensor_id: Mapped[str] = mapped_column(String(64), ForeignKey("sensors.id"), nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)


# ---------------------------------------------------------------------------
# Equipment & maintenance
# ---------------------------------------------------------------------------


class Equipment(Base):
    __tablename__ = "equipment"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    zone_id: Mapped[str] = mapped_column(String(32), ForeignKey("zones.id"), nullable=False)
    equipment_type: Mapped[str] = mapped_column(Text, nullable=False)
    health_score: Mapped[Optional[float]] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MaintenanceRecord(Base):
    __tablename__ = "maintenance_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    equipment_id: Mapped[str] = mapped_column(String(64), ForeignKey("equipment.id"), nullable=False)
    work_order_ref: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


# ---------------------------------------------------------------------------
# Permits
# ---------------------------------------------------------------------------


class Permit(Base):
    __tablename__ = "permits"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    zone_id: Mapped[str] = mapped_column(String(32), ForeignKey("zones.id"), nullable=False)
    permit_type: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    scope_description: Mapped[Optional[str]] = mapped_column(Text)
    issued_by: Mapped[Optional[str]] = mapped_column(Text)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_to: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ---------------------------------------------------------------------------
# Workers
# ---------------------------------------------------------------------------


class Worker(Base):
    __tablename__ = "workers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    certifications: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text))


class WorkerZoneLog(Base):
    __tablename__ = "worker_zone_log"
    __table_args__ = (PrimaryKeyConstraint("worker_id", "zone_id", "entered_at"),)

    worker_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workers.id"), nullable=False)
    zone_id: Mapped[str] = mapped_column(String(32), ForeignKey("zones.id"), nullable=False)
    entered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    exited_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class PermitWorker(Base):
    __tablename__ = "permit_workers"
    __table_args__ = (PrimaryKeyConstraint("permit_id", "worker_id"),)

    permit_id: Mapped[str] = mapped_column(String(64), ForeignKey("permits.id"), nullable=False)
    worker_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workers.id"), nullable=False)


# ---------------------------------------------------------------------------
# Motifs
# ---------------------------------------------------------------------------


class Motif(Base):
    __tablename__ = "motifs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[float] = mapped_column(Float, nullable=False)
    required_signals: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    version: Mapped[str] = mapped_column(Text, nullable=False, default="v1")
    hazard_icons: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text))


# ---------------------------------------------------------------------------
# Risk instances
# ---------------------------------------------------------------------------


class RiskInstanceRow(Base):
    __tablename__ = "risk_instances"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    zone_id: Mapped[str] = mapped_column(String(32), ForeignKey("zones.id"), nullable=False)
    motif_id: Mapped[str] = mapped_column(String(64), ForeignKey("motifs.id"), nullable=False)
    org_id: Mapped[str] = mapped_column(String(64), nullable=False, default="org_vsp")
    plant_id: Mapped[str] = mapped_column(String(64), nullable=False, default="vsp_1")
    crs: Mapped[float] = mapped_column(Float, nullable=False)
    crs_band: Mapped[str] = mapped_column(Text, nullable=False, default="WATCH")
    crs_components: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    motif_version: Mapped[str] = mapped_column(Text, nullable=False, default="v1")
    detection_method: Mapped[str] = mapped_column(Text, nullable=False, default="MOTIF")
    llm_involved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    forecast_eta_minutes: Mapped[Optional[float]] = mapped_column(Float)
    lead_time_seconds: Mapped[Optional[int]] = mapped_column(Integer)
    narrative: Mapped[Optional[str]] = mapped_column(Text)
    evidence_package_id: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    signals: Mapped[list[RiskSignal]] = relationship(back_populates="risk", cascade="all, delete-orphan")
    timeline: Mapped[list[RiskTimeline]] = relationship(back_populates="risk", cascade="all, delete-orphan")


class RiskSignal(Base):
    __tablename__ = "risk_signals"
    __table_args__ = (PrimaryKeyConstraint("id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    risk_instance_id: Mapped[str] = mapped_column(String(64), ForeignKey("risk_instances.id"), nullable=False)
    signal_key: Mapped[str] = mapped_column(Text, nullable=False)
    signal_value: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[Optional[float]] = mapped_column(Float)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    risk: Mapped[RiskInstanceRow] = relationship(back_populates="signals")


class RiskTimeline(Base):
    __tablename__ = "risk_timeline"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    risk_instance_id: Mapped[str] = mapped_column(String(64), ForeignKey("risk_instances.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    actor_id: Mapped[Optional[str]] = mapped_column(Text)
    justification: Mapped[Optional[str]] = mapped_column(Text)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    risk: Mapped[RiskInstanceRow] = relationship(back_populates="timeline")


# ---------------------------------------------------------------------------
# Evidence packages (P5)
# ---------------------------------------------------------------------------


class EvidencePackageRow(Base):
    __tablename__ = "evidence_packages"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # EP-...
    risk_instance_id: Mapped[str] = mapped_column(String(64), ForeignKey("risk_instances.id"), nullable=False)
    narrative: Mapped[Optional[str]] = mapped_column(Text)
    confidence: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    agent_reasoning_trace: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AgentFinding(Base):
    __tablename__ = "agent_findings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evidence_package_id: Mapped[str] = mapped_column(String(64), ForeignKey("evidence_packages.id"), nullable=False)
    agent_name: Mapped[str] = mapped_column(Text, nullable=False)
    finding_text: Mapped[str] = mapped_column(Text, nullable=False)
    raw_response_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    model_used: Mapped[Optional[str]] = mapped_column(Text)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RootCauseHypothesisRow(Base):
    __tablename__ = "root_cause_hypotheses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evidence_package_id: Mapped[str] = mapped_column(String(64), ForeignKey("evidence_packages.id"), nullable=False)
    hypothesis: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    citations: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text))


class RecommendationRow(Base):
    __tablename__ = "recommendations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evidence_package_id: Mapped[str] = mapped_column(String(64), ForeignKey("evidence_packages.id"), nullable=False)
    action_text: Mapped[str] = mapped_column(Text, nullable=False)
    projected_crs: Mapped[Optional[float]] = mapped_column(Float)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    citations: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text))
    counterfactual_ran: Mapped[bool] = mapped_column(Boolean, default=True)


# ---------------------------------------------------------------------------
# Regulations & incidents (RAG corpus — Phase 4 ready; embeddings as JSONB)
# ---------------------------------------------------------------------------


class Regulation(Base):
    __tablename__ = "regulations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    clause_text: Mapped[str] = mapped_column(Text, nullable=False)
    # JSONB list[float] until pgvector is available on the image
    embedding: Mapped[Optional[list[Any]]] = mapped_column(JSONB)


class IncidentCorpus(Base):
    __tablename__ = "incidents_corpus"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_id: Mapped[Optional[str]] = mapped_column(Text, unique=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    report_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Optional[list[Any]]] = mapped_column(JSONB)


class EvidenceCitation(Base):
    __tablename__ = "evidence_citations"
    __table_args__ = (PrimaryKeyConstraint("id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evidence_package_id: Mapped[str] = mapped_column(String(64), ForeignKey("evidence_packages.id"), nullable=False)
    regulation_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("regulations.id"))
    incident_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("incidents_corpus.id"))
    similarity_score: Mapped[Optional[float]] = mapped_column(Float)


# ---------------------------------------------------------------------------
# Enterprise / RBAC / Audit
# ---------------------------------------------------------------------------


class UserRow(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False, default="")
    zone_scope: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_log"
    __table_args__ = (PrimaryKeyConstraint("id", "ts"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), default=uuid.uuid4)
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    actor_username: Mapped[Optional[str]] = mapped_column(Text)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    target_entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    target_entity_id: Mapped[str] = mapped_column(Text, nullable=False)
    justification: Mapped[Optional[str]] = mapped_column(Text)
    details: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


# ---------------------------------------------------------------------------
# Emergency / Outcomes
# ---------------------------------------------------------------------------


class EmergencyEvent(Base):
    __tablename__ = "emergency_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    risk_instance_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("risk_instances.id"))
    zone_id: Mapped[Optional[str]] = mapped_column(String(32), ForeignKey("zones.id"))
    declared_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    declared_by_username: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    checklist_json: Mapped[Optional[list[Any] | dict[str, Any]]] = mapped_column(JSONB)
    declared_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class OutcomeRecordRow(Base):
    __tablename__ = "outcome_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    risk_instance_id: Mapped[str] = mapped_column(String(64), ForeignKey("risk_instances.id"), nullable=False)
    actual_outcome: Mapped[str] = mapped_column(Text, nullable=False)
    recommendation_rating: Mapped[Optional[int]] = mapped_column(Integer)
    root_cause_rating: Mapped[Optional[int]] = mapped_column(Integer)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    recorded_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
