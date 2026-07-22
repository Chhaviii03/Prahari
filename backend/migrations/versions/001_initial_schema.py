"""initial schema with timescaledb hypertables

Revision ID: 001_initial
Revises:
Create Date: 2026-07-22
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _timescaledb_available(connection) -> bool:
    row = connection.execute(
        sa.text("SELECT 1 FROM pg_available_extensions WHERE name = 'timescaledb'")
    ).scalar()
    return row is not None


def _enable_timescaledb_if_possible() -> bool:
    """Enable Timescale when the extension exists (Docker image). Skip on Neon/Supabase."""
    connection = op.get_bind()
    if not _timescaledb_available(connection):
        return False
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE")
    return True


def upgrade() -> None:
    has_timescale = _enable_timescaledb_if_possible()

    op.create_table(
        "plants",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("location", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "zones",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("plant_id", sa.String(64), sa.ForeignKey("plants.id"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("hazard_class", sa.Text()),
        sa.Column("geo_bounds", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "zone_adjacency",
        sa.Column("zone_id", sa.String(32), sa.ForeignKey("zones.id"), nullable=False),
        sa.Column("adjacent_zone_id", sa.String(32), sa.ForeignKey("zones.id"), nullable=False),
        sa.Column("relationship", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("zone_id", "adjacent_zone_id", "relationship"),
    )

    op.create_table(
        "sensors",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("zone_id", sa.String(32), sa.ForeignKey("zones.id"), nullable=False),
        sa.Column("sensor_type", sa.Text(), nullable=False),
        sa.Column("unit", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="healthy"),
        sa.Column("installed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "sensor_readings",
        sa.Column("sensor_id", sa.String(64), sa.ForeignKey("sensors.id"), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("sensor_id", "ts"),
    )
    op.execute("SELECT create_hypertable('sensor_readings', 'ts', if_not_exists => TRUE)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_sensor_readings_sensor_ts "
        "ON sensor_readings (sensor_id, ts DESC)"
    )

    op.create_table(
        "equipment",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("zone_id", sa.String(32), sa.ForeignKey("zones.id"), nullable=False),
        sa.Column("equipment_type", sa.Text(), nullable=False),
        sa.Column("health_score", sa.Float()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "maintenance_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("equipment_id", sa.String(64), sa.ForeignKey("equipment.id"), nullable=False),
        sa.Column("work_order_ref", sa.Text()),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("note", sa.Text()),
        sa.Column("opened_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "permits",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("zone_id", sa.String(32), sa.ForeignKey("zones.id"), nullable=False),
        sa.Column("permit_type", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("scope_description", sa.Text()),
        sa.Column("issued_by", sa.Text()),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_permits_zone_status", "permits", ["zone_id", "status"])

    op.create_table(
        "workers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("certifications", postgresql.ARRAY(sa.Text())),
    )

    op.create_table(
        "worker_zone_log",
        sa.Column("worker_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workers.id"), nullable=False),
        sa.Column("zone_id", sa.String(32), sa.ForeignKey("zones.id"), nullable=False),
        sa.Column("entered_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("exited_at", sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint("worker_id", "zone_id", "entered_at"),
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_worker_zone_current "
        "ON worker_zone_log (zone_id) WHERE exited_at IS NULL"
    )

    op.create_table(
        "permit_workers",
        sa.Column("permit_id", sa.String(64), sa.ForeignKey("permits.id"), nullable=False),
        sa.Column("worker_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workers.id"), nullable=False),
        sa.PrimaryKeyConstraint("permit_id", "worker_id"),
    )

    op.create_table(
        "motifs",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("severity", sa.Float(), nullable=False),
        sa.Column("required_signals", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("version", sa.Text(), nullable=False, server_default="v1"),
        sa.Column("hazard_icons", postgresql.ARRAY(sa.Text())),
    )

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("username", sa.Text(), nullable=False, unique=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False, server_default=""),
        sa.Column("zone_scope", postgresql.ARRAY(sa.Text())),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "risk_instances",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("zone_id", sa.String(32), sa.ForeignKey("zones.id"), nullable=False),
        sa.Column("motif_id", sa.String(64), sa.ForeignKey("motifs.id"), nullable=False),
        sa.Column("org_id", sa.String(64), nullable=False, server_default="org_vsp"),
        sa.Column("plant_id", sa.String(64), nullable=False, server_default="vsp_1"),
        sa.Column("crs", sa.Float(), nullable=False),
        sa.Column("crs_band", sa.Text(), nullable=False, server_default="WATCH"),
        sa.Column("crs_components", postgresql.JSONB()),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("motif_version", sa.Text(), nullable=False, server_default="v1"),
        sa.Column("detection_method", sa.Text(), nullable=False, server_default="MOTIF"),
        sa.Column("llm_involved", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("forecast_eta_minutes", sa.Float()),
        sa.Column("lead_time_seconds", sa.Integer()),
        sa.Column("narrative", sa.Text()),
        sa.Column("evidence_package_id", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "risk_signals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("risk_instance_id", sa.String(64), sa.ForeignKey("risk_instances.id"), nullable=False),
        sa.Column("signal_key", sa.Text(), nullable=False),
        sa.Column("signal_value", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float()),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "risk_timeline",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("risk_instance_id", sa.String(64), sa.ForeignKey("risk_instances.id"), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("actor_id", sa.Text()),
        sa.Column("justification", sa.Text()),
        sa.Column("ts", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "evidence_packages",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("risk_instance_id", sa.String(64), sa.ForeignKey("risk_instances.id"), nullable=False),
        sa.Column("narrative", sa.Text()),
        sa.Column("confidence", postgresql.JSONB()),
        sa.Column("agent_reasoning_trace", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "agent_findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("evidence_package_id", sa.String(64), sa.ForeignKey("evidence_packages.id"), nullable=False),
        sa.Column("agent_name", sa.Text(), nullable=False),
        sa.Column("finding_text", sa.Text(), nullable=False),
        sa.Column("raw_response_json", postgresql.JSONB()),
        sa.Column("model_used", sa.Text()),
        sa.Column("latency_ms", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "root_cause_hypotheses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("evidence_package_id", sa.String(64), sa.ForeignKey("evidence_packages.id"), nullable=False),
        sa.Column("hypothesis", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("citations", postgresql.ARRAY(sa.Text())),
    )

    op.create_table(
        "recommendations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("evidence_package_id", sa.String(64), sa.ForeignKey("evidence_packages.id"), nullable=False),
        sa.Column("action_text", sa.Text(), nullable=False),
        sa.Column("projected_crs", sa.Float()),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("citations", postgresql.ARRAY(sa.Text())),
        sa.Column("counterfactual_ran", sa.Boolean(), server_default=sa.text("true")),
    )

    op.create_table(
        "regulations",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("clause_text", sa.Text(), nullable=False),
        sa.Column("embedding", postgresql.JSONB()),
    )

    op.create_table(
        "incidents_corpus",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("external_id", sa.Text(), unique=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("report_text", sa.Text(), nullable=False),
        sa.Column("embedding", postgresql.JSONB()),
    )

    op.create_table(
        "evidence_citations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("evidence_package_id", sa.String(64), sa.ForeignKey("evidence_packages.id"), nullable=False),
        sa.Column("regulation_id", sa.String(64), sa.ForeignKey("regulations.id")),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("incidents_corpus.id")),
        sa.Column("similarity_score", sa.Float()),
    )

    op.create_table(
        "audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("actor_username", sa.Text()),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("target_entity_type", sa.Text(), nullable=False),
        sa.Column("target_entity_id", sa.Text(), nullable=False),
        sa.Column("justification", sa.Text()),
        sa.Column("details", postgresql.JSONB()),
        sa.Column("ts", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    # Timescale requires a non-unique time dimension PK for hypertables when
    # another PK exists; drop UUID-only PK and use composite (id, ts).
    op.drop_constraint("audit_log_pkey", "audit_log", type_="primary")
    op.create_primary_key("audit_log_pkey", "audit_log", ["id", "ts"])
    op.execute("SELECT create_hypertable('audit_log', 'ts', if_not_exists => TRUE)")

    op.create_table(
        "emergency_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("risk_instance_id", sa.String(64), sa.ForeignKey("risk_instances.id")),
        sa.Column("zone_id", sa.String(32), sa.ForeignKey("zones.id")),
        sa.Column("declared_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("declared_by_username", sa.Text()),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("checklist_json", postgresql.JSONB()),
        sa.Column("declared_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "outcome_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("risk_instance_id", sa.String(64), sa.ForeignKey("risk_instances.id"), nullable=False),
        sa.Column("actual_outcome", sa.Text(), nullable=False),
        sa.Column("recommendation_rating", sa.Integer()),
        sa.Column("root_cause_rating", sa.Integer()),
        sa.Column("notes", sa.Text()),
        sa.Column("recorded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def downgrade() -> None:
    for table in [
        "outcome_records",
        "emergency_events",
        "audit_log",
        "evidence_citations",
        "incidents_corpus",
        "regulations",
        "recommendations",
        "root_cause_hypotheses",
        "agent_findings",
        "evidence_packages",
        "risk_timeline",
        "risk_signals",
        "risk_instances",
        "users",
        "motifs",
        "permit_workers",
        "worker_zone_log",
        "workers",
        "permits",
        "maintenance_records",
        "equipment",
        "sensor_readings",
        "sensors",
        "zone_adjacency",
        "zones",
        "plants",
    ]:
        op.drop_table(table)
