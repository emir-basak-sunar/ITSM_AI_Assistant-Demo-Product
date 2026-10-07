"""LLM Integration Engine — NVIDIA Nemotron via OpenAI-compatible API."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

SRC_DIR = Path(__file__).resolve().parent
ROOT_DIR = SRC_DIR.parent

load_dotenv(SRC_DIR / ".env")
load_dotenv(ROOT_DIR / ".env")
load_dotenv()

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "").strip()
NVIDIA_BASE_URL = os.getenv(
    "NVIDIA_BASE_URL",
    "https://integrate.api.nvidia.com/v1",
).strip()
NVIDIA_MODEL = os.getenv(
    "NVIDIA_MODEL",
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
).strip()
USE_LLM = os.getenv("ASSISTANT_USE_LLM", "1").strip().lower() in {"1", "true", "yes"}


@lru_cache(maxsize=1)
def _client() -> OpenAI | None:
    if not NVIDIA_API_KEY:
        return None
    return OpenAI(base_url=NVIDIA_BASE_URL, api_key=NVIDIA_API_KEY)


def is_llm_active() -> bool:
    """Return True if NVIDIA API key is configured and LLM is enabled."""
    if not USE_LLM:
        return False
    return bool(NVIDIA_API_KEY)


def llm_provider_label() -> str:
    if is_llm_active():
        return "NVIDIA Nemotron"
    return "Hibrit RAG"


def call_nvidia(
    prompt: str,
    system_prompt: str = "",
    *,
    timeout: float = 45.0,
    temperature: float = 0.5,
    max_tokens: int = 1024,
) -> str | None:
    """Call NVIDIA integrate API (OpenAI-compatible chat completions)."""
    client = _client()
    if client is None:
        return None

    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    try:
        completion = client.chat.completions.create(
            model=NVIDIA_MODEL,
            messages=messages,
            temperature=temperature,
            top_p=1,
            max_tokens=max_tokens,
            stream=False,
            timeout=timeout,
        )
        content = completion.choices[0].message.content
        if content:
            return content.strip()
    except Exception as exc:
        print(f"[NVIDIA API Warning] {exc}")
    return None


def generate_llm_response(
    prompt: str,
    system_prompt: str = "",
    *,
    timeout: float = 70.0,
    max_tokens: int = 1024,
) -> str | None:
    """Primary LLM caller — NVIDIA Nemotron."""
    return call_nvidia(
        prompt,
        system_prompt,
        timeout=timeout,
        max_tokens=max_tokens,
    )


def synthesize_ai_troubleshooting(user_text: str, solution_row: dict) -> str | None:
    """Generate a problem-specific 3-step troubleshooting guide."""
    if not is_llm_active():
        return None

    title = solution_row.get("title") or solution_row.get("surec_label") or "Kurumsal Çözüm"
    unit = solution_row.get("birim_label", "Bilgi Teknolojileri")

    sys_prompt = (
        "Sen kurumsal bir IT Servis Masası ve Teknik Destek Yapay Zeka Uzmanısın. "
        "Kullanıcının ilettiği spesifik sorunu derinlemesine anla ve o probleme odaklanan "
        "tam ve eksiksiz 3 pratik adımlık çözüm rehberini üret. "
        "KURALLAR:\n"
        "1. Girişte 1-2 cümleyle kullanıcıyla empati kur ve sorunu anladığını belirt.\n"
        "2. Tam 3 adet numaralandırılmış (1., 2., 3.) somut adım yaz.\n"
        "3. Cevabın sonunu asla yarım bırakma; 3 adımı da eksiksiz tamamla.\n"
        "4. En sona 'Bu adımlar sorununuzu çözdü mü? Çözülmediyse talep aç diyerek kayıt oluşturabilirsiniz.' cümlesini ekle.\n"
        "5. Türkçe yaz ve markdown formatı kullan."
    )

    prompt = f"""
Kullanıcının İlettiği Sorun:
"{user_text}"

İlgili Süreç:
{title} ({unit})

