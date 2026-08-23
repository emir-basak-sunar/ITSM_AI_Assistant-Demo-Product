"""Optional Ollama copy for manager bullets and record notes.

Does not decide escalate vs resolve. Callers must keep using the orchestrator.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

import requests

DEFAULT_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate")
DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")
DEFAULT_TIMEOUT = float(os.environ.get("ASSISTANT_LLM_TIMEOUT", "60"))


def extract_json(text: str) -> dict[str, Any]:
    """Parse JSON even if the model wraps it or forgets a closing brace."""
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    candidates = [text]
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if match:
        candidates.insert(0, match.group(0))
    if "{" in text and "}" not in text:
        candidates.append(text + "\n}")

    last_error: Exception | None = None
    for candidate in candidates:
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError as exc:
            last_error = exc
            continue
        if isinstance(data, dict):
            return data
        last_error = ValueError("JSON was not an object")
    raise last_error or ValueError("No JSON object in model output")


def generate_record_copy(
    *,
    category: str,
    sentiment: str,
    customer_ask: str,
    tried_rules: list[str],
    why_unresolved: str,
    high_risk: bool,
    thread_excerpt: str,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict[str, Any] | None:
    """Return summary_bullets + handoff_notes, or None to use templates."""
    prompt = f"""
You write a supervisor brief for an already-opened complaint record.
Do not decide whether to escalate, resolve, or reply to the customer.
Do not invent facts that are not in the material below.

Respond with ONLY valid JSON. No markdown. No extra text.

JSON schema:
{{
  "summary_bullets": ["short bullet", "short bullet", "short bullet"],
  "handoff_notes": "a short paragraph a supervisor can read in ten seconds, then a compact thread recap"
}}

Rules:
- Exactly 3 summary_bullets, each under 160 characters.
- Turkish only.
- Include category, tone, and why it is still open.

Material:
category: {category}
sentiment: {sentiment}
high_risk: {high_risk}
why_unresolved: {why_unresolved}
tried_rules: {", ".join(tried_rules) or "none"}
customer_ask: {customer_ask}
thread:
{thread_excerpt}
""".strip()

    payload = {
        "model": DEFAULT_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.2},
    }
    try:
        response = requests.post(DEFAULT_URL, json=payload, timeout=timeout)
        response.raise_for_status()
        raw = response.json().get("response", "")
        data = extract_json(raw)
    except (requests.RequestException, json.JSONDecodeError, ValueError, OSError):
        return None

    bullets_raw = data.get("summary_bullets")
    notes = str(data.get("handoff_notes") or "").strip()
    if not isinstance(bullets_raw, list) or not notes:
        return None
    bullets = [re.sub(r"\s+", " ", str(item)).strip() for item in bullets_raw]
    bullets = [item for item in bullets if item][:3]
    if len(bullets) != 3:
        return None
    return {
        "summary_bullets": bullets,
        "handoff_notes": notes,
    }

def _is_faithful(canned: str, rewritten: str, min_sim: float = 0.3) -> bool:
    """True if paraphrase stays close to the canned text."""
    c_words = set(re.findall(r"\w+", canned.lower()))
    r_words = set(re.findall(r"\w+", rewritten.lower()))
    if not c_words or not r_words:
        return True
    overlap = len(c_words & r_words) / max(len(c_words), 1)
    return overlap >= min_sim


def rewrite_customer_reply(
    *,
    canned_reply: str,
    timeout: float = DEFAULT_TIMEOUT,
) -> str | None:
    """Rewrite the already-decided reply using Gemini / LLM. None = keep the canned text."""
    canned_reply = (canned_reply or "").strip()
    if not canned_reply:
        return None

    try:
        from llm_engine import generate_llm_response
        prompt = f"""
Aşağıdaki kurumsal yanıtı anlamını ve içindeki bilet ID, basamak ve kritik bilgileri %100 koruyarak daha akıcı ve profesyonel Türkçe ile yeniden ifade et.
Hiçbir bilgi ekleme, çıkarma. Sadece metni döndür.

Metin:
{canned_reply}
""".strip()
        text = generate_llm_response(prompt)
        if text and _is_faithful(canned_reply, text):
            return text.strip()
    except Exception:
        pass

    return None