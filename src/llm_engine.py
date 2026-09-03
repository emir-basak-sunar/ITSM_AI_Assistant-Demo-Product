"""LLM Integration Engine (Google Gemini 3.5 Flash + Flash Lite + Groq + Hybrid RAG).

Handles dynamic personalized solution synthesis, executive summaries, and intelligent IT reasoning.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

# Search and load .env from both project root and src/
SRC_DIR = Path(__file__).resolve().parent
ROOT_DIR = SRC_DIR.parent

load_dotenv(SRC_DIR / ".env")
load_dotenv(ROOT_DIR / ".env")
load_dotenv()  # Default lookup

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
USE_LLM = os.getenv("ASSISTANT_USE_LLM", "1").strip().lower() in {"1", "true", "yes"}

# Persistent session with connection pool
SESSION = requests.Session()

# High-quota, ultra-fast Gemini models (fastest first)
GEMINI_MODELS = [
    "gemini-flash-lite-latest",
    "gemini-flash-latest",
    "gemini-2.5-flash",
    "gemma-4-26b-a4b-it",
    "gemma-4-31b-it",
]


def is_llm_active() -> bool:
    """Return True if an API key is available and enabled."""
    if not USE_LLM:
        return False
    return bool(GEMINI_API_KEY or GROQ_API_KEY)


def call_gemini(prompt: str, system_prompt: str = "", timeout: float = 8.0) -> str | None:
    """Call Google Gemini with automatic model fallback and connection reuse."""
    if not GEMINI_API_KEY:
        return None
    
    full_prompt = prompt
    if system_prompt:
        full_prompt = f"{system_prompt}\n\nKULLANICI TALEBİ:\n{prompt}"
        
    payload = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 2500,
        },
    }
    
    for model_name in GEMINI_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
        try:
            resp = SESSION.post(url, json=payload, timeout=timeout)
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates") or []
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        text = str(parts[0].get("text", "")).strip()
                        if text:
                            return text
        except Exception:
            continue
            
    return None


def call_groq(prompt: str, system_prompt: str = "", timeout: float = 10.0) -> str | None:
    """Call Groq Cloud (Llama 3.3 70B) via OpenAI-compatible endpoint."""
    if not GROQ_API_KEY:
        return None
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 1200,
    }
    
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
        if resp.status_code == 200:
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[Groq API Warning] {e}")
        return None
    return None


def generate_llm_response(prompt: str, system_prompt: str = "") -> str | None:
    """Multi-provider LLM caller: Tries Gemini -> Groq -> None (Fallback)."""
    # 1. Gemini
    if GEMINI_API_KEY:
        res = call_gemini(prompt, system_prompt)
        if res:
            return res
    
    # 2. Groq
    if GROQ_API_KEY:
        res = call_groq(prompt, system_prompt)
        if res:
            return res
            
    return None


def synthesize_ai_troubleshooting(user_text: str, solution_row: dict) -> str | None:
    """Use Gemini to generate a complete, concise, problem-specific troubleshooting guide."""
    if not is_llm_active():
        return None
    
    title = solution_row.get("title") or solution_row.get("surec_label") or "Kurumsal Çözüm"
    unit = solution_row.get("birim_label", "Bilgi Teknolojileri")
    
    sys_prompt = (
        "Sen kurumsal bir IT Servis Masası ve Teknik Destek Yapay Zeka Uzmanısın. "
        "Kullanıcının ilettiği spesifik sorunu (örneğin mikrofon/kulaklık arızası, masaüstü arkaplanının siyah olması/explorer.exe çökmesi vb.) "
        "derinlemesine anla ve o spesifik probleme odaklanan tam ve eksiksiz 3 pratik adımlık çözüm rehberini üret. "
        "KURALLAR:\n"
        "1. Girişte 1-2 cümleyle kullanıcıyla empati kur ve sorunu anladığını belirt.\n"
        "2. Tam 3 adet numaralandırılmış (1., 2., 3.) somut adım yaz. Her adımı net, anlaşılır ve 2-3 cümleyle açıkla.\n"
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
