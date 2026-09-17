"""Expected-action checks. From the repo root:

    python src/eval_dialogues.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import reports as reports_mod
import tickets as tickets_mod

_tmp = Path(tempfile.mkdtemp())
tickets_mod.TICKETS_PATH = _tmp / "tickets_eval.jsonl"
reports_mod.REPORT_JOBS_PATH = _tmp / "jobs_eval.jsonl"

from orchestrator import handle_turn


def play(case: dict) -> list:
    tickets_mod.TICKETS_PATH.parent.mkdir(parents=True, exist_ok=True)
    tickets_mod.TICKETS_PATH.write_text("", encoding="utf-8")
    reports_mod.REPORT_JOBS_PATH.write_text("", encoding="utf-8")
    history: list[dict] = []
    phase = "open"
    last_rule = None
    last_ticket = None
    slots: dict = {}
    classification = None
    results = []
    for turn in case["turns"]:
        result = handle_turn(
            turn["text"],
            history=history,
            phase=phase,
            last_rule_id=last_rule,
            last_ticket_id=last_ticket,
            slots=slots,
            classification=classification,
        )
        results.append(result)
        history.append({"role": "user", "content": turn["text"]})
        history.append({"role": "assistant", "content": result.reply})
        phase = result.phase
        last_rule = result.last_rule_id
        slots = result.slots or {}
        classification = result.classification
        if result.ticket:
            last_ticket = result.ticket["id"]
        elif result.debug.get("action") == "resolved":
            last_ticket = None
    return results


def _record_blob() -> str:
    parts = []
    for ticket in tickets_mod.load_tickets():
        parts.append(str(ticket.get("customer_ask", "")))
        parts.append(str(ticket.get("path_label", "")))
        parts.append(str(ticket.get("handoff_notes", "")))
        for item in ticket.get("followups") or []:
            if isinstance(item, dict):
                parts.append(str(item.get("text", "")))
            else:
                parts.append(str(item))
    return "\n".join(parts)


DIALOGUES = [
    {
        "name": "1_donanim_cozum",
        "turns": [
            {
                "text": "Laptopum açılmıyor, ekran siyah.",
                "action": "suggest_solution",
            }
        ],
    },
    {
        "name": "2_talep_ac_sinif",
        "turns": [
            {
                "text": "Bilgisayarım bozuldu, talep açmak istiyorum.",
                "action": "collect_fields",
            }
        ],
    },
    {
        "name": "3_netlestir",
        "turns": [
            {
                "text": "Bir sorunum var yardımcı olur musun",
                "action": "clarify",
            }
        ],
    },
    {
        "name": "4_sifre_cozum",
        "turns": [
            {
                "text": "Şifremi unuttum hesabım kilitlendi.",
                "action": "suggest_solution",
            },
            {
                "text": "İşe yaradı teşekkürler.",
                "action": "self_resolved",
            },
        ],
    },
    {
        "name": "5_ticket_alanlar",
        "turns": [
            {
                "text": "VPN bağlanamıyorum talep aç",
                "action": "collect_fields",
            },
            {
                "text": "kullanici ahmet.yilmaz, timeout hatasi, laptop, turk telekom",
                "action": "ticket_open",
            },
        ],
        "ticket_count": 1,
    },
    {
        "name": "6_rapor_kuyruk",
        "turns": [
            {
                "text": "Açık taleplerin raporunu hazırla, günlük özet istiyorum.",
                "action": "report_queued",
            }
        ],
    },
    {
        "name": "7_followup",
        "ticket_count": 1,
        "notes_contains": "8821",
        "turns": [
            {
                "text": "VPN bağlanamıyorum talep aç",
                "action": "collect_fields",
            },
            {
                "text": "kullanici ahmet.yilmaz timeout hatasi laptop turk telekom",
                "action": "ticket_open",
            },
            {
                "text": "Hâlâ aynı, takip 8821.",
                "action": "ticket_followup",
                "same_ticket": True,
            },
        ],
    },
    {
        "name": "8_kisa_acilmiyo",
        "turns": [
            {
                "text": "bilgisayarım açılmıyo",
                "action": "suggest_solution",
            }
        ],
    },
    {
        "name": "9_laptop_tek",
        "turns": [
            {
                "text": "laptop",
                "action": "suggest_solution",
            }
        ],
    },
    {
        "name": "10_klima_cozum",
        "turns": [
            {
                "text": "4. kat klima çok gürültü yapıyor ve soğutmuyor.",
                "action": "suggest_solution",
            }
        ],
    },
    {
        "name": "11_kart_kayip",
        "turns": [
            {
                "text": "Giriş kartımı kaybettim, acil talep aç",
                "action": "collect_fields",
            },
            {
                "text": "sicil 12345, Maslak Ofis 3. kat dün kaybettim, IT departmanı",
                "action": "ticket_open",
            }
        ],
        "ticket_count": 1,
    },
    {
        "name": "12_avans_talebi",
        "turns": [
            {
                "text": "İş seyahati için avans talep ediyorum, talep aç",
                "action": "collect_fields",
            },
            {
                "text": "1500 TL iş seyahati avansı, yönetici onaylı, IBAN TR123456",
                "action": "ticket_open",
            }
        ],
        "ticket_count": 1,
    },
    {
        "name": "13_izin_sorgu",
        "turns": [
            {
                "text": "Kaç gün yıllık izin hakkım kaldı?",
                "action": "suggest_solution",
            }
        ],
    },
]


def main() -> int:
    failed = 0
    for case in DIALOGUES:
        results = play(case)
        ticket_ids = []
        case_failed = False
        for turn, result in zip(case["turns"], results):
            action = result.debug.get("action")
            ok = action == turn["action"]
            if result.ticket:
                ticket_ids.append(result.ticket["id"])
            if turn.get("same_ticket") and len(ticket_ids) >= 2:
                ok = ok and ticket_ids[-1] == ticket_ids[0]
            status = "OK" if ok else "FAIL"
            if not ok:
                case_failed = True
            print(
                f"{status:4} {case['name']:28} got={action} "
                f"expected={turn['action']}"
            )

        stored = tickets_mod.load_tickets()
        blob = _record_blob()
        extras = []
        if case.get("ticket_count") is not None:
            extras.append(len(stored) == case["ticket_count"])
        if case.get("notes_contains"):
            extras.append(case["notes_contains"] in blob)
        if extras and not all(extras):
            case_failed = True
            print(f"FAIL {case['name']:28} record checks failed")
        elif extras:
            print(f"OK   {case['name']:28} record checks")

        if case_failed:
            failed += 1

    print()
    if failed:
        print(f"{failed} dialogue(s) failed.")
        return 1
    print(f"All {len(DIALOGUES)} dialogues passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
