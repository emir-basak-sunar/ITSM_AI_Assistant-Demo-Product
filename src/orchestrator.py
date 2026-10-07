"""ITSM turn: classify, suggest KB solution, fill fields, open ticket, or queue report."""

from __future__ import annotations

from dataclasses import dataclass, field

from dialogue import (
    looks_like_followup_question,
    looks_like_slot_reply,
    looks_like_troubleshooting_continue,
    resolve_classification,
    same_unit,
)
from intents import detect_intents, looks_confirm, looks_decline, rejects_classification
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


def _unclear_classification(hint: str = "") -> dict:
    default_hint = (
        "Asıl sorununuzu bir cümleyle yazın. (Örn. PC arızası, yazılım hatası, SAP, yazıcı)"
    )
    return {
        "unclear": True,
        "score": 0,
        "hits": [],
        "source": "user_correction",
        "model_confidence": 0.0,
        "talep_turu": "",
        "talep_turu_label": "",
        "birim": "",
        "birim_label": "",
        "modul": "",
        "modul_label": "",
        "surec": "",
        "surec_label": "",
        "path_label": "",
        "clarify_hint": hint or default_hint,
    }


def _merge_class(previous: dict | None, incoming: dict) -> dict:
    if incoming and not incoming.get("unclear"):
        return incoming
    if previous and not previous.get("unclear"):
        return previous
    return incoming or previous or classify_request("")


def _debug(classification: dict, sentiment: dict, action: str, extra: dict | None = None) -> dict:
    source = classification.get("source") or "none"
    if source in {"bert", "sklearn", "model"}:
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


def _conversation_blob(history: list[dict] | None, text: str) -> str:
    parts: list[str] = []
    for message in (history or [])[-8:]:
        content = str(message.get("content") or "").strip()
        if content:
            parts.append(content)
    if text.strip():
        parts.append(text.strip())
    return "\n".join(parts)


def _knowledge_answer(user_text: str, classification: dict | None = None) -> str | None:
    """RAG boşsa NVIDIA API kendi bilgisiyle cevap üretir."""
    try:
        from llm_engine import answer_from_model_knowledge, is_llm_active

        if not is_llm_active():
            return None
        text = answer_from_model_knowledge(user_text, classification or {})
        if not text:
            return None
        return f"**LLM (Nemotron · kendi bilgisi):**\n\n{text}"
    except Exception as exc:
        print(f"[llm-knowledge] {exc}")
        return None


def _rag_answer(
    user_text: str,
    similar: list[dict],
    hits: list[dict],
    *,
    history: list[dict] | None = None,
    followup: bool = False,
    classification: dict | None = None,
) -> str | None:
    """BERT süreciyle süzülmüş Chroma kayıtları + Nemotron (yoksa şablon)."""
    kb = hits[0] if hits else None
    try:
        from llm_engine import (
            fallback_answer_from_resolved_tickets,
            is_llm_active,
            synthesize_followup_troubleshooting,
            synthesize_from_resolved_tickets,
        )

        if followup and is_llm_active():
            llm_text = synthesize_followup_troubleshooting(
                user_text,
                history or [],
                similar_tickets=similar,
                kb_solution=kb,
                classification=classification,
            )
            if llm_text:
                return f"**Takip (Nemotron):**\n\n{llm_text}"
        if similar and is_llm_active():
            llm_text = synthesize_from_resolved_tickets(
                user_text, similar, kb_solution=kb
            )
            if llm_text:
                return f"**RAG (Nemotron · çözülmüş kayıtlar):**\n\n{llm_text}"
        if followup:
            knowledge = _knowledge_answer(user_text, classification)
            if knowledge:
                return knowledge
        if similar:
            return fallback_answer_from_resolved_tickets(user_text, similar) or None
        return None
    except Exception as exc:
        print(f"[rag] {exc}")
        return None


