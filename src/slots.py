"""Dynamic ITSM slot filling and field extraction by category."""

from __future__ import annotations

import json
import re
from pathlib import Path

from text_norm import fold_tr

ROOT = Path(__file__).resolve().parent.parent
SCHEMAS_PATH = ROOT / "data" / "schemas.json"

REQUIRED_FIELDS = ("asset", "location", "impact")

FIELD_PROMPTS = {
    "asset": "Hangi cihaz, uygulama veya varlık bu? (ör. laptop, vpn, outlook, yazıcı)",
    "location": "Neredesiniz / ekipman nerede? (ör. 3. kat, İstanbul ofis, uzaktan/evden)",
    "impact": "Kimleri etkiliyor? (yalnız ben / ekibim / tüm ofis)",
    "details": "Sorunun detayını veya hata kodunu iletebilir misiniz?",
}

_ASSET_HINTS = (
    "laptop", "dizüstü", "dizustu", "masaüstü", "masaustu", "bilgisayar",
    "yazıcı", "yazici", "telefon", "hesap", "outlook", "vpn", "monitör", "monitor",
    "teams", "excel", "word", "sap", "klima", "sandalye", "koltuk", "kart",
    "cihaz", "uygulama", "sunucu", "internet", "wifi", "şifre", "sifre", "fatura", "avans"
)

_LOCATION_RE = re.compile(
    r"(\d+\.\s*kat|istanbul|ankara|izmir|bursa|kocaeli|gebze|maslak|levent|ar-ge|ofis|uzaktan|evden|toplanti odasi|toplantı|bodrum kat|zemin kat)",
    re.I,
)

_IMPACT_MAP = (
    (("tüm ofis", "tum ofis", "herkes", "bütün kat", "butun kat", "tüm şirket", "tum sirket", "tüm ekip", "tum ekip"), "tüm ofis"),
    (("ekibim", "ekip", "takım", "takim", "departmanımız", "departman"), "ekibim"),
    (("yalnız", "yalniz", "sadece ben", "beni", "bende"), "yalnız ben"),
)

_AMOUNT_RE = re.compile(r"(\d+[\.,]?\d*)\s*(?:tl|tl'lik|lira)", re.I)
_ERROR_CODE_RE = re.compile(r"(0x[0-9a-fA-F]+|Token Expired|Timeout Exception|Connection Refused|NTLM auth failed|Error \d+|Access Denied|403|500)", re.I)
_DATE_RE = re.compile(r"(\d{1,2}\s+(?:ocak|şubat|mart|nisan|mayıs|haziran|temmuz|ağustos|eylül|ekim|kasım|aralık))", re.I)


def load_schemas() -> dict:
    if not SCHEMAS_PATH.exists():
        return {}
    try:
        return json.loads(SCHEMAS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def get_required_fields_for_surec(surec_key: str) -> list[str]:
    return list(REQUIRED_FIELDS)


def empty_slots() -> dict[str, str]:
    return {key: "" for key in REQUIRED_FIELDS}


def extract_slots(text: str, required_fields: list[str] | None = None) -> dict[str, str]:
    raw = text or ""
    lowered = fold_tr(raw)
    found = empty_slots()
    
    for hint in _ASSET_HINTS:
        if hint in lowered:
            found["asset"] = hint
            break
            
    loc = _LOCATION_RE.search(raw) or _LOCATION_RE.search(lowered)
    if loc:
        found["location"] = loc.group(0)
        
    for phrases, label in _IMPACT_MAP:
        if any(p in lowered for p in phrases):
            found["impact"] = label
            break
            
    amt = _AMOUNT_RE.search(raw)
    if amt:
        found["amount"] = amt.group(0)
        
    err = _ERROR_CODE_RE.search(raw)
    if err:
        found["error_code"] = err.group(0)
        
    dt = _DATE_RE.search(raw)
    if dt:
        found["date"] = dt.group(0)
        
    return found


def merge_slots(current: dict | None, incoming: dict | None, required_fields: list[str] | None = None) -> dict[str, str]:
    slots = empty_slots()
    for key in REQUIRED_FIELDS:
        slots[key] = str((current or {}).get(key) or (incoming or {}).get(key) or "").strip()
    # Also carry forward any extra keys
    for src in (current or {}, incoming or {}):
        for k, v in src.items():
            if k not in slots and v:
                slots[k] = str(v).strip()
    return slots


def missing_fields(slots: dict[str, str], required_fields: list[str] | None = None) -> list[str]:
    fields = required_fields or REQUIRED_FIELDS
    return [key for key in fields if not str(slots.get(key) or "").strip()]


def apply_answer(slots: dict[str, str], field: str, text: str, required_fields: list[str] | None = None) -> dict[str, str]:
    updated = merge_slots(slots, None, required_fields)
    extracted = extract_slots(text, required_fields)
    
    val = " ".join((text or "").split())
    if field in REQUIRED_FIELDS:
        updated[field] = extracted.get(field) or val[:120]
        
    for key, value in extracted.items():
        if value and not updated.get(key):
            updated[key] = value
            
    return updated


def next_prompt(slots: dict[str, str], required_fields: list[str] | None = None) -> str | None:
    missing = missing_fields(slots, required_fields)
    if not missing:
        return None
    return FIELD_PROMPTS.get(missing[0], f"Lütfen {missing[0]} bilgisini iletebilir misiniz?")
