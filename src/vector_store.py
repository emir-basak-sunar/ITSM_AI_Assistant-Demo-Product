"""ChromaDB vector store for resolved ITSM tickets (persistent RAG index)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import cast

import chromadb
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

ROOT = Path(__file__).resolve().parent.parent
STORE_PATH = ROOT / "data" / "chroma_store"
COLLECTION_NAME = "resolved_tickets"
EMBED_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

_client: chromadb.PersistentClient | None = None
_collection = None
_sync_mtime: float = -1.0
_warmed_up: bool = False
_stats_cache: dict | None = None
_embedder: "CachedSentenceTransformerEmbedding | None" = None


class CachedSentenceTransformerEmbedding(EmbeddingFunction[Documents]):
    """Process-wide singleton — model yalnızca bir kez belleğe alınır."""

    def __init__(self, model_name: str) -> None:
        self._model_name = model_name
        self._model = None

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self._model_name)
        vectors = self._model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return cast(Embeddings, vectors.tolist())

    def __call__(self, input: Documents) -> Embeddings:
        return self.embed(list(input))


def _embedder_instance() -> CachedSentenceTransformerEmbedding:
    global _embedder
    if _embedder is None:
        _embedder = CachedSentenceTransformerEmbedding(EMBED_MODEL)
    return _embedder


def _client_instance() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        STORE_PATH.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(path=str(STORE_PATH))
    return _client


def get_collection():
    """Chroma koleksiyonu — embedding Chroma'ya değil, bizim singleton'a bırakıldı."""
    global _collection
    if _collection is None:
        _collection = _client_instance().get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def _tickets_mtime() -> float:
    from tickets import TICKETS_PATH

    if not TICKETS_PATH.exists():
        return 0.0
    return TICKETS_PATH.stat().st_mtime


def _resolved_tickets() -> list[dict]:
    from ticket_rag import resolved_tickets

    return resolved_tickets()


def _ticket_document(ticket: dict) -> str:
    parts = [
        str(ticket.get("customer_ask") or ""),
        str(ticket.get("path_label") or ""),
        str(ticket.get("surec_label") or ""),
        str(ticket.get("birim_label") or ""),
        str(ticket.get("recommended_next_step") or ""),
        str(ticket.get("resolution_summary") or ""),
        str(ticket.get("handoff_notes") or ""),
    ]
    for bullet in ticket.get("summary_bullets") or []:
        parts.append(str(bullet))
    for followup in ticket.get("followups") or []:
        if isinstance(followup, dict):
            parts.append(str(followup.get("text") or ""))
        else:
            parts.append(str(followup))
    for message in ticket.get("messages") or []:
        if isinstance(message, dict):
            parts.append(str(message.get("content") or ""))
    return " ".join(part.strip() for part in parts if part and str(part).strip())


def _refresh_stats_cache() -> dict:
    global _stats_cache
    tickets = _resolved_tickets()
    try:
        count = get_collection().count() if tickets else 0
    except Exception:
        count = 0
    _stats_cache = {
        "engine": "chromadb",
        "embed_model": EMBED_MODEL,
        "indexed_tickets": count,
        "resolved_tickets": len(tickets),
        "store_path": str(STORE_PATH),
        "warmed_up": _warmed_up,
    }
    return _stats_cache


def warmup_vector_store(*, force: bool = False) -> dict:
    """API startup: model bir kez yüklenir, indeks senkronize edilir."""
    global _warmed_up
    if _warmed_up and not force:
        return _stats_cache or _refresh_stats_cache()

    _embedder_instance().embed(["warmup"])
    indexed = sync_resolved_tickets(force=force)
    _warmed_up = True
    stats = _refresh_stats_cache()
    stats["indexed_on_warmup"] = indexed
    return stats


def sync_resolved_tickets(tickets: list[dict] | None = None, *, force: bool = False) -> int:
    """Upsert resolved tickets into ChromaDB. Returns indexed count."""
    global _sync_mtime, _collection, _stats_cache

    if tickets is None:
        tickets = _resolved_tickets()

    mtime = _tickets_mtime()
    if not force and _sync_mtime == mtime and tickets:
        existing = get_collection().count()
        if existing >= len(tickets):
            return existing

    if force:
        try:
            _client_instance().delete_collection(COLLECTION_NAME)
        except Exception:
            pass
        _collection = None

    collection = get_collection()

    if not tickets:
        _sync_mtime = mtime
        _stats_cache = None
        return 0

    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict] = []

    for ticket in tickets:
        ticket_id = str(ticket.get("id") or "").strip()
        if not ticket_id:
            continue
        doc = _ticket_document(ticket)
        if not doc.strip():
            continue
        ids.append(ticket_id)
        documents.append(doc)
        metadatas.append(
            {
                "surec": str(ticket.get("surec") or ""),
                "birim": str(ticket.get("birim") or ""),
                "ticket_id": ticket_id,
            }
        )

    if not ids:
        _sync_mtime = mtime
        _stats_cache = None
        return 0

    embeddings = _embedder_instance().embed(documents)
    collection.upsert(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
    )
    _sync_mtime = mtime
    _stats_cache = None
    return len(ids)


def _ticket_by_id(ticket_id: str) -> dict | None:
    for ticket in _resolved_tickets():
        if str(ticket.get("id") or "") == ticket_id:
            return ticket
    return None


def query_similar(
    query: str,
    *,
    surec: str = "",
    birim: str = "",
    limit: int = 2,
    min_similarity: float = 0.35,
) -> list[dict]:
    """Semantic search over resolved tickets. Returns ticket dicts with scores."""
    if not _warmed_up:
        warmup_vector_store()

    tickets = _resolved_tickets()
    if not tickets:
        return []

    sync_resolved_tickets(tickets)
    collection = get_collection()
    if collection.count() == 0:
        return []

    query_text = (query or "").strip()
    if not query_text:
        return []

    query_embedding = _embedder_instance().embed([query_text])
    raw = collection.query(
        query_embeddings=query_embedding,
        n_results=min(max(limit * 3, limit), collection.count()),
        include=["metadatas", "distances"],
    )

    ids = (raw.get("ids") or [[]])[0]
    distances = (raw.get("distances") or [[]])[0]
    metadatas = (raw.get("metadatas") or [[]])[0]

    ranked: list[tuple[float, dict]] = []
    for ticket_id, distance, meta in zip(ids, distances, metadatas):
        meta = meta or {}
        tid = str(meta.get("ticket_id") or ticket_id or "")
        ticket = _ticket_by_id(tid)
        if not ticket:
            continue

        similarity = max(0.0, 1.0 - float(distance))
        if similarity < min_similarity:
            continue

        bonus = 0.0
        if surec and str(meta.get("surec") or "") == surec:
            bonus += 0.06
        if birim and str(meta.get("birim") or "") == birim:
            bonus += 0.03

        score = min(1.0, similarity + bonus)
        ranked.append((score, ticket))

    ranked.sort(key=lambda item: item[0], reverse=True)

    results: list[dict] = []
    seen: set[str] = set()
    for score, ticket in ranked:
        tid = str(ticket.get("id") or "")
        if tid in seen:
            continue
        seen.add(tid)
        results.append(
            {
                "ticket": ticket,
                "score": round(score, 3),
                "similarity_pct": round(score * 100),
            }
        )
        if len(results) >= limit:
            break
    return results


def reset_store() -> None:
    """Drop collection and clear sync cache (called when tickets change)."""
    global _collection, _sync_mtime, _stats_cache
    try:
        _client_instance().delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    _collection = None
    _sync_mtime = -1.0
    _stats_cache = None


def store_stats(*, refresh: bool = False) -> dict:
    """Vector store health info — uses cache unless refresh requested."""
    if _stats_cache is not None and not refresh:
        return dict(_stats_cache)
    if not _warmed_up:
        return {
            "engine": "chromadb",
            "embed_model": EMBED_MODEL,
            "indexed_tickets": 0,
            "resolved_tickets": len(_resolved_tickets()),
            "store_path": str(STORE_PATH),
            "warmed_up": False,
        }
    return _refresh_stats_cache()