def _suggest_reply(
    classification: dict,
    hits: list[dict],
    user_text: str = "",
    similar_tickets: list[dict] | None = None,
    *,
    history: list[dict] | None = None,
    followup: bool = False,
) -> str:
    path = path_line(classification)
    source = str(classification.get("source") or "")
    conf = float(classification.get("model_confidence") or 0.0)
    if followup:
        header = (
            f"🔄 **Aynı olaydayız:** {path}  \n"
            "Önceki çözümü ve yeni itirazınızı birlikte ele alıyorum."
        )
    elif source in {"bert", "sklearn", "model"} and conf:
        header = (
            f"🔍 **BERT sınıflandırması:** {path}  \n"
            f"*(Süreç Chroma filtresi olarak kullanıldı.)*"
        )
    else:
        header = f"🔍 **Talebinizi şöyle sınıflandırdım:** {path}"
    blocks = [header]
    similar = similar_tickets or []

    rag_text = _rag_answer(
        user_text,
        similar,
        hits,
        history=history,
        followup=followup,
        classification=classification,
    )
    if rag_text:
        blocks.append(rag_text)
    else:
        knowledge = _knowledge_answer(user_text, classification)
        if knowledge:
            blocks.append(knowledge)
        elif hits:
            for row in hits:
                blocks.append(format_solution(row, user_text=user_text))
        else:
            blocks.append(
                "Bu süreç için hazır çözüm veya benzer kayıt bulunamadı. "
                "İlgili birime bilet oluşturmamı ister misiniz?"
            )

    if similar and not followup:
        top = similar[0]
        ticket = top.get("ticket") if isinstance(top.get("ticket"), dict) else top
        pct = top.get("similarity_pct") or round(float(top.get("score", 0)) * 100)
        blocks.append(
            f"📎 **Kaynak kayıt:** `{ticket.get('id', '—')}` (%{pct} benzerlik)"
        )
    return "\n\n".join(blocks)


