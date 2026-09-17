"""Dynamic ITSM slot filling from schemas.json and free-text extraction."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from text_norm import fold_tr

ROOT = Path(__file__).resolve().parent.parent
SCHEMAS_PATH = ROOT / "data" / "schemas.json"

REQUIRED_FIELDS = ("asset", "location", "impact")

FIELD_PROMPTS = {
    "asset": "Hangi cihaz, uygulama veya varlık bu? (ör. laptop, vpn, outlook, yazıcı)",
    "location": "Neredesiniz / ekipman nerede? (ör. 3. kat, İstanbul ofis, uzaktan/evden)",
    "impact": "Kimleri etkiliyor? (yalnız ben / ekibim / tüm ofis)",
}

LOCATION_FIELDS = frozenset(
    {
        "location",
        "ofis_lokasyon",
        "lokasyon_kat_oda",
        "yazici_lokasyon",
        "teslimat_lokasyonu",
        "kart_kayip_tarihi_yeri",
    }
)
IMPACT_FIELDS = frozenset({"impact", "etkilenen_kullanici_sayisi", "etkilenen_kisi_sayisi"})
DEVICE_FIELDS = frozenset(
    {
        "asset",
        "cihaz_etiket_no",
        "cihaz_seri_no",
        "cihaz_marka_model",
        "kullanilan_cihaz_turu",
        "yazici_marka_model",
        "uygulama_adi",
    }
)
AMOUNT_FIELDS = frozenset({"amount", "talep_tutari"})
ERROR_FIELDS = frozenset({"error_code", "hata_kodu", "hata_kodu_mesaji", "hata_mesaji", "hata_ekran_goruntusu"})
USER_FIELDS = frozenset({"kullanici_adi", "kullanici_adi_sicil_no", "personel_sicil_no", "ad_soyad"})
DEPARTMENT_FIELDS = frozenset({"departman", "departman_pozisyon"})

_ASSET_HINTS = (
    "laptop",
    "dizüstü",
    "dizustu",
    "masaüstü",
    "masaustu",
    "bilgisayar",
    "yazıcı",
    "yazici",
    "telefon",
    "hesap",
    "outlook",
    "vpn",
    "monitör",
    "monitor",
    "teams",
    "excel",
    "word",
    "sap",
    "klima",
    "sandalye",
    "koltuk",
    "kart",
    "cihaz",
    "uygulama",
    "sunucu",
    "internet",
    "wifi",
    "şifre",
    "sifre",
    "fatura",
    "avans",
)

_LOCATION_RE = re.compile(
    r"(\d+\.\s*kat|istanbul|ankara|izmir|bursa|kocaeli|gebze|maslak|levent|ar-ge|ofis|uzaktan|evden|toplanti odasi|toplantı|bodrum kat|zemin kat|merkez)",
    re.I,
)
_AMOUNT_RE = re.compile(r"(\d+[\.,]?\d*)\s*(?:tl|tl'lik|lira)", re.I)
_ERROR_CODE_RE = re.compile(
    r"(0x[0-9a-fA-F]+|Token Expired|Timeout Exception|Connection Refused|NTLM auth failed|Error \d+|Access Denied|403|500)",
    re.I,
)
_DATE_RE = re.compile(
    r"(\d{1,2}\s+(?:ocak|şubat|mart|nisan|mayıs|haziran|temmuz|ağustos|eylül|ekim|kasım|aralık))",
    re.I,
)
_IMPACT_MAP = (
    (("tüm ofis", "tum ofis", "herkes", "bütün kat", "butun kat", "tüm şirket", "tum sirket", "tüm ekip", "tum ekip"), "tüm ofis"),
    (("ekibim", "ekip", "takım", "takim", "departmanımız", "departman"), "ekibim"),
    (("yalnız", "yalniz", "sadece ben", "beni", "bende"), "yalnız ben"),
)


@lru_cache(maxsize=1)
def load_schemas() -> dict:
    if not SCHEMAS_PATH.exists():
        return {}
    try:
        return json.loads(SCHEMAS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def get_schema_for_surec(surec_key: str) -> dict | None:
    if not surec_key:
        return None
    schemas = load_schemas()
    if surec_key in schemas:
        return schemas[surec_key]
    folded = fold_tr(surec_key)
    for key, value in schemas.items():
        if fold_tr(key) == folded:
            return value
    return None


def get_required_fields_for_surec(surec_key: str) -> list[str]:
    schema = get_schema_for_surec(surec_key)
    if schema and schema.get("zorunlu_alanlar"):
        return list(schema["zorunlu_alanlar"])
    return list(REQUIRED_FIELDS)


def _human_label(field: str) -> str:
    return field.replace("_", " ")


def _prompt_for_field(field: str, surec_key: str) -> str:
    if field in FIELD_PROMPTS:
        return FIELD_PROMPTS[field]
    schema = get_schema_for_surec(surec_key)
    if schema:
        fields = schema.get("zorunlu_alanlar") or []
        hint = str(schema.get("netlestirme_sorusu") or "").strip()
        if hint and fields and field == fields[0]:
            return hint
    return f"Lütfen {_human_label(field)} bilgisini iletebilir misiniz?"


def empty_slots(required_fields: list[str] | None = None) -> dict[str, str]:
    fields = required_fields or list(REQUIRED_FIELDS)
    return {key: "" for key in fields}


def _impact_label(lowered: str) -> str:
    for phrases, label in _IMPACT_MAP:
        if any(p in lowered for p in phrases):
            return label
    return ""


def extract_slots(text: str, required_fields: list[str] | None = None) -> dict[str, str]:
    raw = text or ""
    lowered = fold_tr(raw)
    fields = required_fields or list(REQUIRED_FIELDS)
    found = empty_slots(fields)

    asset_hint = ""
    for hint in _ASSET_HINTS:
        if hint in lowered:
            asset_hint = hint
            break

    location_val = ""
    loc = _LOCATION_RE.search(raw) or _LOCATION_RE.search(lowered)
    if loc:
        location_val = loc.group(0)

    impact_val = _impact_label(lowered)
    amount_val = (_AMOUNT_RE.search(raw) or _AMOUNT_RE.search(lowered))
    amount_val = amount_val.group(0) if amount_val else ""
    error_val = (_ERROR_CODE_RE.search(raw) or _ERROR_CODE_RE.search(lowered))
    error_val = error_val.group(0) if error_val else ""
    date_val = (_DATE_RE.search(raw) or _DATE_RE.search(lowered))
    date_val = date_val.group(0) if date_val else ""

    user_match = re.search(r"(?:kullanici|kullanıcı)\s+([\w.\-@]+)", raw, re.I)
    sicil_match = re.search(r"sicil\s*(\d+)", raw, re.I)
    iban_match = re.search(r"\bIBAN\s*[A-Z0-9]+", raw, re.I)
    provider_match = re.search(r"(turk telekom|superonline|vodafone|turkcell)", lowered)

    for field in fields:
        if field in LOCATION_FIELDS and location_val:
            found[field] = location_val
        elif field in IMPACT_FIELDS and impact_val:
            found[field] = impact_val
        elif field in DEVICE_FIELDS and asset_hint:
            found[field] = asset_hint
        elif field in AMOUNT_FIELDS and amount_val:
            found[field] = amount_val
        elif field in ERROR_FIELDS and error_val:
            found[field] = error_val
        elif field in ERROR_FIELDS and "timeout" in lowered:
            found[field] = "timeout hatasi"
        elif field == "izin_tarih_araligi" and date_val:
            found[field] = date_val
        elif field in DEPARTMENT_FIELDS and "departman" in lowered:
            found[field] = "departman bilgisi mesajda"
        elif field in USER_FIELDS and user_match:
            found[field] = user_match.group(1)
        elif field in USER_FIELDS and sicil_match:
            found[field] = sicil_match.group(1)
        elif field == "internet_saglayici" and provider_match:
            found[field] = provider_match.group(1)
        elif field == "seyahat_gorev_amaci" and ("seyahat" in lowered or "gorev" in lowered or "görev" in lowered):
            found[field] = "is seyahati"
        elif field == "yonetici_onayi" and ("onay" in lowered or "onayli" in lowered or "onaylı" in lowered):
            found[field] = "yonetici onayli"
        elif field == "odeme_hesap_bilgisi" and iban_match:
            found[field] = iban_match.group(0)
        elif field == "kart_kayip_tarihi_yeri" and ("kayb" in lowered or location_val):
            found[field] = f"{location_val} kayip".strip()
        elif field == "iptal_degisiklik_nedeni" and raw.strip():
            found[field] = raw.strip()[:120]

    if "asset" in fields and asset_hint:
        found["asset"] = asset_hint
    if "location" in fields and location_val:
        found["location"] = location_val
    if "impact" in fields and impact_val:
        found["impact"] = impact_val
    if amount_val and "amount" in fields:
        found["amount"] = amount_val
    if error_val and "error_code" in fields:
        found["error_code"] = error_val

    return found


def merge_slots(
    current: dict | None,
    incoming: dict | None,
    required_fields: list[str] | None = None,
) -> dict[str, str]:
    fields = required_fields or list(REQUIRED_FIELDS)
    slots = empty_slots(fields)
    for key in fields:
        slots[key] = str((current or {}).get(key) or (incoming or {}).get(key) or "").strip()
    for src in (current or {}, incoming or {}):
        for key, value in src.items():
            if value and not slots.get(key):
                slots[key] = str(value).strip()
    return slots


def missing_fields(slots: dict[str, str], required_fields: list[str] | None = None) -> list[str]:
    fields = required_fields or list(REQUIRED_FIELDS)
    return [key for key in fields if not str(slots.get(key) or "").strip()]


def apply_answer(
    slots: dict[str, str],
    field: str,
    text: str,
    required_fields: list[str] | None = None,
) -> dict[str, str]:
    fields = required_fields or list(REQUIRED_FIELDS)
    updated = merge_slots(slots, None, fields)
    extracted = extract_slots(text, fields)
    val = " ".join((text or "").split())

    if field in fields:
        updated[field] = extracted.get(field) or val[:160]

    for key, value in extracted.items():
        if value and not updated.get(key):
            updated[key] = value

    return updated


def next_prompt(slots: dict[str, str], required_fields: list[str] | None = None, surec_key: str = "") -> str | None:
    fields = required_fields or list(REQUIRED_FIELDS)
    missing = missing_fields(slots, fields)
    if not missing:
        return None
    return _prompt_for_field(missing[0], surec_key)
