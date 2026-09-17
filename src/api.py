"""FastAPI backend for ITSM AI Asistanı React client."""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

SRC = Path(__file__).resolve().parent
ROOT = SRC.parent
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from auth import authenticate
from sessions import (
    create_session,
    delete_session,
    get_user,
    init_sessions,
    session_expires_at,
)
from llm_engine import is_llm_active, llm_provider_label
from orchestrator import handle_turn
from reports import build_unit_summary, load_jobs, queue_report_job, run_queued_jobs
from solutions import get_feedback_analytics, get_solution_stats, load_solutions, record_feedback
from tickets import load_tickets, update_status


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        from vector_store import warmup_vector_store

        stats = warmup_vector_store()
        print(
            f"[vector_store] ready — indexed={stats.get('indexed_tickets', 0)} "
            f"model={stats.get('embed_model', '')}"
        )
    except Exception as exc:
        print(f"[vector_store] warmup skipped: {exc}")
    active = init_sessions()
    print(f"[auth] sessions loaded — active={active}")
    yield


app = FastAPI(title="ITSM AI Asistanı API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class LoginRequest(BaseModel):
    email: str
    password: str


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatTurnRequest(BaseModel):
    text: str
    history: list[ChatMessage] = Field(default_factory=list)
    phase: str = "open"
    last_rule_id: str | None = None
    last_ticket_id: str | None = None
    slots: dict[str, str] = Field(default_factory=dict)
    classification: dict[str, Any] | None = None


class FeedbackRequest(BaseModel):
    helpful: bool
    comment: str = ""


def _require_auth(authorization: str | None = Header(default=None)) -> dict[str, str]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Oturum gerekli.")
    token = authorization.removeprefix("Bearer ").strip()
    user = get_user(token)
    if not user:
        raise HTTPException(status_code=401, detail="Geçersiz oturum.")
    return user


def _optional_auth(authorization: str | None = Header(default=None)) -> dict[str, str] | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.removeprefix("Bearer ").strip()
    return get_user(token)


@app.get("/api/health")
def health() -> dict[str, Any]:
    try:
        from vector_store import store_stats

        vector_store = store_stats(refresh=False)
    except Exception as exc:
        vector_store = {"engine": "chromadb", "error": str(exc)}
    return {
        "status": "ok",
        "llm_active": is_llm_active(),
        "llm_provider": llm_provider_label(),
        "vector_store": vector_store,
    }


@app.post("/api/auth/login")
def login(body: LoginRequest) -> dict[str, Any]:
    user = authenticate(body.email, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="E-posta veya şifre hatalı.")
    token = create_session(user)
    return {
        "token": token,
        "user": user,
        "expires_at": session_expires_at(token),
    }


@app.post("/api/auth/logout")
def logout(
    authorization: str | None = Header(default=None),
    user: dict[str, str] = Depends(_require_auth),
) -> dict[str, str]:
    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
        delete_session(token)
    return {"status": "ok"}


@app.get("/api/auth/me")
def me(user: dict[str, str] = Depends(_require_auth)) -> dict[str, str]:
    return user


@app.post("/api/auth/refresh")
def refresh_session(
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Oturum gerekli.")
    token = authorization.removeprefix("Bearer ").strip()
    user = get_user(token, touch=True)
    if not user:
        raise HTTPException(status_code=401, detail="Geçersiz oturum.")
    return {"user": user, "expires_at": session_expires_at(token)}


@app.post("/api/chat/turn")
def chat_turn(
    body: ChatTurnRequest,
    user: dict[str, str] | None = Depends(_optional_auth),
) -> dict[str, Any]:
    history = [{"role": m.role, "content": m.content} for m in body.history]
    result = handle_turn(
        body.text,
        history=history,
        phase=body.phase,
        last_rule_id=body.last_rule_id,
        last_ticket_id=body.last_ticket_id,
        slots=body.slots,
        classification=body.classification,
        customer_email=(user or {}).get("email", ""),
    )
    return {
        "reply": result.reply,
        "phase": result.phase,
        "last_rule_id": result.last_rule_id,
        "ticket": result.ticket,
        "debug": result.debug,
        "slots": result.slots,
        "classification": result.classification,
        "similar_tickets": result.similar_tickets,
    }


@app.get("/api/tickets")
def list_tickets(_: dict[str, str] = Depends(_require_auth)) -> list[dict]:
    return load_tickets()


@app.patch("/api/tickets/{ticket_id}/status")
def patch_ticket_status(
    ticket_id: str,
    status: str,
    _: dict[str, str] = Depends(_require_auth),
) -> dict[str, Any]:
    updated = update_status(ticket_id, status)
    if not updated:
        raise HTTPException(status_code=404, detail="Bilet bulunamadı.")
    return updated


@app.get("/api/jobs")
def list_jobs(_: dict[str, str] = Depends(_require_auth)) -> list[dict]:
    return load_jobs()


@app.post("/api/jobs/run")
def run_jobs(_: dict[str, str] = Depends(_require_auth)) -> dict[str, Any]:
    ran = run_queued_jobs()
    return {"count": len(ran), "jobs": ran}


@app.post("/api/jobs/queue")
def queue_job(
    command: str,
    user: dict[str, str] = Depends(_require_auth),
) -> dict[str, Any]:
    job = queue_report_job(command=command, requested_by=user.get("email", ""))
    return job


@app.get("/api/analytics")
def analytics(_: dict[str, str] = Depends(_require_auth)) -> dict[str, Any]:
    tickets = load_tickets()
    fb = get_feedback_analytics()
    return {
        "total_tickets": len(tickets),
        "resolved": sum(1 for t in tickets if t.get("status") == "resolved"),
        "open": sum(1 for t in tickets if t.get("status") in {"open", "in_progress", ""}),
        "feedback": fb,
    }


@app.get("/api/solutions")
def list_solutions(_: dict[str, str] = Depends(_require_auth)) -> list[dict]:
    rows = load_solutions()
    enriched = []
    for row in rows:
        sid = str(row.get("id") or "")
        stats = get_solution_stats(sid)
        enriched.append({**row, "stats": stats})
    return enriched


@app.post("/api/solutions/{solution_id}/feedback")
def solution_feedback(
    solution_id: str,
    body: FeedbackRequest,
    _: dict[str, str] = Depends(_require_auth),
) -> dict[str, str]:
    record_feedback(solution_id, body.helpful, comment=body.comment)
    return {"status": "ok"}


@app.get("/api/reports/summary")
def report_summary(
    birim: str = "",
    _: dict[str, str] = Depends(_require_auth),
) -> dict[str, str]:
    return {"markdown": build_unit_summary(birim)}
