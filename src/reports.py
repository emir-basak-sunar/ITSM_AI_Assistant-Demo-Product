"""Store chatbot reporting commands; daily_jobs.py executes them."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path

from text_norm import fold_tr
from tickets import load_tickets

ROOT = Path(__file__).resolve().parent.parent
REPORT_JOBS_PATH = ROOT / "data" / "report_jobs.jsonl"

REPORT_PHRASES = (
    "rapor",
    "günlük özet",
    "gunluk ozet",
    "açık talepler",
    "acik talepler",
    "ticket raporu",
    "birim özeti",
    "birim ozeti",
    "istatistik",
    "analiz",
    "kaç talep var",
)


def looks_report_command(text: str) -> bool:
    lowered = fold_tr(text)
    return any(p in lowered for p in REPORT_PHRASES)


def load_jobs() -> list[dict]:
    if not REPORT_JOBS_PATH.exists():
        return []
    jobs: list[dict] = []
    for line in REPORT_JOBS_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        jobs.append(json.loads(line))
    return jobs


def _next_id(existing: list[dict]) -> str:
    day = datetime.now().strftime("%Y%m%d")
    prefix = f"R-{day}-"
    seq = 0
    for job in existing:
        jid = str(job.get("id", ""))
        if jid.startswith(prefix):
            try:
                seq = max(seq, int(jid.split("-")[-1]))
            except ValueError:
                pass
    return f"{prefix}{seq + 1:04d}"


def queue_report_job(
    *,
    command: str,
    birim: str = "",
    requested_by: str = "",
) -> dict:
    existing = load_jobs()
    job = {
        "id": _next_id(existing),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "command": (command or "").strip(),
        "birim": birim,
        "requested_by": (requested_by or "").strip().lower(),
        "status": "queued",
        "result": "",
        "run_at": "",
    }
    REPORT_JOBS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with REPORT_JOBS_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(job, ensure_ascii=False) + "\n")
    return job


def _rewrite(jobs: list[dict]) -> None:
    REPORT_JOBS_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JOBS_PATH.write_text(
        "".join(json.dumps(j, ensure_ascii=False) + "\n" for j in jobs),
        encoding="utf-8",
    )


def build_unit_summary(birim: str = "") -> str:
    tickets = load_tickets()
    if birim:
        tickets = [t for t in tickets if str(t.get("birim") or "").lower() == birim.lower() or str(t.get("birim_label") or "").lower() == birim.lower()]
        
    total_n = len(tickets)
    open_n = sum(1 for t in tickets if t.get("status") in {"open", "in_progress", ""})
    resolved_n = sum(1 for t in tickets if t.get("status") == "resolved")
    high_n = sum(1 for t in tickets if t.get("urgency") == "high")
    
    by_unit = Counter(str(t.get("birim_label") or t.get("birim") or "Diğer") for t in tickets)
    by_modul = Counter(str(t.get("modul_label") or t.get("modul") or "Diğer") for t in tickets)
    by_surec = Counter(str(t.get("surec_label") or t.get("surec") or "Diğer") for t in tickets)

    unit_title = f" ({birim.upper()})" if birim else " (Tüm Birimler)"
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M')

    lines = [
        f"### 📊 ITSM Yönetici Günlük Özeti{unit_title}",
        f"**Tarih/Saat:** `{now_str}`",
        f"**Genel Durum:** Toplam {total_n} kayıt · 🟢 {resolved_n} Çözüldü · 🟡 {open_n} Açık/İşlemde · 🔴 {high_n} Yüksek Öncelik",
        "",
        "#### 🏢 Birim Bazlı Dağılım:"
    ]
    
    if by_unit:
        for u, count in by_unit.most_common():
            lines.append(f"- **{u}:** {count} talep")
    else:
        lines.append("- Henüz kayıtlı bilet bulunmamaktadır.")
        
    if by_surec:
        lines.append("")
        lines.append("#### 🔥 En Sık Karşılaşılan Süreçler (Top 5):")
        for s, count in by_surec.most_common(5):
            lines.append(f"1. **{s}:** {count} adet")
            
    lines.append("")
    lines.append("📨 *Bu rapor ilgili birim yöneticilerine ve dağıtım listesine otomatik olarak iletilmiştir.*")
    return "\n".join(lines)


def run_queued_jobs(*, allow_empty_run: bool = True) -> list[dict]:
    """Run queued report jobs. If queue is empty, create a daily summary job first."""
    jobs = load_jobs()
    has_queued = any(j.get("status") == "queued" for j in jobs)
    if not has_queued and allow_empty_run:
        jobs.append(
            {
                "id": _next_id(jobs),
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "command": "Günlük ITSM özet raporu (yönetici paneli)",
                "birim": "",
                "requested_by": "admin_panel",
                "status": "queued",
                "result": "",
                "run_at": "",
            }
        )
        _rewrite(jobs)

    ran: list[dict] = []
    stamp = datetime.now().isoformat(timespec="seconds")
    for job in jobs:
        if job.get("status") != "queued":
            continue
        job["result"] = build_unit_summary(str(job.get("birim") or ""))
        job["status"] = "sent"
        job["run_at"] = stamp
        ran.append(job)
    if ran:
        _rewrite(jobs)
    return ran
