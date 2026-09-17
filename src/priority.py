"""ITSM priority inference from text, classification and sentiment."""

from __future__ import annotations

from text_norm import fold_tr

CRITICAL_PHRASES = (
    "kritik",
    "acil",
    "tüm ofis",
    "tum ofis",
    "tüm sistem",
    "tum sistem",
    "sunucu çöktü",
    "sunucu coktu",
    "erişilemez",
    "erisilemez",
    "kesinti",
    "fidye",
    "ransomware",
)

HIGH_PHRASES = (
    "yüksek",
    "yuksek",
    "hemen",
    "çalışamıyorum",
    "calisamiyorum",
    "iş durdu",
    "is durdu",
    "kilitlendi",
    "açılmıyor",
    "acilmiyor",
)

LOW_PHRASES = (
    "düşük",
    "dusuk",
    "bilgi",
    "sorgu",
    "merak",
    "ne zaman",
    "kaç gün",
    "bakiye",
)


def infer_priority(
    text: str,
    *,
    talep_turu: str = "",
    high_risk: bool = False,
    sentiment: str = "",
) -> str:
    """Return Kritik | Yüksek | Orta | Düşük."""
    lowered = fold_tr(text or "")
    talep = fold_tr(talep_turu or "")

    if high_risk or any(p in lowered for p in CRITICAL_PHRASES):
        return "Kritik"
    if sentiment == "angry" or any(p in lowered for p in HIGH_PHRASES):
        return "Yüksek"
    if "arıza" in talep or "ariza" in talep:
        return "Yüksek"
    if "bilgi" in talep or any(p in lowered for p in LOW_PHRASES):
        return "Düşük"
    if "hizmet" in talep:
        return "Orta"
    return "Orta"
