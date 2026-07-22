# PRAHARI — Industrial Safety Intelligence Platform

**प्रहरी** — *"the sentinel who watches so others may work."*

AI-Powered Industrial Safety Intelligence for Zero-Harm Operations. Built per PRD v1.1 for ET AI Hackathon 2026, Problem Statement #1.

## What It Does

PRAHARI sits above plant systems and fuses sensor, permit, maintenance, and worker data into a live risk picture. It detects **compound hazards** — dangerous combinations of individually-normal conditions — using a **deterministic** rule engine (no LLM in the detection path). AI is used only to explain, retrieve evidence, and recommend.

### Core Differentiators

1. **Deterministic core, AI periphery** — P3 decides "is this dangerous?"; P4/P5 explain "why and what to do?"
2. **Compound hazard detection** — Gas + hot work + confined space, even when no single sensor breaches threshold
3. **Forecast-aware lead time** — Projects sensor trends against scheduled work
4. **Evidence packages** — Cited regulations (OISD, Factory Act), historical precedent, counterfactual-scored recommendations

## UI (current)

The web app uses a **light coral / blush** safety console (not a dark SOC theme):

| Token | Role | Example |
|-------|------|---------|
| Canvas | App background | `#FAF8F8` |
| Surface | Cards, sidebar | `#FFFFFF` |
| Accent | CTAs, icons, links | coral peach (`#F5A892` / `#B4533A` text) |
| Ink | Primary / secondary text | `#0F172A` / `#475569` |

- Font: **Plus Jakarta Sans** (+ JetBrains Mono for tabular IDs)
- Soft rose binary watermark on the canvas
- **Geospatial Heatmap** uses **Leaflet** (Esri satellite + OSM) with CRS zone polygons, workers, and evacuation routes over Visakhapatnam Steel Plant bounds

### Main screens

| Route | Screen |
|-------|--------|
| `/` | Live Safety Dashboard — risk queue + system status |
| `/heatmap` | Leaflet plant map + zone / permit side panels |
| `/risk/:id` | Evidence package, agent findings, acknowledge / emergency |
| `/incident` | Incident response / evacuation |
| `/permits` | Permit Intelligence |
| `/copilot` | Grounded AI Q&A |
| `/notifications` | Notification Center |
| `/analytics` | Historical Analytics |
| `/reports` | Reports Library |
| `/executive` | Executive KPI roll-up |
| `/mobile` | Worker field view |
| `/admin/users`, `/settings` | Admin |

## Seed data (edit without touching code)

All demo content is in the **`seed/`** folder as JSON files. See [`seed/README.md`](seed/README.md) for full docs.

- Change scenario timeline → edit `seed/scenarios/coke-oven.json`
- Switch scenarios → set `"active_scenario"` in `seed/config.json` or `POST /v1/demo/load-scenario?scenario=h2s-leak`
- Reload after edits → `POST /v1/demo/reload-seed` (or restart backend)


### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (running)
- Python 3.11+
- Node.js 18+ (for frontend)

### 1. Database setup (PostgreSQL 16 + TimescaleDB)

Each developer runs this **on their own machine**. The database is local (`localhost`) — it is not shared automatically with teammates.

#### Step A — Start the database container

From the `Prahari/` folder (where `docker-compose.yml` lives):

```bash
docker compose up -d
```

Confirm in Docker Desktop that **`prahari` → `db-1`** is running, with ports **`5433:5432`**.

> Port **5433** on the host maps to Postgres **5432** inside the container (avoids clashes with a local Postgres already on 5432).

#### Step B — Install backend deps, migrate, and seed

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
python -m scripts.seed
```

This creates all tables and seeds:

- Plant + 6 zones (C-10 … C-15) and sensors
- Motifs, demo users, regulations / incidents corpus
- Equipment (E-441)

Default connection (also in `backend/.env.example`):

| Field | Value |
|--------|--------|
| Host | `localhost` |
| Port | `5433` |
| Database | `prahari` |
| Username | `prahari` |
| Password | `prahari_dev` |
| URL | `postgresql+asyncpg://prahari:prahari_dev@localhost:5433/prahari` |

#### Step C — View tables (pick one)

**pgAdmin (GUI, no SQL required)**

