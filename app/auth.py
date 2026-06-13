"""API-key authentication (TH-003).

Keys are stored as SHA-256 hashes, never in plaintext. For Sprint 1 the key
store is an in-memory dict seeded from the TRUTHHIRE_API_KEYS env var
(comma-separated). Phase 1 (TH-005) replaces this with a DB-backed store.
"""
from __future__ import annotations

import hashlib
import os
from typing import Dict

from fastapi import Header, HTTPException, status


def hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _load_keys() -> Dict[str, str]:
    """Return {hashed_key: org_label}. Seeds a sandbox key if none configured."""
    store: Dict[str, str] = {}
    raw = os.environ.get("TRUTHHIRE_API_KEYS", "")
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        if ":" in item:
            key, label = item.split(":", 1)
        else:
            key, label = item, "org"
        store[hash_key(key.strip())] = label.strip()
    if not store:  # dev/sandbox default
        store[hash_key("th_sandbox_demo_key")] = "sandbox"
    return store


API_KEYS = _load_keys()


def require_api_key(authorization: str = Header(default="")) -> str:
    """FastAPI dependency. Expects 'Authorization: Bearer <key>'. Returns org label."""
    token = authorization
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "UNAUTHORIZED", "message": "Missing API key"},
        )
    org = API_KEYS.get(hash_key(token))
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "UNAUTHORIZED", "message": "Invalid API key"},
        )
    return org
