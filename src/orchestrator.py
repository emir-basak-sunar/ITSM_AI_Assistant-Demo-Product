"""ITSM turn: classify, suggest KB solution, fill fields, open ticket, or queue report."""

from __future__ import annotations

from dataclasses import dataclass, field

from intents import detect_intents, looks_confirm, looks_decline
from reports import looks_report_command, queue_report_job
from rules import force_ticket
from sentiment import analyze_sentiment, looks_positive_resolution
from slots import (
    apply_answer,
    extract_slots,
    get_required_fields_for_surec,
    merge_slots,
    missing_fields,
    next_prompt,
)
from priority import infer_priority
from solutions import find_solutions, format_solution, record_feedback
from sap_router import classification_from_solution, user_refuses_clarify
from ticket_rag import find_similar_resolved_tickets, format_similar_ticket_payload
from summaries import build_manager_copy, llm_enabled
from taxonomy import classify_request, path_line
from tickets import append_followup, create_ticket, update_status


@dataclass
class TurnResult:
    reply: str
    phase: str
    last_rule_id: str | None
    ticket: dict | None = None
    debug: dict = field(default_factory=dict)
    slots: dict = field(default_factory=dict)
    classification: dict | None = None
    similar_tickets: list[dict] = field(default_factory=list)


def _urgency(sentiment: str, high_risk: bool, impact: str = "", priority: str = "") -> str:
    if high_risk or "tüm ofis" in (impact or "") or priority == "Kritik":
        return "high"
    if sentiment == "angry" or priority == "Yüksek":
        return "high"
    return "medium"


def _primary_ask(history: list[dict], text: str) -> str:
    for message in history:
        if message.get("role") == "user":
            ask = str(message.get("content") or "").strip()
            if ask:
                return ask
    return (text or "").strip()


def _merge_class(previous: dict | None, incoming: dict) -> dict:
    if incoming and not incoming.get("unclear"):
        return incoming
    if previous and not previous.get("unclear"):
        return previous
    return incoming or previous or classify_request("")


def _debug(classification: dict, sentiment: dict, action: str, extra: dict | None = None) -> dict:
    source = classification.get("source") or "none"
    if source == "model":
        confidence = float(classification.get("model_confidence") or 0.0)
    else:
        confidence = min(1.0, (classification.get("score") or 0) / 4)
    payload = {
        "category": classification.get("path_label") or "unclear",
        "confidence": confidence,
        "nlu_source": source,
        "sentiment": sentiment["label"],
        "high_risk": sentiment["high_risk"],
        "talep_turu": classification.get("talep_turu_label") or "—",
        "birim": classification.get("birim_label") or "—",
        "modul": classification.get("modul_label") or "—",
        "surec": classification.get("surec_label") or "—",
        "rule_id": classification.get("surec") or None,
        "action": action,
    }
    if extra:
        payload.update(extra)
    return payload


def _with_llm_reply(result: TurnResult, customer_text: str) -> TurnResult:
    # Solutions and opened tickets already have rich, complete formatting
    if result.phase in {"suggest_solution", "ticket_open", "report_queued"}:
        return result
    if not llm_enabled() or len((customer_text or "").strip()) < 12:
        return result
    from llm_analyze import rewrite_customer_reply

    rewritten = rewrite_customer_reply(canned_reply=result.reply)
    if rewritten:
        result.reply = rewritten
    return result