1. Install [pgAdmin 4](https://www.pgadmin.org/download/)
2. Register Server → Connection tab with the credentials above
3. Browse: **Databases → prahari → Schemas → public → Tables**
4. Right-click a table → **View/Edit Data → All Rows**

**`psql` via Docker**

```bash
docker exec -it prahari-db-1 psql -U prahari -d prahari
```

```sql
\dt
SELECT * FROM zones;
SELECT * FROM risk_instances LIMIT 10;
```

**`psql` on your machine** (if PostgreSQL client tools are installed)

```bash
psql -h localhost -p 5433 -U prahari -d prahari
```

#### Teammates / friends

1. Clone or copy this repo  
2. Repeat **Steps A–B** on their laptop  
3. Use **Step C** to inspect tables  

They get the same **schema + seed data**. Demo runtime rows (risks after “Load Coke-Oven Demo”) appear only after they run the app demo themselves.

### 2. Backend (Python/FastAPI)

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

Persistence: risk instances, sensor readings (Timescale hypertable), permits, evidence, audit, and emergencies are stored in Postgres. `PrahariState` keeps a cache + replay/websocket orchestration only.

### 3. Frontend (React/TypeScript/Tailwind)

```bash
cd frontend
npm install
npm run dev
```

App: http://localhost:5173

> After pull, always run `npm install` so **Leaflet** / **react-leaflet** are present (`leaflet/dist/leaflet.css` is imported from `src/main.tsx`).

### Demo Accounts

| Username   | Role            | Password | Lands on |
|-----------|-----------------|----------|----------|
| safety    | Safety Officer  | prahari  | Dashboard |
| permit    | Permit Officer  | prahari  | Permits |
| compliance| Compliance Officer | prahari | Reports |
| executive | Executive       | prahari  | Executive |
| worker    | Worker (mobile) | prahari  | Mobile |
| admin     | Admin           | prahari  | Users |

## Demo Flow

1. Sign in as **safety** / **prahari**
2. Click **"Load Coke-Oven Demo"** on the Safety Dashboard
3. Open the Critical risk instance (C-12, CRS ~86)
4. Review Evidence Package with OISD citations and counterfactual recommendations
5. Open **Geospatial Heatmap** — satellite map with CRS overlays, workers, and evacuation routes
6. Acknowledge the risk (notification fan-out) or escalate to **Incident Response**
7. Check **Worker Mobile** for the field-worker evacuate / safe view
8. Ask **AI Copilot** a grounded question about the active risk

## Architecture (8 Platforms)

| Platform | Name | Role |
|----------|------|------|
| P1 | Data Intelligence | Ingest, validate, normalize events |
| P2 | Digital Twin | Live plant state + Holt forecasting |
| P3 | Compound Risk Engine | **Deterministic** motif detection + CRS scoring |
| P4 | Multi-Agent Intelligence | AI enrichment (Sensor, Permit, Worker, Equipment, Compliance, Planner) |
| P5 | Decision Intelligence | RAG, root cause, counterfactual recommendations |
| P6 | Safety Operations | Dashboard, Leaflet heatmap, emergency, mobile |
| P7 | Learning & Knowledge | Outcome recording, evaluation |
| P8 | Enterprise Platform | Auth, RBAC, audit |

## Tech Stack

- **Backend:** FastAPI, Pydantic, SQLAlchemy 2.0 async + asyncpg, Alembic, JWT auth
- **LLM (P4):** OpenAI-compatible client — Groq free tier (primary) → Ollama local (fallback) → mock
- **Database:** PostgreSQL 16 + TimescaleDB (`sensor_readings`, `audit_log` hypertables); embeddings as JSONB (pgvector-ready for Phase 4)
- **Frontend:** React 18, TypeScript, Tailwind CSS, Vite, **Leaflet / react-leaflet**
- **Design:** Light coral/blush theme (Plus Jakarta Sans); severity colors for CRITICAL / ACTIVE / WATCH / OK

## Multi-Agent LLM setup (P4)

Agents run **only after** a risk is flagged (slow lane). Motif/CRS detection stays deterministic (no LLM).

```bash
# backend/.env
LLM_PROVIDER=auto          # mock | groq | ollama | auto
GROQ_API_KEY=gsk_...       # from https://console.groq.com/keys
OLLAMA_MODEL=llama3.1:8b   # after: ollama pull llama3.1:8b
```

| Provider | When |
|----------|------|
| `auto` | Groq if key set → else Ollama → else mock |
| `groq` | Groq, falls back to Ollama on failure |
| `ollama` | Local only (`http://localhost:11434/v1`) |
| `mock` | Template-like JSON — tests / offline CI |

Pipeline: Sensor → Permit → Equipment → Compliance → Planner. Outputs land in `agent_findings` (model, latency_ms, raw JSON).

## API Endpoints

Key endpoints under `/v1/`:
- `POST /auth/login` — Authentication
- `GET /ops/dashboard` — Live risk queue
- `GET /ops/heatmap` — Geospatial / map config + zones
- `GET /risk/instances` — Risk instances from P3
- `GET /decision/evidence/by-risk/{id}` — Evidence packages
- `POST /demo/load-scenario` — Load coke-oven demo
- `GET /learning/eval` — Session evaluation metrics

## License

Built for ET AI Hackathon 2026.
