"""Retrieve similar past ITSM solution records from knowledge base,
provide dynamic AI synthesis/interpretation, and track feedback & learning.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from text_norm import fold_tr

ROOT = Path(__file__).resolve().parent.parent
SOLUTIONS_PATH = ROOT / "data" / "solutions.jsonl"
SAP_SOLUTIONS_PATH = ROOT / "data" / "sap_solutions.jsonl"
FEEDBACK_PATH = ROOT / "data" / "solution_feedback.jsonl"


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def load_solutions() -> list[dict]:
    rows = _read_jsonl(SOLUTIONS_PATH) + _read_jsonl(SAP_SOLUTIONS_PATH)
    return rows


# ----------------------------------------------------------------------
# Option D: Solution Feedback Loop & Learning System
# ----------------------------------------------------------------------
def load_all_feedback() -> list[dict]:
    if not FEEDBACK_PATH.exists():
        return []
    rows: list[dict] = []
    for line in FEEDBACK_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            continue
    return rows


def record_feedback(solution_id: str, is_helpful: bool, user_text: str = "", comment: str = "") -> None:
    """Record user feedback (Helpful vs Unhelpful) to improve knowledge base learning."""
    if not solution_id:
        return
    FEEDBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "solution_id": solution_id,
        "is_helpful": bool(is_helpful),
        "user_text": user_text,
        "comment": comment,
        "created_at": datetime.now().isoformat(),
    }
    with FEEDBACK_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def get_solution_stats(solution_id: str) -> dict:
    """Calculate live success rate and total deflection counts for a solution."""
    feedbacks = [f for f in load_all_feedback() if f.get("solution_id") == solution_id]
    helpful = sum(1 for f in feedbacks if f.get("is_helpful"))
    unhelpful = sum(1 for f in feedbacks if not f.get("is_helpful"))
    total = helpful + unhelpful
    rate = round((helpful / total) * 100, 1) if total else 0.0

    if total:
        rating_display = f"%{rate:.0f} Başarı ({total} geri bildirim)"
    else:
        rating_display = "Henüz geri bildirim yok"

    return {
        "helpful": helpful,
        "unhelpful": unhelpful,
        "total_votes": total,
        "success_rate": rate,
        "rating_display": rating_display,
    }


def get_feedback_analytics() -> dict:
    """Executive summary of solution deflection and self-service performance."""
    feedbacks = load_all_feedback()
    total_feedbacks = len(feedbacks)
    helpful_n = sum(1 for f in feedbacks if f.get("is_helpful"))
    unhelpful_n = total_feedbacks - helpful_n
    
    overall_rate = round((helpful_n / total_feedbacks * 100), 1) if total_feedbacks > 0 else 0.0
    return {
        "total_feedback": total_feedbacks,
        "helpful_count": helpful_n,
        "unhelpful_count": unhelpful_n,
        "overall_success_rate": overall_rate,
    }


# ----------------------------------------------------------------------
# Solution Retrieval
# ----------------------------------------------------------------------
def _score(text: str, row: dict) -> int:
    lowered = fold_tr(text)
    keywords = [fold_tr(str(k)) for k in (row.get("keywords") or [])]
    title = fold_tr(str(row.get("title") or ""))
    surec_label = fold_tr(str(row.get("surec_label") or ""))

    score = sum(2 for kw in keywords if kw and (kw in lowered or fold_tr(kw) in lowered))
    if title and title in lowered:
        score += 4
    if surec_label and surec_label in lowered:
        score += 3
    unit = fold_tr(str(row.get("birim_label") or row.get("birim") or ""))
    if unit and unit in lowered:
        score += 1

    if "sap" in lowered and str(row.get("birim") or "") == "sap_erp":
        score += 3
    if "mm" in lowered and str(row.get("modul") or "") == "sap_mm":
        score += 4
    if any(token in lowered for token in ("karakter", "mecburi", "maximum", "max ")):
        if "karakter" in " ".join(keywords) or "field" in " ".join(keywords):
            score += 5
    return score


def find_solutions(text: str, *, birim: str = "", surec: str = "", limit: int = 2) -> list[dict]:
    all_solutions = load_solutions()
    
    # 1. Exact match by surec
    if surec:
        surec_norm = fold_tr(surec)
        exact_matches = [
            row for row in all_solutions
            if row.get("surec") == surec or fold_tr(row.get("surec", "")) == surec_norm or fold_tr(row.get("surec_label", "")) == surec_norm
        ]
        if exact_matches:
            return exact_matches[:limit]

    # 2. Ranked match by text keywords & unit
    ranked: list[tuple[int, dict]] = []
    for row in all_solutions:
        score = _score(text, row)
        if birim and str(row.get("birim") or "") == birim:
            score += 2
        if score <= 0:
            continue
        ranked.append((score, row))
        
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [row for _, row in ranked[:limit]]


# ----------------------------------------------------------------------
# Option A: Dynamic AI Solution Synthesis & Personalized Interpretation
# ----------------------------------------------------------------------
def synthesize_solution_explanation(user_text: str, row: dict) -> str:
    """Generate dynamic contextual AI guidance based on the user's specific problem and ITIL solution."""
    lowered = fold_tr(user_text)
    surec_label = row.get("surec_label", "Talep")
    birim_label = row.get("birim_label", "Destek")
    
    # Contextual insight generator
    if "siyah" in lowered or "goruntu" in lowered or "ekran" in lowered:
        context_note = "Belirttiğiniz siyah ekran/görüntü kesintisi genellikle güç besleme veya statik elektrik kaynaklıdır."
    elif "yavas" in lowered or "donuyor" in lowered or "kasiyor" in lowered:
        context_note = "Yaşadığınız yavaşlama ve donma problemi arka plan bellek taşması veya servis tıkanıklığından kaynaklanabilir."
    elif "sifre" in lowered or "kilit" in lowered or "login" in lowered:
        context_note = "Hesap kilitlenmesi veya parola unutma durumlarında kimlik doğrulama portalı üzerinden anında işlem yapabilirsiniz."
    elif "vpn" in lowered or "baglan" in lowered or "internet" in lowered or "wifi" in lowered:
        context_note = "Ağ erişim ve VPN bağlantı sorunlarında DNS önbelleği veya sertifika süresi belirleyici etkendir."
    elif "klima" in lowered or "isi" in lowered or "sicak" in lowered or "soguk" in lowered:
        context_note = "İklimlendirme ve sıcaklık arızalarında kat/bölge termostatı ve filtre kontrolü önceliklidir."
    else:
        context_note = f"İlettiğiniz **{surec_label}** konusu için kurumsal {birim_label} standart çözüm prosedürümüz aşağıdadır."

    return context_note