def _continue_solution_turn(
    *,
    text: str,
    history: list[dict],
    classed: dict,
    sentiment: dict,
    current_slots: dict,
    surec_key: str,
    last_rule_id: str | None,
) -> TurnResult:
    query = _conversation_blob(history, text)
    hits = find_solutions(
        query,
        birim=str(classed.get("birim") or ""),
        surec=surec_key,
    )
    similar_raw = find_similar_resolved_tickets(
        query,
        surec=surec_key,
        birim=str(classed.get("birim") or ""),
        limit=2,
    )
    similar_payload = [format_similar_ticket_payload(match) for match in similar_raw]
    solution_ids = [str(h.get("id")) for h in hits if h.get("id")]
    sid = solution_ids[0] if solution_ids else last_rule_id
    debug = _debug(classed, sentiment, "suggest_solution", {"followup": True})
    return TurnResult(
        reply=_suggest_reply(
            classed,
            hits,
            user_text=text,
            similar_tickets=similar_raw,
            history=history,
            followup=True,
        ),
        phase="suggest_solution",
        last_rule_id=sid,
        debug=debug,
        slots=current_slots,
        classification=classed,
        similar_tickets=similar_payload,
    )


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
    force_open: bool = False,
) -> TurnResult:
    surec_key = str(classification.get("surec") or "")
    req_fields = get_required_fields_for_surec(surec_key)

    ask = _primary_ask(history, text)
    merged = merge_slots(slots, extract_slots(ask, req_fields), req_fields)
    merged = merge_slots(merged, extract_slots(text, req_fields), req_fields)
    prompt = next_prompt(merged, req_fields, surec_key)

    if prompt and not force_open:
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
    incoming_full = classify_request(full_context)
    incoming_turn = classify_request(text)
    user_rejects = rejects_classification(text, classification)
    classed = resolve_classification(
        text=text,
        phase=phase,
        previous=classification,
        incoming_full=incoming_full,
        incoming_turn=incoming_turn,
        user_rejects=user_rejects,
    )
    if (
        phase == "collect_fields"
        and classification
        and not classification.get("unclear")
        and not user_rejects
        and not looks_like_followup_question(text)
        and not looks_like_slot_reply(text)
    ):
        classed = classification
    if (
        looks_like_followup_question(text)
        and classification
        and not classification.get("unclear")
        and incoming_turn
        and not incoming_turn.get("unclear")
        and not same_unit(classification, incoming_turn)
    ):
        classed = incoming_turn
    if classed and not classed.get("unclear"):
        classed = dict(classed)
        classed["priority"] = infer_priority(
            " ".join(part for part in (prior, text) if part),
            talep_turu=str(classed.get("talep_turu_label") or ""),
            high_risk=sentiment["high_risk"],
            sentiment=sentiment["label"],
        )
    
    prev_surec = str((classification or {}).get("surec") or "")
    surec_key = str(classed.get("surec") or "")
    if prev_surec and prev_surec != surec_key:
        slots = {}
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
        if looks_like_slot_reply(text):
            extracted = extract_slots(text, req_fields)
            if not any(str(v).strip() for v in extracted.values()):
                missing = missing_fields(current_slots, req_fields)
                if missing:
                    current_slots = apply_answer(current_slots, missing[0], text, req_fields)
            result = _collect_or_open(
                text=text,
                history=history,
                classification=classed,
                sentiment=sentiment,
                slots=current_slots,
                customer_email=owner,
                solution_ids=solution_ids,
                why="Kullanıcı çözüm sonrası eksik alanları dolduruyor.",
            )
            return _with_llm_reply(result, text)
        if looks_like_followup_question(text) or looks_like_troubleshooting_continue(text):
            return _with_llm_reply(
                _continue_solution_turn(
                    text=text,
                    history=history,
                    classed=classed,
                    sentiment=sentiment,
                    current_slots=current_slots,
                    surec_key=surec_key,
                    last_rule_id=last_rule_id,
                ),
                text,
            )
        debug = _debug(classed, sentiment, "suggest_wait")
        return _with_llm_reply(
            TurnResult(
                reply=(
                    "Aynı kayıt üzerindeyiz. Adımlar işe yaradıysa yazın; "
                    "kayıt açmamı isterseniz **talep aç** demeniz yeterli. "
                    "Farklı bir konuysa kısaca yeni talebinizi yazın."
                ),
                phase="suggest_solution",
                last_rule_id=last_rule_id,
                debug=debug,
                slots=current_slots,
                classification=classed,
            ),
            text,
        )

    if phase == "collect_fields":
        if user_rejects:
            debug = _debug(classed, sentiment, "clarify")
            return _with_llm_reply(
                TurnResult(
                    reply=(
                        "Anladım, önceki yönlendirme yanlıştı. **Asıl sorununuzu** kısaca yazar mısınız?\n\n"
                        "Kayıt açmamı isterseniz **talep aç** demeniz yeterli."
                    ),
                    phase="clarify",
                    last_rule_id=None,
                    debug=debug,
                    slots={},
                    classification=_unclear_classification(),
                ),
                text,
            )

        if intents["open_ticket"]:
            result = _collect_or_open(
                text=text,
                history=history,
                classification=classed,
                sentiment=sentiment,
                slots=current_slots,
                customer_email=owner,
                solution_ids=solution_ids,
                why="Kullanıcı alan toplama sırasında kayıt açmayı talep etti.",
                force_open=True,
            )
            return _with_llm_reply(result, text)

        missing = missing_fields(current_slots, req_fields)
        field_to_fill = missing[0] if missing else req_fields[0]
        if not rejects_classification(text, classification):
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
        if user_rejects:
            debug = _debug(classed, sentiment, "clarify")
            return _with_llm_reply(
                TurnResult(
                    reply=(
                        "Tamam, önceki sınıflandırmayı iptal ettim. "
                        "**Gerçek sorununuzu** bir cümleyle yazar mısınız?"
                    ),
                    phase="clarify",
                    last_rule_id=None,
                    debug=debug,
                    slots={},
                    classification=_unclear_classification(),
                ),
                text,
            )

        if incoming.get("unclear") and not intents["open_ticket"] and not user_refuses_clarify(text):
            probe_hits = find_solutions(
                full_context,
                birim=str(classed.get("birim") or ""),
                surec=str(classed.get("surec") or ""),
            )
            similar_probe = find_similar_resolved_tickets(full_context, limit=2)
            if probe_hits:
                classed = classification_from_solution(probe_hits[0])
                surec_key = str(classed.get("surec") or "")
                req_fields = get_required_fields_for_surec(surec_key)
            elif similar_probe:
                ticket = similar_probe[0].get("ticket") if isinstance(similar_probe[0], dict) else {}
                if not isinstance(ticket, dict):
                    ticket = similar_probe[0]
                classed = classification_from_solution(ticket)
                surec_key = str(classed.get("surec") or "")
                req_fields = get_required_fields_for_surec(surec_key)
            else:
                knowledge = _knowledge_answer(text, incoming)
                if knowledge:
                    debug = _debug(classed, sentiment, "suggest_solution", {"llm_knowledge": True})
                    return TurnResult(
                        reply=knowledge,
                        phase="suggest_solution",
                        last_rule_id=None,
                        debug=debug,
                        slots=merge_slots(current_slots, extract_slots(text, req_fields), req_fields),
                        classification=classed,
                    )
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
        similar_probe = find_similar_resolved_tickets(full_context, limit=2)
        if probe_hits:
            classed = classification_from_solution(probe_hits[0])
            surec_key = str(classed.get("surec") or "")
            req_fields = get_required_fields_for_surec(surec_key)
        elif similar_probe:
            ticket = similar_probe[0].get("ticket") if isinstance(similar_probe[0], dict) else {}
            if not isinstance(ticket, dict):
                ticket = similar_probe[0]
            classed = classification_from_solution(ticket)
            surec_key = str(classed.get("surec") or "")
            req_fields = get_required_fields_for_surec(surec_key)
        elif not user_refuses_clarify(text):
            knowledge = _knowledge_answer(text, classed)
            if knowledge:
                debug = _debug(classed, sentiment, "suggest_solution", {"llm_knowledge": True})
                return TurnResult(
                    reply=knowledge,
                    phase="suggest_solution",
                    last_rule_id=None,
                    debug=debug,
                    slots=current_slots,
                    classification=classed,
                )
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
