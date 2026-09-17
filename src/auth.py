"""Local JSONL account store for demo authentication."""

from __future__ import annotations

import hashlib
import json
import secrets
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
USERS_PATH = ROOT / "data" / "users.jsonl"

DEFAULT_USERS = (
    {
        "email": "admin@kurumsal.local",
        "password": "admin123",
        "name": "Yönetici Kullanıcı",
        "role": "admin",
    },
    {
        "email": "kullanici@kurumsal.local",
        "password": "kullanici123",
        "name": "Demo Kullanıcı",
        "role": "user",
    },
)


def _hash_password(password: str, salt: str) -> str:
    payload = f"{salt}:{password}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _ensure_seed() -> None:
    if USERS_PATH.exists() and USERS_PATH.stat().st_size > 0:
        return
    USERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with USERS_PATH.open("w", encoding="utf-8") as handle:
        for row in DEFAULT_USERS:
            salt = secrets.token_hex(8)
            record = {
                "email": row["email"].lower(),
                "name": row["name"],
                "role": row["role"],
                "salt": salt,
                "password_hash": _hash_password(row["password"], salt),
                "created_at": datetime.now().isoformat(timespec="seconds"),
            }
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_users() -> list[dict]:
    _ensure_seed()
    users: list[dict] = []
    for line in USERS_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            users.append(json.loads(line))
    return users


def authenticate(email: str, password: str) -> dict | None:
    email = (email or "").strip().lower()
    password = password or ""
    if not email or not password:
        return None
    for user in load_users():
        if user.get("email") != email:
            continue
        salt = str(user.get("salt") or "")
        expected = str(user.get("password_hash") or "")
        if _hash_password(password, salt) == expected:
            return {
                "email": user["email"],
                "name": user.get("name") or user["email"],
                "role": user.get("role") or "user",
            }
    return None
