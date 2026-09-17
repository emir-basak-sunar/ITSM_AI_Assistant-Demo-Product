"""ITSM tickets as JSONL. No live ServiceNow."""

import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TICKETS_PATH = ROOT / "data" / "tickets.jsonl"


def _next_id(existing: list[dict]) -> str:
    day = datetime.now().strftime("%Y%m%d")
    prefix = f"T-{day}-"
    seq = 0
    for ticket in existing:
        tid = str(ticket.get("id", ""))
        if tid.startswith(prefix):
            try:
                seq = max(seq, int(tid.split("-")[-1]))
            except ValueError:
                pass
    return f"{prefix}{seq + 1:04d}"


def load_tickets() -> list[dict]:
    if not TICKETS_PATH.exists():
        return []
    tickets = []
    for line in TICKETS_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        tickets.append(json.loads(line))
    return tickets


def save_ticket(ticket: dict) -> dict:
    TICKETS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with TICKETS_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(ticket, ensure_ascii=False) + "\n")
    return ticket


def _rewrite(tickets: list[dict]) -> None:
    TICKETS_PATH.parent.mkdir(parents=True, exist_ok=True)
    TICKETS_PATH.write_text(
        "".join(json.dumps(t, ensure_ascii=False) + "\n" for t in tickets),
        encoding="utf-8",
    )


def create_ticket(
    *,
    urgency: str,
    customer_ask: str,
    why_unresolved: str,
    summary_bullets: list[str],
    recommended_next_step: str,
    handoff_notes: str,
    sentiment: str = "",
    customer_email: str = "",
    talep_turu: str = "",
    talep_turu_label: str = "",
    birim: str = "",
    birim_label: str = "",
    modul: str = "",
    modul_label: str = "",
    surec: str = "",
    surec_label: str = "",
    asset: str = "",
    location: str = "",
    impact: str = "",
    slots: dict | None = None,
    solution_ids: list[str] | None = None,
    priority: str = "Orta",
    kind: str = "ticket",
) -> dict:
    existing = load_tickets()
    slots_dict = dict(slots or {})
    
    # Fill fallback fields if present in slots
    asset_val = asset or slots_dict.get("asset") or slots_dict.get("cihaz_etiket_no") or slots_dict.get("cihaz_seri_no") or slots_dict.get("yazici_marka_model") or slots_dict.get("uygulama_adi") or ""
    loc_val = location or slots_dict.get("location") or slots_dict.get("ofis_lokasyon") or slots_dict.get("yazici_lokasyon") or slots_dict.get("lokasyon_kat_oda") or slots_dict.get("teslimat_lokasyonu") or ""
    impact_val = impact or slots_dict.get("impact") or slots_dict.get("etkilenen_kisi_sayisi") or ""
    
    created_at = datetime.now().isoformat(timespec="seconds")
    ticket = {
        "id": _next_id(existing),
        "created_at": created_at,
        "kind": kind,
        "status": "open",
        "urgency": urgency,
        "priority": priority or "Orta",
        "sentiment": sentiment,
        "customer_ask": customer_ask.strip(),
        "why_unresolved": why_unresolved,
        "summary_bullets": summary_bullets,
        "recommended_next_step": recommended_next_step,
        "handoff_notes": handoff_notes,
        "followups": [],
        "customer_email": (customer_email or "").strip().lower(),
        "talep_turu": talep_turu,
        "talep_turu_label": talep_turu_label,
        "birim": birim,
        "birim_label": birim_label,
        "modul": modul,
        "modul_label": modul_label,
        "surec": surec,
        "surec_label": surec_label,
        "asset": str(asset_val),
        "location": str(loc_val),
        "impact": str(impact_val),
        "slots": slots_dict,
        "solution_ids": list(solution_ids or []),
        "path_label": " → ".join(
            part
            for part in (talep_turu_label, birim_label, modul_label, surec_label)
            if part
        ),
        "messages": [
            {
                "role": "user",
                "content": customer_ask.strip(),
                "at": created_at,
            }
        ],
        "resolution_summary": "",
        "resolved_at": "",
    }
    saved = save_ticket(ticket)
    try:
        from ticket_rag import invalidate_index

        invalidate_index()
    except Exception:
        pass
    return saved


def append_followup(ticket_id: str, text: str) -> dict | None:
    note = (text or "").strip()
    if not ticket_id or not note:
        return None
    tickets = load_tickets()
    updated = None
    stamp = datetime.now().isoformat(timespec="seconds")
    for ticket in tickets:
        if ticket.get("id") != ticket_id:
            continue
        followups = list(ticket.get("followups") or [])
        followups.append({"at": stamp, "text": note})
        ticket["followups"] = followups
        messages = list(ticket.get("messages") or [])
        messages.append({"role": "user", "content": note, "at": stamp})
        ticket["messages"] = messages
        existing = str(ticket.get("handoff_notes") or "").rstrip()
        ticket["handoff_notes"] = existing + f"\n\nFollow-up ({stamp}): {note}"
        updated = ticket
        break
    if updated is None:
        return None
    _rewrite(tickets)
    try:
        from ticket_rag import invalidate_index

        invalidate_index()
    except Exception:
        pass
    return updated


def update_status(
    ticket_id: str,
    status: str,
    *,
    resolution_summary: str = "",
) -> dict | None:
    allowed = {"open", "in_progress", "resolved"}
    if status not in allowed:
        raise ValueError(f"Unknown status: {status}")
    tickets = load_tickets()
    updated = None
    stamp = datetime.now().isoformat(timespec="seconds")
    for ticket in tickets:
        if ticket.get("id") == ticket_id:
            ticket["status"] = status
            if status == "resolved":
                ticket["resolved_at"] = stamp
                summary = (resolution_summary or ticket.get("recommended_next_step") or "").strip()
                if summary:
                    ticket["resolution_summary"] = summary
                    messages = list(ticket.get("messages") or [])
                    messages.append({"role": "agent", "content": summary, "at": stamp})
                    ticket["messages"] = messages
            updated = ticket
            break
    if updated is None:
        return None
    _rewrite(tickets)
    try:
        from ticket_rag import invalidate_index

        invalidate_index()
    except Exception:
        pass
    return updated


def tickets_for_customer(
    *,
    email: str = "",
    extra_ids: list[str] | None = None,
) -> list[dict]:
    email = (email or "").strip().lower()
    extra = set(extra_ids or [])
    matched: list[dict] = []
    for ticket in load_tickets():
        owner = str(ticket.get("customer_email") or "").strip().lower()
        tid = str(ticket.get("id") or "")
        if tid in extra or (email and owner == email):
            matched.append(ticket)
    return list(reversed(matched))
