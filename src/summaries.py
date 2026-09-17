"""Template ITSM brief. LLM is optional copy only."""

import os
from typing import Iterable


def _trim(text: str, limit: int = 220) -> str:
    cleaned = " ".join((text or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1] + "…"


def conversation_excerpt(history: Iterable[dict], latest_user: str, limit: int = 8) -> str:
    lines = []
    for message in list(history)[-limit:]:
        role = "Kullanıcı" if message.get("role") == "user" else "Asistan"
        lines.append(f"{role}: {_trim(str(message.get('content', '')), 320)}")
    lines.append(f"Kullanıcı: {_trim(latest_user, 320)}")
    return "\n".join(lines)


def llm_enabled() -> bool:
    return os.environ.get("ASSISTANT_USE_LLM", "1").strip().lower() in {"1", "true", "yes"}


def build_manager_copy(
    *,
    classification: dict,
    sentiment: str,
    customer_ask: str,
    why_unresolved: str,
    high_risk: bool,
    history: Iterable[dict],
    latest_user: str,
    slots: dict | None = None,
    solution_ids: list[str] | None = None,
) -> dict:
    path = classification.get("path_label") or "sınıf net değil"
    slots = slots or {}
    bullets = [
        f"{path} · üslup {sentiment}.",
        _trim(customer_ask, 160) or "Ek ayrıntı yok.",
        _trim(
            "Alanlar: "
            + ", ".join(
                f"{k}={slots.get(k) or '—'}"
                for k in ("asset", "location", "impact")
            )
            + ("; KB: " + ", ".join(solution_ids) if solution_ids else "")
            + ". "
            + why_unresolved,
            200,
        ),
    ]
    if high_risk:
        next_step = "Öncelikli: güvenlik/kesinti; aynı gün ara ve kaydı güncelle."
    else:
        next_step = "Sınıf ve alanları doğrula; KB denendiyse sonucu not et; kullanıcıyı bilgilendir."
    notes = (
        f"ITSM kayıt notu. Sınıf: {path}. Üslup: {sentiment}. "
        f"Gerekçe: {why_unresolved}\n\nSon konuşma:\n"
        f"{conversation_excerpt(history, latest_user)}"
    )
    if llm_enabled():
        from llm_analyze import generate_record_copy

        llm = generate_record_copy(
            category=path,
            sentiment=sentiment,
            customer_ask=customer_ask,
            tried_rules=list(solution_ids or []),
            why_unresolved=why_unresolved,
            high_risk=high_risk,
            thread_excerpt=conversation_excerpt(history, latest_user),
        )
        if llm:
            bullets = llm["summary_bullets"]
            notes = llm["handoff_notes"]
    return {
        "summary_bullets": bullets[:3],
        "recommended_next_step": next_step,
        "handoff_notes": notes,
    }
