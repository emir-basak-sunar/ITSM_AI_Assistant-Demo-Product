"""SAP ERP module detection — routes SAP questions away from generic ITSM taxonomy."""

from __future__ import annotations

import re

from text_norm import fold_tr

SAP_MODULE_ALIASES: dict[str, dict[str, str]] = {
    "fi": {
        "modul": "sap_fi",
        "modul_label": "FI — Finans Muhasebe",
        "surec": "sap_fi_destek",
        "surec_label": "FI Genel Destek",
    },
    "mm": {
        "modul": "sap_mm",
        "modul_label": "MM — Malzeme Yönetimi",
        "surec": "sap_mm_destek",
        "surec_label": "MM Genel Destek",
    },
    "sd": {
        "modul": "sap_sd",
        "modul_label": "SD — Satış & Dağıtım",
        "surec": "sap_sd_destek",
        "surec_label": "SD Genel Destek",
    },
    "pp": {
        "modul": "sap_pp",
        "modul_label": "PP — Üretim Planlama",
        "surec": "sap_pp_destek",
        "surec_label": "PP Genel Destek",
    },
    "co": {
        "modul": "sap_co",
        "modul_label": "CO — Controlling",
        "surec": "sap_co_destek",
        "surec_label": "CO Genel Destek",
    },
    "pm": {
        "modul": "sap_pm",
        "modul_label": "PM — Bakım Yönetimi",
        "surec": "sap_pm_destek",
        "surec_label": "PM Genel Destek",
    },
    "hr": {
        "modul": "sap_hr",
        "modul_label": "HR — İnsan Kaynakları (HCM)",
        "surec": "sap_hr_destek",
        "surec_label": "HR Genel Destek",
    },
    "qm": {
        "modul": "sap_qm",
        "modul_label": "QM — Kalite Yönetimi",
        "surec": "sap_qm_destek",
        "surec_label": "QM Genel Destek",
    },
    "ewm": {
        "modul": "sap_ewm",
        "modul_label": "EWM — Gelişmiş Depo Yönetimi",
        "surec": "sap_ewm_destek",
        "surec_label": "EWM Genel Destek",
    },
    "ps": {
        "modul": "sap_ps",
        "modul_label": "PS — Proje Sistemi",
        "surec": "sap_ps_destek",
        "surec_label": "PS Genel Destek",
    },
}

MODULE_PATTERNS = [
    (re.compile(r"\bmm\b|\bmm\s*modul|\bmalzeme\s*yonetim", re.I), "mm"),
    (re.compile(r"\bfi\b|\bfinans\b|\bmuhasebe\b", re.I), "fi"),
    (re.compile(r"\bsd\b|\bsatis\b|\bdagitim\b", re.I), "sd"),
    (re.compile(r"\bpp\b|\buretim\b|\bis\s*emri\b", re.I), "pp"),
    (re.compile(r"\bco\b|\bcontrolling\b|\bmaliyet\b", re.I), "co"),
    (re.compile(r"\bpm\b|\bbakim\b|\bekipman\b", re.I), "pm"),
    (re.compile(r"\bhr\b|\bhcm\b|\bbordro\b|\bsicil\b", re.I), "hr"),
    (re.compile(r"\bqm\b|\bkalite\b|\bmuayene\b", re.I), "qm"),
    (re.compile(r"\bewm\b|\bdepo\b|\bwarehouse\b", re.I), "ewm"),
    (re.compile(r"\bps\b|\bproje\b|\bwbs\b", re.I), "ps"),
]

REFUSE_CLARIFY_PHRASES = (
    "paylasam",
    "paylaşam",
    "soylemem",
    "söylemem",
    "bilmiyorum",
    "bilemiyorum",
    "detay veremem",
    "listeleyemem",
    "yok elimde",
)


def is_sap_context(text: str) -> bool:
    lowered = fold_tr(text)
    return "sap" in lowered or "erp" in lowered or bool(re.search(r"\b(tcode|transaction|me21n|migo|mm0|fb50)\b", lowered))


def detect_sap_module(text: str) -> str | None:
    lowered = fold_tr(text)
    for pattern, code in MODULE_PATTERNS:
        if pattern.search(lowered):
            return code
    return None


def classify_sap_request(text: str) -> dict | None:
    """Return taxonomy-shaped classification when text is an SAP ERP question."""
    if not is_sap_context(text):
        return None

    module_code = detect_sap_module(text) or "mm"
    module = SAP_MODULE_ALIASES.get(module_code, SAP_MODULE_ALIASES["mm"])

    return {
        "unclear": False,
        "score": 5,
        "hits": ["sap", module_code],
        "source": "sap_router",
        "model_confidence": 0.0,
        "talep_turu": "bilgi",
        "talep_turu_label": "Bilgi Talebi (Information)",
        "birim": "sap_erp",
        "birim_label": "SAP ERP",
        "modul": module["modul"],
        "modul_label": module["modul_label"],
        "surec": module["surec"],
        "surec_label": module["surec_label"],
        "path_label": (
            f"Bilgi Talebi (Information) → SAP ERP → "
            f"{module['modul_label']} → {module['surec_label']}"
        ),
        "clarify_hint": "",
    }


def classification_from_solution(row: dict) -> dict:
    return {
        "unclear": False,
        "score": 4,
        "hits": [],
        "source": "solution_match",
        "model_confidence": 0.0,
        "talep_turu": str(row.get("talep_turu") or "bilgi"),
        "talep_turu_label": str(row.get("talep_turu") or "Bilgi Talebi (Information)"),
        "birim": str(row.get("birim") or ""),
        "birim_label": str(row.get("birim_label") or ""),
        "modul": str(row.get("modul") or ""),
        "modul_label": str(row.get("modul_label") or ""),
        "surec": str(row.get("surec") or ""),
        "surec_label": str(row.get("surec_label") or ""),
        "path_label": " → ".join(
            part
            for part in (
                row.get("talep_turu"),
                row.get("birim_label"),
                row.get("modul_label"),
                row.get("surec_label"),
            )
            if part
        ),
        "clarify_hint": "",
    }


def user_refuses_clarify(text: str) -> bool:
    lowered = fold_tr(text)
    return any(phrase in lowered for phrase in REFUSE_CLARIFY_PHRASES)