def _open_itsm_ticket(
    *,
    classification: dict,
    sentiment: dict,
    text: str,
    history: list[dict],
    slots: dict,
    why: str,
    customer_email: str,
    solution_ids: list[str],
) -> dict:
    ask = _primary_ask(history, text)
    copy = build_manager_copy(
        classification=classification,
        sentiment=sentiment["label"],
        customer_ask=ask,
        why_unresolved=why,
        high_risk=sentiment["high_risk"],
        history=history,
        latest_user=text,
        slots=slots,
        solution_ids=solution_ids,
    )
    priority = str(classification.get("priority") or infer_priority(
        ask,
        talep_turu=str(classification.get("talep_turu_label") or ""),
        high_risk=sentiment["high_risk"],
        sentiment=sentiment["label"],
    ))
    return create_ticket(
        urgency=_urgency(
            sentiment["label"],
            sentiment["high_risk"],
            slots.get("impact", ""),
            priority=priority,
        ),
        priority=priority,
        customer_ask=ask,
        why_unresolved=why,
        summary_bullets=copy["summary_bullets"],
        recommended_next_step=copy["recommended_next_step"],
        handoff_notes=copy["handoff_notes"],
        sentiment=sentiment["label"],
        customer_email=customer_email,
        talep_turu=str(classification.get("talep_turu") or ""),
        talep_turu_label=str(classification.get("talep_turu_label") or ""),
        birim=str(classification.get("birim") or ""),
        birim_label=str(classification.get("birim_label") or ""),
        modul=str(classification.get("modul") or ""),
        modul_label=str(classification.get("modul_label") or ""),
        surec=str(classification.get("surec") or ""),
        surec_label=str(classification.get("surec_label") or ""),
        slots=slots,
        solution_ids=solution_ids,
    )


def _ticket_reply(ticket: dict) -> str:
    path = ticket.get("path_label") or "sınıflandırma"
    slots = ticket.get("slots") or {}
    
    fields_repr = []
    for k, v in slots.items():
        if v:
            clean_k = k.replace("_", " ").title()
            fields_repr.append(f"{clean_k}: {v}")
            
    fields_line = " · ".join(fields_repr) if fields_repr else "Gerekli alanlar kaydedildi."
    
    return (
        f"✅ **Talebiniz Kaydedildi:** {ticket['id']}\n\n"
        f"📌 **Sınıf:** {path}\n"
        f"📋 **Kayıt Bilgileri:** {fields_line}\n"
        f"🏢 **Atanan Kuyruk:** {ticket.get('birim_label') or 'İlgili birim'} "
        f"(Öncelik: {ticket.get('priority') or ticket.get('urgency', 'medium')})"
    )


def _rag_answer(user_text: str, similar: list[dict], hits: list[dict]) -> str | None:
    kb = hits[0] if hits else None
    try:
        from llm_engine import fallback_answer_from_resolved_tickets, synthesize_from_resolved_tickets

        llm_text = synthesize_from_resolved_tickets(user_text, similar, kb_solution=kb)
        if llm_text:
            return llm_text
        return fallback_answer_from_resolved_tickets(user_text, similar) or None
    except Exception:
        return None


def _suggest_reply(
    classification: dict,
    hits: list[dict],
    user_text: str = "",
    similar_tickets: list[dict] | None = None,
) -> str:
    path = path_line(classification)
    blocks = [f"🔍 **Talebinizi şöyle sınıflandırdım:** {path}"]
    similar = similar_tickets or []

    if similar:
        top = similar[0]
        ticket = top.get("ticket") if isinstance(top.get("ticket"), dict) else top
        pct = top.get("similarity_pct") or round(float(top.get("score", 0)) * 100)
        blocks.append(
            f"📎 **Benzer çözülmüş kayıt:** `{ticket.get('id', '—')}` "
            f"(%{pct} benzerlik) — mesajlaşma geçmişi sohbet panelinde gösteriliyor."
        )
        rag_text = _rag_answer(user_text, similar, hits)
        if rag_text:
            blocks.append(f"**🧠 Geçmiş kayıtlara dayalı öneri:**\n\n{rag_text}")
        elif hits:
            for row in hits:
                blocks.append(format_solution(row, user_text=user_text))
    elif hits:
        for row in hits:
            blocks.append(format_solution(row, user_text=user_text))
    else:
        blocks.append(
            "Bu süreç için hazır bir self-service çözüm kaydı bulunamadı. İlgili birime bilet oluşturmamı ister misiniz?"
        )
    return "\n\n".join(blocks)


