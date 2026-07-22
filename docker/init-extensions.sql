-- TimescaleDB is typically preloaded in the image; ensure it's available.
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- pgvector is optional in the base Timescale image; embeddings use JSONB in v1.
-- When available (e.g. timescaledb-ha or custom image), enable for Phase 4 RAG:
-- CREATE EXTENSION IF NOT EXISTS vector;
