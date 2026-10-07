"""Session policy: lock BERT class, treat short replies as slots, allow related follow-ups."""

from __future__ import annotations

from text_norm import fold_tr

_FOLLOWUP_HINTS = (
    "ne kadar",
    "kaç gün",
    "kac gun",
    "kaç günüm",
    "bakiy",
    "nasıl",
    "nasil",
    "neden",
    "niye",
    "hangi",
    "nereden",
    "ne zaman",
    "peşine",
    "pesine",
    "bir de",
    "birde ",
    "peki ",
    "olabilir mi",
    "olabilir miyiz",
    "eksik",
    "hala",
    "hâlâ",
    "devam ediyor",
    "aynı hata",
    "ayni hata",
    "yine aynı",
    "yine ayni",
    "ancak",
    "fakat",
    "ama ben",
    "söylediğiniz gibi",
    "soylediginiz gibi",
)

_CONTINUE_HINTS = (
    "devam ediyor",
    "aynı hata",
    "ayni hata",
    "hala ",
    "hâlâ ",
    "yine ",
    "tekrar at",
    "tekrar dene",
    "işe yaram",
    "ise yaram",
    "açtığını",
    "actigini",
    "yaptım",
    "yaptim",
    "denedim",
    "görüştüm",
    "gorustum",
    "olabilir mi",
    "kısıtlama",
    "kisitlama",
    "hesap turu",
    "hesap türü",
)

_NEW_TOPIC = (
    "başka konu",
    "baska konu",
    "farklı bir sorun",
    "farkli bir sorun",
    "yeni talep",
    "ayrı bir iş",
    "ayri bir is",
    "konu değiş",
    "konu degis",
)


def looks_like_new_topic(text: str) -> bool:
    lowered = fold_tr(text)
    return any(fold_tr(p) in lowered for p in _NEW_TOPIC)


def looks_like_followup_question(text: str) -> bool:
    raw = (text or "").strip()
    if looks_like_new_topic(raw):
        return True
    if len(raw) < 8:
        return False
    lowered = fold_tr(raw)
    if "?" in raw:
        return True
    return any(fold_tr(p) in lowered for p in _FOLLOWUP_HINTS)


def looks_like_troubleshooting_continue(text: str) -> bool:
    """User stays on the same incident: tried the steps, still failing, new detail."""
    raw = (text or "").strip()
    if not raw or looks_like_new_topic(raw):
        return False
    lowered = fold_tr(raw)
    if any(fold_tr(p) in lowered for p in _CONTINUE_HINTS):
        return True
    return len(raw) >= 80


def looks_like_slot_reply(text: str) -> bool:
    raw = (text or "").strip()
    if not raw:
        return False
    if looks_like_followup_question(raw) or looks_like_new_topic(raw):
        return False
    if len(raw) <= 56 and "\n" not in raw:
        return True
    return False


def same_unit(previous: dict | None, incoming: dict | None) -> bool:
    if not previous or not incoming:
        return False
    if previous.get("unclear") or incoming.get("unclear"):
        return False
    left = str(previous.get("birim") or "")
    right = str(incoming.get("birim") or "")
    return bool(left) and left == right


def resolve_classification(
    *,
    text: str,
    phase: str,
    previous: dict | None,
    incoming_full: dict,
    incoming_turn: dict,
    user_rejects: bool,
) -> dict:
    """Keep the BERT decision unless the user starts a related or new request."""
    if user_rejects or phase in {"open", "clarify"} or not previous or previous.get("unclear"):
        return incoming_full if incoming_full and not incoming_full.get("unclear") else incoming_turn or incoming_full or previous

    if looks_like_new_topic(text) or looks_like_followup_question(text):
        chosen = incoming_turn
        if chosen and not chosen.get("unclear"):
            return chosen
        return previous

    if phase in {"suggest_solution", "collect_fields", "ticket_open"}:
        return previous

    return incoming_full if incoming_full and not incoming_full.get("unclear") else previous