def _collect_or_open(
    *,
    text: str,
    history: list[dict],
    classification: dict,
    sentiment: dict,
    slots: dict,
    customer_email: str,
    solution_ids: list[str],
    why: str,
    intro: str = "",
) -> TurnResult:
    surec_key = str(classification.get("surec") or "")
    req_fields = get_required_fields_for_surec(surec_key)
    
    merged = merge_slots(slots, extract_slots(text, req_fields), req_fields)
    prompt = next_prompt(merged, req_fields, surec_key)
    
    if prompt:
        debug = _debug(classification, sentiment, "collect_fields")
        lead = intro.strip() + "\n\n" if intro.strip() else ""
        return TurnResult(
            reply=lead + prompt,
            phase="collect_fields",
            last_rule_id=None,
            debug=debug,
            slots=merged,
            classification=classification,
        )

    ticket = _open_itsm_ticket(
        classification=classification,
        sentiment=sentiment,
        text=text,
        history=history,
        slots=merged,
        why=why,
        customer_email=customer_email,
        solution_ids=solution_ids,
    )
    debug = _debug(
        classification,
        sentiment,
        "ticket_open",
        {"ticket_id": ticket["id"], "urgency": ticket["urgency"]},
    )
    return TurnResult(
        reply=_ticket_reply(ticket),
        phase="ticket_open",
        last_rule_id=None,
        ticket=ticket,
        debug=debug,
        slots=merged,
        classification=classification,
    )