Lütfen yukarıdaki problemi çözmek için 3 adımlık eksiksiz, net ve yarım kalmayan bir çözüm rehberi yaz.
""".strip()

    return generate_llm_response(prompt, system_prompt=sys_prompt)


def synthesize_from_resolved_tickets(
    user_text: str,
    similar_tickets: list[dict],
    kb_solution: dict | None = None,
) -> str | None:
    """Generate guidance using similar resolved ticket conversations (RAG)."""
    if not similar_tickets:
        return None

    context_blocks: list[str] = []
    for idx, payload in enumerate(similar_tickets[:2], start=1):
        ticket = payload.get("ticket") if isinstance(payload.get("ticket"), dict) else payload
        messages = payload.get("messages") or ticket.get("messages") or []
        thread = "\n".join(
            f"  - {item.get('role', 'user')}: {item.get('content', '')}"
            for item in messages
            if str(item.get("content") or "").strip()
        )
        context_blocks.append(
            f"Benzer Çözülmüş Kayıt #{idx} ({ticket.get('id', '—')}):\n"
            f"Sorun: {ticket.get('customer_ask', '')}\n"
            f"Çözüm: {ticket.get('resolution_summary') or ticket.get('recommended_next_step', '')}\n"
            f"Mesajlaşma:\n{thread}"
        )

    kb_hint = ""
    if kb_solution:
        steps = kb_solution.get("steps") or []
        if isinstance(steps, list):
            kb_hint = "\n".join(f"- {step}" for step in steps[:5])
        else:
            kb_hint = str(steps)

    sys_prompt = (
        "Sen kurumsal ITSM L1 destek asistanısın. BERT ile seçilen süreçteki "
        "benzer çözülmüş kayıtlardan RAG yaparsın.\n"
        "KURALLAR:\n"
        "1. Yalnızca verilen kayıtlardaki çözümü uyarla; uydurma.\n"
        "2. 1-2 cümle empati ve hangi kayıt id'sine dayandığını yaz.\n"
        "3. Tam 3 numaralandırılmış adım yaz.\n"
        "4. Son cümle: 'Bu adımlar işe yaramazsa talep aç diyerek kayıt oluşturabilirsiniz.'\n"
        "5. Türkçe ve markdown kullan."
    )

    prompt = f"""
Kullanıcının yeni sorunu:
"{user_text}"

Benzer çözülmüş kayıtlar:
{chr(10).join(context_blocks)}

Ek bilgi bankası adımları:
{kb_hint or "—"}

Lütfen geçmiş kayıtlardan yararlanarak 3 adımlık çözüm öner.
""".strip()

    return generate_llm_response(prompt, system_prompt=sys_prompt)


def synthesize_followup_troubleshooting(
    user_text: str,
    history: list[dict],
    similar_tickets: list[dict] | None = None,
    kb_solution: dict | None = None,
    classification: dict | None = None,
) -> str | None:
    """Continue the same incident: keep prior diagnosis, answer the user's objection."""
    if not is_llm_active():
        return None

    thread_lines: list[str] = []
    for item in (history or [])[-8:]:
        role = str(item.get("role") or "user")
        content = str(item.get("content") or "").strip()
        if content:
            thread_lines.append(f"{role}: {content}")
    thread_lines.append(f"user: {user_text}")

    context_blocks: list[str] = []
    for idx, payload in enumerate((similar_tickets or [])[:2], start=1):
        ticket = payload.get("ticket") if isinstance(payload.get("ticket"), dict) else payload
        context_blocks.append(
            f"Benzer kayıt #{idx} ({ticket.get('id', '—')}):\n"
            f"Sorun: {ticket.get('customer_ask', '')}\n"
            f"Çözüm: {ticket.get('resolution_summary') or ticket.get('recommended_next_step', '')}"
        )

    kb_hint = ""
    if kb_solution:
        steps = kb_solution.get("steps") or []
        kb_hint = "\n".join(f"- {step}" for step in steps[:5]) if isinstance(steps, list) else str(steps)

    classed = classification or {}
    path = str(classed.get("path_label") or "")
    sap = str(classed.get("birim") or "") == "sap_erp"
    sap_extra = (
        "SAP OB52'de dönem şirket kodu + hesap türü (A/D/K/M/S/+) bazında açılır; "
        "yalnızca şirket kodunu açmak yetmeyebilir. FB50 genelde S (ana hesap) dönemine bakar. "
        if sap
        else ""
    )

    sys_prompt = (
        "Sen kurumsal ITSM L1 asistanısın. Kullanıcı aynı olayda itiraz/ek bilgi verdi.\n"
        "KURALLAR:\n"
        "1. İlk sorunu ve senin önceki çözümünü unutma; sıfırdan başlama.\n"
        "2. Kullanıcının yeni itirazını (ör. adımı yaptım ama hata sürüyor) doğrudan yanıtla.\n"
        "3. Aynı 3 adımı kopyalama; bir sonraki tanı adımlarını yaz.\n"
        "4. Türkçe markdown, tam 3 numaralı adım.\n"
        "5. Son: 'Hâlâ olmazsa talep aç diyerek kayıt oluşturabilirsiniz.'\n"
        f"{sap_extra}"
    )
    prompt = f"""
Sınıf: {path or "—"}

Sohbet:
{chr(10).join(thread_lines)}

Benzer çözülmüş kayıtlar:
{chr(10).join(context_blocks) or "—"}

Bilgi bankası:
{kb_hint or "—"}

Önceki tavsiyeyi temel alarak kullanıcının itirazına cevap ver.
""".strip()
    return generate_llm_response(prompt, system_prompt=sys_prompt)


