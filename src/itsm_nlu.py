"""ITSM leaf classifier: BERT first, then TF-IDF + logistic regression."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import joblib

from text_norm import fold_tr

ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = ROOT / "models"
BERT_DIR = MODELS_DIR / "bert_model"

SKLEARN_CANDIDATES = (
    (MODELS_DIR / "tfidf_vectorizer.joblib", MODELS_DIR / "logistic_regression_model.joblib"),
    (MODELS_DIR / "itsm_tfidf.joblib", MODELS_DIR / "itsm_logreg.joblib"),
    (ROOT / "models2" / "itsm_tfidf.joblib", ROOT / "models2" / "itsm_logreg.joblib"),
)

MIN_CONFIDENCE = 0.32


def _bert_ready() -> bool:
    weights = BERT_DIR / "model.safetensors"
    legacy = BERT_DIR / "pytorch_model.bin"
    return (BERT_DIR / "config.json").exists() and (weights.exists() or legacy.exists())


def _id2label() -> dict[int, str]:
    config_path = BERT_DIR / "config.json"
    if not config_path.exists():
        return {}
    raw = json.loads(config_path.read_text(encoding="utf-8")).get("id2label") or {}
    return {int(k): str(v) for k, v in raw.items()}


def _label_to_surec(label: object) -> str:
    if label is None:
        return ""
    if isinstance(label, (int, float)) or (isinstance(label, str) and str(label).isdigit()):
        mapped = _id2label().get(int(label), "")
        return mapped
    return str(label)


@lru_cache(maxsize=1)
def _bert_artifacts():
    if not _bert_ready():
        return None
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(str(BERT_DIR), local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(
        str(BERT_DIR),
        local_files_only=True,
    )
    model.eval()
    device = torch.device("cpu")
    model.to(device)
    return tokenizer, model, device


@lru_cache(maxsize=1)
def _sklearn_artifacts():
    for vectorizer_path, model_path in SKLEARN_CANDIDATES:
        if vectorizer_path.exists() and model_path.exists():
            try:
                return joblib.load(vectorizer_path), joblib.load(model_path)
            except Exception:
                continue
    return None, None


def nlu_backend() -> str:
    if _bert_ready():
        try:
            if _bert_artifacts() is not None:
                return "bert"
        except Exception as exc:
            print(f"[itsm_nlu] BERT load failed, sklearn fallback: {exc}")
    vectorizer, model = _sklearn_artifacts()
    if vectorizer is not None and model is not None:
        return "sklearn"
    return "none"


def model_available() -> bool:
    return nlu_backend() != "none"


def _predict_bert(text: str) -> dict:
    import torch

    packed = _bert_artifacts()
    if packed is None:
        return {"surec": "", "confidence": 0.0, "top": [], "backend": "none"}
    tokenizer, model, device = packed
    encoded = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        max_length=256,
        padding=True,
    )
    encoded = {key: value.to(device) for key, value in encoded.items()}
    with torch.no_grad():
        logits = model(**encoded).logits
        probs = torch.softmax(logits, dim=-1)[0]
    ranked = sorted(
        ((int(i), float(p)) for i, p in enumerate(probs.tolist())),
        key=lambda item: item[1],
        reverse=True,
    )
    top = [(_label_to_surec(idx), score) for idx, score in ranked[:3]]
    surec, confidence = top[0] if top else ("", 0.0)
    return {"surec": surec, "confidence": confidence, "top": top, "backend": "bert"}


def _predict_sklearn(text: str) -> dict:
    vectorizer, model = _sklearn_artifacts()
    cleaned = " ".join(fold_tr(text or "").split())
    if not cleaned or vectorizer is None or model is None:
        return {"surec": "", "confidence": 0.0, "top": [], "backend": "none"}
    matrix = vectorizer.transform([cleaned])
    if not hasattr(model, "predict_proba"):
        label = _label_to_surec(model.predict(matrix)[0])
        return {
            "surec": label,
            "confidence": 1.0,
            "top": [(label, 1.0)],
            "backend": "sklearn",
        }
    proba = model.predict_proba(matrix)[0]
    ranked = sorted(zip(model.classes_, proba), key=lambda item: item[1], reverse=True)
    top = [(_label_to_surec(label), float(score)) for label, score in ranked[:3]]
    surec, confidence = top[0] if top else ("", 0.0)
    return {"surec": surec, "confidence": confidence, "top": top, "backend": "sklearn"}


def predict_surec(text: str) -> dict:
    """Predict taxonomy surec label. Empty only if no usable model or blank text."""
    raw = (text or "").strip()
    if not raw:
        return {"surec": "", "confidence": 0.0, "top": [], "backend": "none"}
    backend = nlu_backend()
    if backend == "bert":
        return _predict_bert(raw)
    if backend == "sklearn":
        return _predict_sklearn(raw)
    return {"surec": "", "confidence": 0.0, "top": [], "backend": "none"}
