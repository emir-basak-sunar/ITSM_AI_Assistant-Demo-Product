"""Persistent API sessions with in-memory cache + sliding expiry."""

from __future__ import annotations

import json
import secrets
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SESSIONS_PATH = ROOT / "data" / "sessions.json"
SESSION_TTL_DAYS = 30

_CACHE: dict[str, dict] | None = None


def _now() -> datetime:
    return datetime.now()


def _load_raw() -> dict[str, dict]:
    if not SESSIONS_PATH.exists():
        return {}
    try:
        data = json.loads(SESSIONS_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_raw(data: dict[str, dict]) -> None:
    SESSIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = SESSIONS_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(SESSIONS_PATH)


def init_sessions() -> int:
    """Load sessions from disk into memory (call on API startup)."""
    global _CACHE
    _CACHE = _load_raw()
    removed = purge_expired(persist=True)
    return len(_CACHE) - removed if _CACHE else 0


def _cache() -> dict[str, dict]:
    global _CACHE
    if _CACHE is None:
        _CACHE = _load_raw()
    return _CACHE


def _persist() -> None:
    _save_raw(_cache())


def _is_expired(row: dict) -> bool:
    expires_at = str(row.get("expires_at") or "")
    if not expires_at:
        return False
    try:
        return datetime.fromisoformat(expires_at) <= _now()
    except ValueError:
        return False


def _user_from_row(row: dict) -> dict[str, str] | None:
    user = row.get("user")
    if not isinstance(user, dict) or not user.get("email"):
        return None
    return {
        "email": str(user.get("email") or ""),
        "name": str(user.get("name") or ""),
        "role": str(user.get("role") or "user"),
    }


def purge_expired(*, persist: bool = True) -> int:
    store = _cache()
    removed = 0
    for token in list(store.keys()):
        row = store.get(token) or {}
        if _is_expired(row):
            store.pop(token, None)
            removed += 1
    if removed and persist:
        _persist()
    return removed


def load_sessions() -> dict[str, dict[str, str]]:
    purge_expired(persist=True)
    sessions: dict[str, dict[str, str]] = {}
    for token, row in _cache().items():
        user = _user_from_row(row)
        if user:
            sessions[token] = user
    return sessions


def create_session(user: dict[str, str]) -> str:
    token = secrets.token_urlsafe(32)
    now = _now()
    store = _cache()
    store[token] = {
        "user": {
            "email": user["email"],
            "name": user.get("name") or user["email"],
            "role": user.get("role") or "user",
        },
        "created_at": now.isoformat(timespec="seconds"),
        "last_seen_at": now.isoformat(timespec="seconds"),
        "expires_at": (now + timedelta(days=SESSION_TTL_DAYS)).isoformat(timespec="seconds"),
    }
    _persist()
    return token


def touch_session(token: str) -> bool:
    """Sliding window — extend expiry on activity."""
    if not token:
        return False
    store = _cache()
    row = store.get(token)
    if not row or _is_expired(row):
        if row:
            store.pop(token, None)
            _persist()
        return False
    now = _now()
    row["last_seen_at"] = now.isoformat(timespec="seconds")
    row["expires_at"] = (now + timedelta(days=SESSION_TTL_DAYS)).isoformat(timespec="seconds")
    _persist()
    return True


def get_user(token: str, *, touch: bool = True) -> dict[str, str] | None:
    if not token:
        return None
    store = _cache()
    row = store.get(token)
    if not row:
        return None
    if _is_expired(row):
        store.pop(token, None)
        _persist()
        return None
    if touch:
        touch_session(token)
        row = store.get(token) or row
    return _user_from_row(row)


def session_expires_at(token: str) -> str | None:
    row = _cache().get(token or "")
    if not row:
        return None
    return str(row.get("expires_at") or "") or None


def delete_session(token: str) -> None:
    if not token:
        return
    store = _cache()
    if token not in store:
        return
    store.pop(token, None)
    _persist()