def answer_from_model_knowledge(user_text: str, classification: dict | None = None) -> str | None:
    """When Chroma has no match, answer from the model's own knowledge (NVIDIA API)."""
    if not is_llm_active():
        return None

    classed = classification or {}
    path = str(classed.get("path_label") or "").strip()
    modul = str(classed.get("modul_label") or classed.get("modul") or "").strip()
    surec = str(classed.get("surec_label") or classed.get("surec") or "").strip()
    sap_hint = ""
    if str(classed.get("birim") or "") == "sap_erp" or "sap" in (user_text or "").lower():
        sap_hint = (
            "Konu SAP (FI, MM, Basis, SD vb.) olabilir. İşlem kodu, şirket kodu, "
            "malzeme, dump veya hata metnine göre pratik L1 adımlar öner. "
            "Emin olmadığın yapılandırma değişikliklerini danışmana bırak."
        )

    sys_prompt = (
        "Sen kurumsal ITSM L1 asistanısın. Vektör veritabanında bu sorun için "
        "çözülmüş kayıt yok; kendi genel bilginle yardımcı ol.\n"
        "KURALLAR:\n"
        "1. Türkçe yaz, markdown kullan.\n"
        "2. 1-2 cümle empati, sonra tam 3 numaralandırılmış adım.\n"
        "3. Uydurma belge numarası veya kurum içi gizli bilgi üretme.\n"
        "4. Son cümle: 'Bu adımlar yetmezse talep aç diyerek kayıt oluşturabilirsiniz.'\n"
        f"{sap_hint}"
    )
    prompt = (
        f"Kullanıcı sorunu:\n\"{user_text}\"\n\n"
        f"Sınıflandırma (belirsiz olabilir): {path or '—'}\n"
        f"Modül: {modul or '—'}\n"
        f"Süreç: {surec or '—'}\n\n"
        "Kendi bilginle 3 adımlık çözüm yaz."
    )
    return generate_llm_response(prompt, system_prompt=sys_prompt)


def fallback_answer_from_resolved_tickets(user_text: str, similar_tickets: list[dict]) -> str:
    """Template fallback when LLM is unavailable."""
    if not similar_tickets:
        return ""

    payload = similar_tickets[0]
    ticket = payload.get("ticket") if isinstance(payload.get("ticket"), dict) else payload
    ticket_id = ticket.get("id", "—")
    resolution = ticket.get("resolution_summary") or ticket.get("recommended_next_step") or ""
    pct = payload.get("similarity_pct") or round(float(payload.get("score", 0)) * 100)

    return (
        f"**Benzer çözülmüş kayıt bulundu** (`{ticket_id}` · %{pct} benzerlik)\n\n"
        f"Geçmişte benzer bir sorun **{resolution}** şeklinde çözülmüştü. "
        f"Aynı yaklaşımı sizin durumunuza uyarlayarak denemenizi öneririm.\n\n"
        f"**Önerilen adımlar:**\n"
        f"1. Önce geçmiş kayıttaki tanı adımlarını uygulayın.\n"
        f"2. Sorun devam ederse cihaz/uygulama bilgilerinizi netleştirin.\n"
        f"3. Hâlâ çözülmediyse **talep aç** diyerek destek kaydı oluşturun.\n\n"
        f"*(Kaynak: `{ticket_id}`)*"
    )
