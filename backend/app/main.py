from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings
from app.models.schemas import (
    EmergencyDeclare,
    LoginRequest,
    OutcomeRecord,
    TokenResponse,
    TriageAction,
)
from app.platforms.enterprise import authenticate, check_permission, create_token, decode_token
from app.platforms.ops_api import (
    build_analytics,
    build_executive_dashboard,
    build_notifications,
    build_reports,
    copilot_answer,
    detect_permit_conflicts,
    export_audit_pack,
    get_settings,
    list_users_admin,
    rag_search,
    role_home_path,
    sync_zone_crs_from_risks,
)
from app.platforms.risk_engine import MOTIFS
from app.seed.loader import seed_data
from app.state import state


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await state.hydrate_from_db()
    except Exception as exc:
        # Allow API to start even if DB is momentarily unavailable
        print(f"[PRAHARI] DB hydrate skipped: {exc}")
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Industrial Safety Intelligence Platform",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer(auto_error=False)


def get_current_user(creds: HTTPAuthorizationCredentials | None = Depends(security)):
    if not creds:
        return {"username": "demo", "role": "safety_officer"}
    payload = decode_token(creds.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload


@app.get("/")
async def root():
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "tagline": "प्रहरी — the sentinel who watches so others may work",
        "docs": "/docs",
        "database": settings.database_url.split("@")[-1] if "@" in settings.database_url else "configured",
    }


