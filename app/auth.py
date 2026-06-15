"""API-key authentication (TH-003) — DB-backed (api_keys table) via HTTP Bearer.

Keys stored as SHA-256 hashes, never plaintext. Sandbox key `th_sandbox_demo_key`
is seeded when no keys are configured via TRUTHHIRE_API_KEYS (comma-separated
`key:label`)."""
from __future__ import annotations
import hashlib
import os
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .db import SessionLocal
from .models import ApiKey


def hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def add_key(raw: str, label: str) -> None:
    with SessionLocal() as s:
        if not s.get(ApiKey, hash_key(raw)):
            s.add(ApiKey(key_hash=hash_key(raw), label=label)); s.commit()


def lookup_key(raw: str) -> Optional[str]:
    with SessionLocal() as s:
        a = s.get(ApiKey, hash_key(raw))
        return a.label if a else None


def seed_keys() -> None:
    raw = os.environ.get("TRUTHHIRE_API_KEYS", "")
    seeded = False
    for item in raw.split(","):
        item = item.strip()
        if item:
            key, label = (item.split(":", 1) + ["org"])[:2]
            add_key(key.strip(), label.strip()); seeded = True
    if not seeded:
        add_key("th_sandbox_demo_key", "sandbox")


bearer_scheme = HTTPBearer(auto_error=False,
                           description="Paste your API key (sandbox: th_sandbox_demo_key)")


def require_api_key(creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)) -> str:
    token = creds.credentials.strip() if creds and creds.credentials else ""
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail={"error_code": "UNAUTHORIZED", "message": "Missing API key"})
    org = lookup_key(token)
    if org is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail={"error_code": "UNAUTHORIZED", "message": "Invalid API key"})
    return org