def handle_turn(
    text: str,
    *,
    history: list[dict] | None = None,
    phase: str = "open",
    last_rule_id: str | None = None,
    last_ticket_id: str | None = None,
    slots: dict | None = None,
    classification: dict | None = None,
    customer_email: str = "",
) -> TurnResult:
    history = history or []
    slots = slots or {}
    owner = (customer_email or "").strip().lower()
    sentiment = analyze_sentiment(text)
    if force_ticket(text):
        sentiment["high_risk"] = True
    intents = detect_intents(text)
    prior = " ".join(
        str(message.get("content") or "")
        for message in history
        if message.get("role") == "user"
    )
    full_context = " ".join(part for part in (prior, text) if part)
    incoming = classify_request(full_context)
    if phase == "collect_fields" and classification and not classification.get("unclear"):
        classed = classification
    else:
        classed = _merge_class(classification, incoming)
    if classed and not classed.get("unclear"):
        classed = dict(classed)
        classed["priority"] = infer_priority(
            " ".join(part for part in (prior, text) if part),
            talep_turu=str(classed.get("talep_turu_label") or ""),
            high_risk=sentiment["high_risk"],
            sentiment=sentiment["label"],
        )
    
    surec_key = str(classed.get("surec") or "")
    req_fields = get_required_fields_for_surec(surec_key)
    current_slots = merge_slots(slots, None, req_fields)
    solution_ids = [last_rule_id] if last_rule_id and str(last_rule_id).startswith("S-") else []

    if looks_report_command(text):
        job = queue_report_job(
            command=text,
            birim=str(classed.get("birim") or ""),
            requested_by=owner,
        )
        debug = _debug(classed, sentiment, "report_queued", {"job_id": job["id"]})
        return _with_llm_reply(
            TurnResult(
                reply=(
                    f"📊 **Rapor komutunuz kuyruğa alındı:** `{job['id']}`\n\n"
                    "Günlük analitik JOB (`python src\\daily_jobs.py`) çalıştığında özet rapor hazırlanıp ilgili birimlere ulaştırılacaktır."
                ),
                phase=phase if phase != "open" else "open",
                last_rule_id=last_rule_id,
                debug=debug,
                slots=current_slots,
                classification=classed,
            ),
            text,
        )

    if phase == "ticket_open" and looks_positive_resolution(text) and not intents["still_unresolved"]:
        if last_ticket_id:
            update_status(last_ticket_id, "resolved")
        debug = _debug(classed, sentiment, "resolved")
        return _with_llm_reply(
            TurnResult(
                reply="Talebiniz başarıyla kapatıldı. Başka bir ITSM talebiniz olursa yardımcı olmaktan memnuniyet duyarım.",
                phase="open",
                last_rule_id=None,
                debug=debug,
                slots=merge_slots(None, None, req_fields),
                classification=None,
            ),
            text,
        )

    if phase == "ticket_open":
        ticket = append_followup(last_ticket_id or "", text)
        debug = _debug(classed, sentiment, "ticket_followup")
        tid = last_ticket_id or (ticket or {}).get("id") or ""
        extra = " İkinci bir kayıt açılmadı; ek açıklamanız mevcut talebe işlendi." if intents["open_ticket"] else ""
        return _with_llm_reply(
            TurnResult(
                reply=f"Açık bir kaydınız bulunmaktadır ({tid}). Bu detayı takip notlarına ekledim.{extra}",
                phase="ticket_open",
                last_rule_id=last_rule_id,
                ticket=ticket,
                debug=debug,
                slots=current_slots,
                classification=classed,
            ),
            text,
        )

    if phase == "suggest_solution":
        if looks_positive_resolution(text) and not intents["still_unresolved"] and not intents["open_ticket"]:
            if last_rule_id:
                record_feedback(last_rule_id, is_helpful=True, user_text=text)
            debug = _debug(classed, sentiment, "self_resolved")
            return _with_llm_reply(
                TurnResult(
                    reply="Harika, sorununuzun çözüldüğüne sevindim! Bilet açılmadan self-service olarak tamamlandı. İyi çalışmalar dilerim.",
                    phase="open",
                    last_rule_id=None,
                    debug=debug,
                    slots=merge_slots(None, None, req_fields),
                    classification=None,
                ),
                text,
            )
        if looks_decline(text) and not intents["open_ticket"]:
            debug = _debug(classed, sentiment, "solution_declined")
            return _with_llm_reply(
                TurnResult(
                    reply="Anlaşıldı, kayıt açmadım. İhtiyaç duyduğunuzda yeni bir talep iletebilirsiniz.",
                    phase="open",
                    last_rule_id=None,
                    debug=debug,
                    slots=merge_slots(None, None, req_fields),
                    classification=None,
                ),
                text,
            )
        if intents["open_ticket"] or intents["still_unresolved"] or looks_confirm(text):
            if last_rule_id and intents["still_unresolved"]:
                record_feedback(last_rule_id, is_helpful=False, user_text=text)
            result = _collect_or_open(
                text=text,
                history=history,
                classification=classed,
                sentiment=sentiment,
                slots=current_slots,
                customer_email=owner,
                solution_ids=solution_ids,
                why="Kullanıcı çözüm önerisinden sonra ticket talep etti veya sorun devam etti.",
            )
            return _with_llm_reply(result, text)
        debug = _debug(classed, sentiment, "suggest_wait")
        return _with_llm_reply(
            TurnResult(
                reply="Önerilen adımlar işe yaradıysa belirtebilirsiniz. Destek ekibine kayıt açılması için **“talep aç”** demeniz yeterlidir.",
                phase="suggest_solution",
                last_rule_id=last_rule_id,
                debug=debug,
                slots=current_slots,
                classification=classed,
            ),
            text,
        )

    if phase == "collect_fields":
        missing = missing_fields(current_slots, req_fields)
        field_to_fill = missing[0] if missing else req_fields[0]
        current_slots = apply_answer(current_slots, field_to_fill, text, req_fields)
        result = _collect_or_open(
            text=text,
            history=history,
            classification=classed,
            sentiment=sentiment,
            slots=current_slots,
            customer_email=owner,
            solution_ids=solution_ids,
            why="Zorunlu alanlar tamamlandı; bilet oluşturuldu.",
        )
        return _with_llm_reply(result, text)

    if phase == "clarify":
        if incoming.get("unclear") and not intents["open_ticket"] and not user_refuses_clarify(text):
            probe_hits = find_solutions(
                full_context,
                birim=str(classed.get("birim") or ""),
                surec=str(classed.get("surec") or ""),
            )
            if probe_hits:
                classed = classification_from_solution(probe_hits[0])
                surec_key = str(classed.get("surec") or "")
                req_fields = get_required_fields_for_surec(surec_key)
            else:
                debug = _debug(classed, sentiment, "clarify")
                hint = str(classed.get("clarify_hint") or "").strip()
                if not hint:
                    hint = "Size hızlıca yardımcı olabilmem için yaşadığınız sorunu veya talebinizi biraz daha detaylandırabilir misiniz? (Örn: 'Laptop açılmıyor', 'VPN bağlanmıyor', 'SAP MM malzeme hatası', 'İzin talebi' vb.)"
                reply_text = hint if hint.startswith("Size") else f"Talebinizi tam netleştiremedim. {hint}"
                return _with_llm_reply(
                    TurnResult(
                        reply=reply_text,
                        phase="clarify",
                        last_rule_id=None,
                        debug=debug,
                        slots=merge_slots(current_slots, extract_slots(text, req_fields), req_fields),
                        classification=classed,
                    ),
                    text,
                )
        classed = _merge_class(classed, incoming)
        surec_key = str(classed.get("surec") or "")
        req_fields = get_required_fields_for_surec(surec_key)
        current_slots = merge_slots(current_slots, None, req_fields)

    # New / clarified request
    current_slots = merge_slots(current_slots, extract_slots(text, req_fields), req_fields)
    if classed.get("unclear") and not intents["open_ticket"]:
        probe_hits = find_solutions(full_context)
        if probe_hits:
            classed = classification_from_solution(probe_hits[0])
            surec_key = str(classed.get("surec") or "")
            req_fields = get_required_fields_for_surec(surec_key)
        elif not user_refuses_clarify(text):
            debug = _debug(classed, sentiment, "clarify")
            hint = str(classed.get("clarify_hint") or "").strip()
            if not hint:
                hint = "Size hızlıca yardımcı olabilmem için yaşadığınız sorunu veya talebinizi biraz daha detaylandırabilir misiniz? (Örn: 'Laptop açılmıyor', 'VPN bağlanmıyor', 'SAP MM malzeme hatası', 'İzin talebi' vb.)"
            reply_text = hint if hint.startswith("Size") else f"Talebinizi daha doğru yönlendirebilmem için bir sorum var: {hint}"
            return _with_llm_reply(
                TurnResult(
                    reply=reply_text,
                    phase="clarify",
                    last_rule_id=None,
                    debug=debug,
                    slots=current_slots,
                    classification=classed,
                ),
                text,
            )

    hits = []
    similar_raw: list[dict] = []
    similar_payload: list[dict] = []
    if not sentiment["high_risk"]:
        hits = find_solutions(
            full_context,
            birim=str(classed.get("birim") or ""),
            surec=surec_key,
        )
        similar_raw = find_similar_resolved_tickets(
            full_context,
            surec=surec_key,
            birim=str(classed.get("birim") or ""),
            limit=2,
        )
        similar_payload = [format_similar_ticket_payload(match) for match in similar_raw]
    solution_ids = [str(h.get("id")) for h in hits if h.get("id")]
    want_ticket = intents["open_ticket"] or sentiment["high_risk"]

    has_self_service = bool(hits or similar_raw)
    if has_self_service and not want_ticket:
        sid = solution_ids[0] if solution_ids else None
        debug = _debug(
            classed,
            sentiment,
            "suggest_solution",
            {
                "solution_id": sid,
                "similar_ticket_id": (similar_payload[0] or {}).get("id") if similar_payload else None,
            },
        )
        return _with_llm_reply(
            TurnResult(
                reply=_suggest_reply(classed, hits, user_text=text, similar_tickets=similar_raw),
                phase="suggest_solution",
                last_rule_id=sid,
                debug=debug,
                slots=current_slots,
                classification=classed,
                similar_tickets=similar_payload,
            ),
            text,
        )

    intro = ""
    if hits or similar_raw:
        intro = _suggest_reply(classed, hits, user_text=text, similar_tickets=similar_raw)
    why = (
        "Yüksek risk/öncelik; self-servis atlandı."
        if sentiment["high_risk"]
        else "Hazır çözüm yok veya kullanıcı doğrudan kayıt istedi."
    )
    result = _collect_or_open(
        text=text,
        history=history,
        classification=classed,
        sentiment=sentiment,
        slots=current_slots,
        customer_email=owner,
        solution_ids=solution_ids,
        why=why,
        intro=intro,
    )
    if similar_payload:
        result.similar_tickets = similar_payload
    return _with_llm_reply(result, text)
