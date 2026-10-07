"""27 süreç için Chroma RAG derlemi.

itsmyenidataset.json metinleri + solutions.jsonl çözüm adımları → data/rag_corpus.jsonl

    .\\.venv\\Scripts\\python.exe src\\build_rag_corpus.py
    .\\.venv\\Scripts\\python.exe src\\build_rag_corpus.py --index
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

SRC = Path(__file__).resolve().parent
ROOT = SRC.parent
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from solutions import load_solutions
from taxonomy import PATHS, path_by_surec

DATASET_PATH = ROOT / "data" / "itsmyenidataset.json"
FALLBACK_DATASET = ROOT / "data" / "itsm_dataset.json"
OUT_PATH = ROOT / "data" / "rag_corpus.jsonl"
PER_CLASS = 8


def _load_examples() -> list[dict]:
    path = DATASET_PATH if DATASET_PATH.exists() else FALLBACK_DATASET
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else []


def _steps_text(row: dict) -> str:
    steps = row.get("steps") or []
    if isinstance(steps, str):
        return steps
    return " ".join(str(s) for s in steps)


def _bucket_examples(rows: list[dict]) -> dict[str, list[str]]:
    buckets: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        text = str(row.get("talep_metni") or "").strip()
        label = str(row.get("surec_talep_tipi") or "").strip()
        path = path_by_surec(label)
        if not path or not text:
            continue
        if len(buckets[path.surec]) >= PER_CLASS:
            continue
        if text in buckets[path.surec]:
            continue
        buckets[path.surec].append(text)
    return buckets


def build_records() -> list[dict]:
    solutions = {str(s.get("surec") or ""): s for s in load_solutions()}
    buckets = _bucket_examples(_load_examples())
    stamp = datetime.now().isoformat(timespec="seconds")
    records: list[dict] = []

    for path in PATHS:
        sol = solutions.get(path.surec) or {}
        texts = buckets.get(path.surec) or []
        if not texts:
            kw = ", ".join(path.keywords[:4])
            texts = [f"{path.surec_label} konusunda yardım istiyorum ({kw})."]
        resolution = _steps_text(sol) or path.clarify_hint
        title = str(sol.get("title") or path.surec_label)
        for i, ask in enumerate(texts, start=1):
            tid = f"RAG-{path.surec}-{i:02d}"
            records.append(
                {
                    "id": tid,
                    "created_at": stamp,
                    "resolved_at": stamp,
                    "kind": "ticket",
                    "status": "resolved",
                    "priority": "Orta",
                    "customer_ask": ask,
                    "resolution_summary": resolution,
                    "recommended_next_step": resolution,
                    "surec": path.surec,
                    "surec_label": path.surec_label,
                    "birim": path.birim,
                    "birim_label": path.birim_label,
                    "modul": path.modul,
                    "modul_label": path.modul_label,
                    "talep_turu": path.talep_turu,
                    "talep_turu_label": path.talep_turu_label,
                    "path_label": (
                        f"{path.talep_turu_label} → {path.birim_label} → "
                        f"{path.modul_label} → {path.surec_label}"
                    ),
                    "solution_ids": [str(sol.get("id") or "")],
                    "messages": [
                        {"role": "user", "content": ask, "at": stamp},
                        {
                            "role": "agent",
                            "content": f"{title}. {resolution}",
                            "at": stamp,
                        },
                    ],
                }
            )
    return records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", action="store_true", help="Chroma indeksini yenile")
    args = parser.parse_args()

    records = build_records()
    OUT_PATH.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records),
        encoding="utf-8",
    )
    by = defaultdict(int)
    for row in records:
        by[row["surec"]] += 1
    print(f"Wrote {len(records)} docs → {OUT_PATH}")
    print(f"Classes covered: {len(by)} / {len(PATHS)}")
    missing = [p.surec for p in PATHS if by[p.surec] == 0]
    if missing:
        print("Missing:", missing)

    if args.index:
        from vector_store import warmup_vector_store

        stats = warmup_vector_store(force=True)
        print("Indexed:", stats)


if __name__ == "__main__":
    main()
