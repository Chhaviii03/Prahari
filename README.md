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
5. **Demo scorecard** — Side-by-side comparison vs single-sensor SCADA baseline

## Seed data (edit without touching code)

All demo content is in the **`seed/`** folder as JSON files. See [`seed/README.md`](seed/README.md) for full docs.

- Change scenario timeline → edit `seed/scenarios/coke-oven.json`
- Switch scenarios → set `"active_scenario"` in `seed/config.json` or `POST /v1/demo/load-scenario?scenario=h2s-leak`
- Reload after edits → `POST /v1/demo/reload-seed` (or restart backend)


### Backend (Python/FastAPI)

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### Frontend (React/TypeScript/Tailwind)

```bash
cd frontend
npm install
npm run dev
```

App: http://localhost:5173

### Demo Accounts

| Username   | Role            | Password |
|-----------|-----------------|----------|
| safety    | Safety Officer  | prahari  |
| permit    | Permit Officer  | prahari  |
| executive | Executive       | prahari  |
| worker    | Worker (mobile) | prahari  |

## Demo Flow

1. Sign in as **safety** / **prahari**
2. Click **"Load Coke-Oven Demo"** on the Safety Dashboard
3. Open the Critical risk instance (C-12, CRS ~86)
4. Review Evidence Package with OISD citations and counterfactual recommendations
5. Visit **Demo Scorecard** to see PRAHARI vs baseline comparison
6. View **Geospatial Heatmap** for zone visualization
7. Check **Worker Mobile** for field-worker view

## Architecture (8 Platforms)

| Platform | Name | Role |
|----------|------|------|
| P1 | Data Intelligence | Ingest, validate, normalize events |
| P2 | Digital Twin | Live plant state + Holt forecasting |
| P3 | Compound Risk Engine | **Deterministic** motif detection + CRS scoring |
| P4 | Multi-Agent Intelligence | AI enrichment (Sensor, Permit, Worker, Equipment, Compliance, Planner) |
| P5 | Decision Intelligence | RAG, root cause, counterfactual recommendations |
| P6 | Safety Operations | Dashboard, heatmap, emergency, mobile |
| P7 | Learning & Knowledge | Outcome recording, evaluation |
| P8 | Enterprise Platform | Auth, RBAC, audit |

## Tech Stack

- **Backend:** FastAPI, Pydantic, statsmodels (Holt forecasting), JWT auth
- **Frontend:** React 18, TypeScript, Tailwind CSS, Vite
- **Design:** Dark control-room theme per PRD §18

## API Endpoints

Key endpoints under `/v1/`:
- `POST /auth/login` — Authentication
- `GET /ops/dashboard` — Live risk queue
- `GET /ops/heatmap` — Geospatial data
- `GET /risk/instances` — Risk instances from P3
- `GET /decision/evidence/by-risk/{id}` — Evidence packages
- `POST /demo/load-scenario` — Load coke-oven demo
- `GET /demo/scorecard` — Evaluation metrics

## License

Built for ET AI Hackathon 2026.
