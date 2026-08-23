"""Train full ITSM 27-class süreç classifier (TF-IDF + logreg).

    python src/train_itsm_nlu.py
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
import sys

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

SRC = Path(__file__).resolve().parent
ROOT = SRC.parent
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split

from taxonomy import PATHS, path_by_surec
from text_norm import fold_tr

JSON_PATH = ROOT / "data" / "itsm_dataset.json"

TEMPLATES = (
    "{kw}",
    "{kw} var",
    "{kw} sorunum var",
    "{kw} çalışmıyor",
    "{kw} calismiyor",
    "talep açmak istiyorum {kw}",
    "{kw} için ticket aç",
    "yardım {kw}",
    "{kw} bozuldu",
    "{kw} destek rica ediyorum",
)


def _keyword_examples() -> tuple[list[str], list[str]]:
    texts: list[str] = []
    labels: list[str] = []
    for path in PATHS:
        for keyword in path.keywords:
            for template in TEMPLATES:
                texts.append(fold_tr(template.format(kw=keyword)))
                labels.append(path.surec)
    return texts, labels


def _dataset_examples() -> tuple[list[str], list[str], int]:
    if not JSON_PATH.exists():
        print("No dataset at", JSON_PATH)
        return [], [], 0
    data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    texts = []
    labels = []
    for row in data:
        text = fold_tr(row.get("talep_metni") or "")
        surec_name = row.get("surec_talep_tipi") or ""
        path = path_by_surec(surec_name)
        if path and text:
            texts.append(text)
            labels.append(path.surec)
    return texts, labels, len(data)


def main() -> None:
    kw_texts, kw_labels = _keyword_examples()
    ds_texts, ds_labels, total_ds = _dataset_examples()
    
    print(f"Dataset items: {total_ds} mapped: {len(ds_texts)} | Keyword templates: {len(kw_texts)}")
    
    all_texts = ds_texts + kw_texts
    all_labels = ds_labels + kw_labels
    
    print(f"Class count: {len(set(all_labels))} classes across {len(all_labels)} samples")
    
    x_train, x_test, y_train, y_test = train_test_split(
        all_texts,
        all_labels,
        test_size=0.2,
        random_state=42,
        stratify=all_labels,
    )
    
    vectorizer = TfidfVectorizer(max_features=5000, ngram_range=(1, 2), min_df=1)
    x_train_vec = vectorizer.fit_transform(x_train)
    x_test_vec = vectorizer.transform(x_test)
    
    model = LogisticRegression(max_iter=1000, C=2.0)
    model.fit(x_train_vec, y_train)
    
    pred = model.predict(x_test_vec)
    acc = accuracy_score(y_test, pred)
    print("Test Accuracy:", round(acc, 4))
    print(classification_report(y_test, pred, zero_division=0))
    
    models_dir = ROOT / "models"
    models_dir.mkdir(exist_ok=True)
    joblib.dump(vectorizer, models_dir / "itsm_tfidf.joblib")
    joblib.dump(model, models_dir / "itsm_logreg.joblib")
    print("Saved models/itsm_tfidf.joblib and models/itsm_logreg.joblib successfully!")


if __name__ == "__main__":
    main()
