"""RAG over resolved ITSM tickets — ChromaDB vector search + ticket formatting."""

from __future__ import annotations

import json
from pathlib import Path

from tickets import load_tickets

ROOT = Path(__file__).resolve().parent.parent
SEED_PATH = ROOT / "data" / "resolved_tickets_seed.jsonl"
MIN_SIMILARITY = 0.35


def _load_seed_tickets() -> list[dict]:
    if not SEED_PATH.exists():
        return []
    rows: list[dict] = []
    for line in SEED_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def ticket_document(ticket: dict) -> str:
    parts = [
        str(ticket.get("customer_ask") or ""),
        str(ticket.get("path_label") or ""),
        str(ticket.get("surec_label") or ""),
        str(ticket.get("birim_label") or ""),
        str(ticket.get("recommended_next_step") or ""),
        str(ticket.get("resolution_summary") or ""),
        str(ticket.get("handoff_notes") or ""),
    ]
    for bullet in ticket.get("summary_bullets") or []:
        parts.append(str(bullet))
    for followup in ticket.get("followups") or []:
        if isinstance(followup, dict):
            parts.append(str(followup.get("text") or ""))
        else:
            parts.append(str(followup))
    for message in ticket.get("messages") or []:
        if isinstance(message, dict):
            parts.append(str(message.get("content") or ""))
    return " ".join(part.strip() for part in parts if part and str(part).strip())


def resolved_tickets() -> list[dict]:
    merged: dict[str, dict] = {}
    for ticket in _load_seed_tickets() + load_tickets():
        if ticket.get("status") != "resolved":
            continue
        tid = str(ticket.get("id") or "")
        if tid:
            merged[tid] = ticket
    return list(merged.values())


def invalidate_index() -> None:
    from vector_store import reset_store

    reset_store()


def find_similar_resolved_tickets(
    query: str,
    *,
    surec: str = "",
    birim: str = "",
    limit: int = 2,
    min_score: float = MIN_SIMILARITY,
) -> list[dict]:
    """Return resolved tickets ranked by semantic similarity (ChromaDB)."""
    from vector_store import query_similar

    return query_similar(
        query,
        surec=surec,
        birim=birim,
        limit=limit,
        min_similarity=min_score,
    )


def ticket_conversation(ticket: dict) -> list[dict]:
    """Normalize ticket thread for UI/API."""
    messages = list(ticket.get("messages") or [])
    if messages:
        return [
            {
                "role": str(item.get("role") or "user"),
                "content": str(item.get("content") or "").strip(),
                "at": str(item.get("at") or ""),
            }
            for item in messages
            if str(item.get("content") or "").strip()
        ]

    thread: list[dict] = []
    ask = str(ticket.get("customer_ask") or "").strip()
    if ask:
        thread.append(
            {
                "role": "user",
                "content": ask,
                "at": str(ticket.get("created_at") or ""),
            }
        )
    for followup in ticket.get("followups") or []:
        text = followup.get("text") if isinstance(followup, dict) else str(followup)
        text = str(text or "").strip()
        if not text:
            continue
        at = followup.get("at") if isinstance(followup, dict) else ""
        thread.append({"role": "user", "content": text, "at": str(at or "")})

    resolution = str(ticket.get("resolution_summary") or ticket.get("recommended_next_step") or "").strip()
    if resolution:
        thread.append(
            {
                "role": "agent",
                "content": resolution,
                "at": str(ticket.get("resolved_at") or ""),
            }
        )
    return thread


def format_similar_ticket_payload(match: dict) -> dict:
    ticket = match["ticket"]
    return {
        "id": ticket.get("id"),
        "score": match.get("score"),
        "similarity_pct": match.get("similarity_pct"),
        "status": ticket.get("status"),
        "path_label": ticket.get("path_label"),
        "surec_label": ticket.get("surec_label"),
        "birim_label": ticket.get("birim_label"),
        "priority": ticket.get("priority"),
        "customer_ask": ticket.get("customer_ask"),
        "resolution_summary": ticket.get("resolution_summary") or ticket.get("recommended_next_step"),
        "created_at": ticket.get("created_at"),
        "resolved_at": ticket.get("resolved_at"),
        "messages": ticket_conversation(ticket),
    }