def format_solution(row: dict, user_text: str = "") -> str:
    title = row.get("title") or row.get("surec_label") or "Çözüm Kaydı"
    sid = row.get("id") or ""
    self_service = " · Self-Service Çözüm" if row.get("self_service_uygun_mu") else ""
    
    stats = get_solution_stats(sid)
    rating_badge = f"⭐ {stats['rating_display']}"

    # Try LLM Engine first if active (NVIDIA Nemotron)
    try:
        from llm_engine import synthesize_ai_troubleshooting
        llm_text = synthesize_ai_troubleshooting(user_text, row) if user_text else None
        if llm_text:
            return (
                f"**💡 {title} (Yapay Zeka Destekli Çözüm)**\n\n"
                f"{llm_text}\n\n"
                f"*(Kayıt No: `{sid}` · {rating_badge}{self_service})*"
            )
    except Exception:
        pass

    # Fallback to smart built-in synthesis
    steps = row.get("steps") or []
    if isinstance(steps, str):
        body = steps
    else:
        body = "\n".join(
            step if step.startswith(("1.", "2.", "3.", "4.", "5.")) else f"{i}. {step}"
            for i, step in enumerate(steps, start=1)
        )
        
    ai_insight = synthesize_solution_explanation(user_text, row)
    return (
        f"**💡 {title}**\n"
        f"*{ai_insight}*\n\n"
        f"**Önerilen Çözüm Adımları:**\n{body}\n\n"
        f"*(Kayıt No: `{sid}` · {rating_badge}{self_service})*"
    )