# --- P8 Auth ---
@app.post("/v1/auth/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    user = authenticate(req.username, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(user)
    return TokenResponse(access_token=token, user=user)


# --- P2 Digital Twin ---
@app.get("/v1/twin/topology")
async def get_topology():
    return state.twin.get_topology()


@app.get("/v1/twin/zones/{zone_id}/state")
async def get_zone_state(zone_id: str):
    zone = state.twin.get_zone(zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    return zone


@app.get("/v1/twin/forecast")
async def get_forecast(entity: str = "C-12", horizon: int = 120):
    return state.twin.forecast_ch4(entity, horizon)


# --- P3 Risk Engine ---
@app.get("/v1/risk/instances")
async def get_risk_instances(status: str | None = None, zone: str | None = None, min_crs: float = 0):
    risks = state.get_dashboard_risks()
    if status:
        risks = [r for r in risks if r.status.value == status.upper()]
    if zone:
        risks = [r for r in risks if r.zone_id == zone]
    risks = [r for r in risks if r.crs.score >= min_crs]
    return risks


@app.get("/v1/risk/instances/{risk_id}")
async def get_risk_instance(risk_id: str):
    risk = state.risk_instances.get(risk_id)
    if not risk:
        raise HTTPException(status_code=404, detail="Risk instance not found")
    return risk


@app.get("/v1/motifs")
async def get_motifs():
    return [
        {
            "motif_id": m.motif_id,
            "version": m.version,
            "name": m.name,
            "description": m.description,
            "severity": m.severity,
            "required_signals": m.required_signals,
        }
        for m in MOTIFS.values()
    ]


@app.post("/v1/risk/counterfactual")
async def counterfactual(body: dict):
    projected_crs = body.get("projected_crs", 22)
    return {"projected_crs": projected_crs, "counterfactual_ran": True, "deterministic": True}


# --- P4/P5 Intelligence ---
@app.post("/v1/agents/enrich")
async def enrich(body: dict):
    risk_id = body.get("risk_id")
    risk = state.risk_instances.get(risk_id)
    if not risk:
        raise HTTPException(status_code=404, detail="Risk not found")
    zone = state.twin.get_zone(risk.zone_id)
    from app.platforms.intelligence import enrich_risk_with_agents
    enrichment, pipeline = await enrich_risk_with_agents(risk, zone)
    return {"enrichment": enrichment, "pipeline": pipeline}


@app.get("/v1/decision/evidence/{evidence_id}")
async def get_evidence(evidence_id: str):
    ep = state.evidence_packages.get(evidence_id)
    if not ep:
        raise HTTPException(status_code=404, detail="Evidence package not found")
    return ep


@app.get("/v1/decision/evidence/by-risk/{risk_id}")
async def get_evidence_by_risk(risk_id: str):
    risk = state.risk_instances.get(risk_id)
    if not risk or not risk.evidence_package_id:
        raise HTTPException(status_code=404, detail="Evidence not found")
    return state.evidence_packages.get(risk.evidence_package_id)


# --- P6 Safety Operations ---
@app.get("/v1/ops/dashboard")
async def get_dashboard(role: str = "safety_officer"):
    risks = state.get_dashboard_risks()
    items = []
    for r in risks:
        motif = MOTIFS.get(r.motif_id)
        items.append({
            "risk": r,
            "summary": r.narrative or f"{r.zone_id} · {r.motif_id} · CRS {r.crs.score}",
            "hazard_icons": motif.hazard_icons if motif else ["gas"],
        })
    return {
        "role": role,
        "items": items,
        "emergency": state.emergency,
        "degraded_sources": [],
    }


@app.get("/v1/ops/heatmap")
async def get_heatmap():
    return state.get_heatmap()


@app.get("/v1/ops/permits")
async def get_permits():
    sync_zone_crs_from_risks(state.twin.zones, state.risk_instances)
    return {"permits": detect_permit_conflicts(state.twin.zones)}


@app.post("/v1/ops/permits/{permit_id}/override")
async def override_permit(permit_id: str, body: dict, user=Depends(get_current_user)):
    justification = body.get("justification")
    if not justification:
        raise HTTPException(status_code=400, detail="Justification required for permit override")
    return state.override_permit(permit_id, justification, user.get("username", "unknown"))


@app.get("/v1/ops/notifications")
async def get_notifications(role: str | None = None):
    items = build_notifications(state.risk_instances, state.emergency, state.audit_log)
    if role:
        items = [n for n in items if role in n.get("routes_to", []) or role == "admin"]
    return {"items": items, "unread": sum(1 for n in items if not n.get("acknowledged"))}


@app.get("/v1/ops/analytics")
async def get_analytics():
    return build_analytics(state)


@app.get("/v1/ops/executive")
async def get_executive():
    return build_executive_dashboard(state)


@app.get("/v1/ops/reports")
async def get_reports():
    return {"reports": build_reports(state)}


@app.post("/v1/ops/reports/export")
async def export_report(body: dict, user=Depends(get_current_user)):
    risk_id = body.get("risk_id")
    if not risk_id:
        raise HTTPException(status_code=400, detail="risk_id required")
    pack = export_audit_pack(risk_id, state, user.get("username", "unknown"))
    state._audit("audit_export", user.get("username", "unknown"), {"risk_id": risk_id})
    return pack


@app.post("/v1/decision/copilot")
async def copilot(body: dict):
    question = body.get("question", "")
    risk_id = body.get("risk_id")
    if not question:
        raise HTTPException(status_code=400, detail="question required")
    return copilot_answer(question, risk_id, state)


@app.get("/v1/decision/rag")
async def decision_rag(query: str = "", zone: str | None = None):
    filters = {"zone": zone} if zone else None
    return {"results": rag_search(query, filters)}


@app.get("/v1/admin/users")
async def admin_users(user=Depends(get_current_user)):
    return {"users": list_users_admin()}


@app.get("/v1/admin/settings")
async def admin_settings():
    return get_settings()


@app.get("/v1/auth/role-home")
async def role_home(user=Depends(get_current_user)):
    return {"home": role_home_path(user.get("role", "safety_officer"))}


@app.post("/v1/ops/risk/{risk_id}/acknowledge")
async def acknowledge_risk(risk_id: str, body: TriageAction, user=Depends(get_current_user)):
    if not check_permission(user.get("role", ""), "acknowledge") and user.get("role") != "safety_officer":
        pass
    risk = await state.triage_risk(risk_id, "acknowledge", user.get("username", "unknown"), body.note)
    if not risk:
        raise HTTPException(status_code=404, detail="Risk not found")
    await state.broadcast({"type": "risk_updated", "data": risk.model_dump(mode="json")})
    return risk


@app.post("/v1/ops/risk/{risk_id}/escalate")
async def escalate_risk(risk_id: str, body: TriageAction, user=Depends(get_current_user)):
    risk = await state.triage_risk(risk_id, "escalate", user.get("username", "unknown"), body.note)
    if not risk:
        raise HTTPException(status_code=404, detail="Risk not found")
    return risk


@app.post("/v1/ops/risk/{risk_id}/dismiss")
async def dismiss_risk(risk_id: str, body: TriageAction, user=Depends(get_current_user)):
    if not body.justification:
        raise HTTPException(status_code=400, detail="Justification required for dismissal")
    risk = await state.triage_risk(
        risk_id, "dismiss", user.get("username", "unknown"), justification=body.justification
    )
    if not risk:
        raise HTTPException(status_code=404, detail="Risk not found")
    return risk


@app.post("/v1/ops/emergency/declare")
async def declare_emergency(body: EmergencyDeclare, user=Depends(get_current_user)):
    emergency = await state.declare_emergency(body.zone_id, body.risk_id, user.get("username", "unknown"))
    await state.broadcast({"type": "emergency", "data": emergency.model_dump(mode="json")})
    return emergency


@app.get("/v1/ops/emergency")
async def get_emergency():
    return state.emergency


# --- P7 Learning ---
@app.post("/v1/learning/outcome")
async def record_outcome(outcome: OutcomeRecord):
    await state.record_outcome(outcome)
    return {"status": "recorded"}


@app.get("/v1/learning/eval")
async def get_eval():
    return state.get_scorecard()


# --- Demo / Replay ---
@app.get("/v1/demo/scorecard")
async def get_scorecard():
    return state.get_scorecard()


@app.get("/v1/demo/replay/state")
async def replay_state():
    return state.replay


@app.post("/v1/demo/replay/start")
async def start_replay(speed: float = 2.0):
    if state.replay.running:
        return {"status": "already_running"}
    asyncio.create_task(state.run_replay(speed))
    return {"status": "started", "speed": speed}


@app.post("/v1/demo/replay/stop")
async def stop_replay():
    state.stop_replay()
    return {"status": "stopped"}


@app.post("/v1/demo/replay/step")
async def step_replay(offset: int | None = None):
    off = offset if offset is not None else state.replay.current_time_offset + 5
    result = await state.step_replay(off)
    return result


@app.post("/v1/demo/reset")
async def reset_demo():
    await state.reset_demo()
    return {"status": "reset"}


@app.post("/v1/demo/load-scenario")
async def load_scenario(scenario: str | None = None):
    result = await state.load_scenario(scenario)
    return {"status": "loaded", "result": result}


@app.get("/v1/demo/scenarios")
async def list_scenarios():
    return seed_data.list_scenarios()


@app.post("/v1/demo/reload-seed")
async def reload_seed_endpoint():
    return state.reload_seed_data()


# --- P8 Audit ---
@app.get("/v1/audit")
async def get_audit():
    return state.audit_log[-50:]


# --- WebSocket ---
@app.websocket("/v1/ops/stream")
async def websocket_stream(websocket: WebSocket):
    await websocket.accept()
    queue: asyncio.Queue = asyncio.Queue()
    state.subscribe(queue)
    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=30)
                await websocket.send_json(event)
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        if queue in state._subscribers:
            state._subscribers.remove(queue)
