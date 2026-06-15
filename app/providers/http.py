"""Tiny HTTP helper for live provider calls (sync). Patchable in tests."""
from __future__ import annotations
from typing import Any, Optional

try:
    import httpx
except Exception:  # pragma: no cover
    httpx = None


def get_json(url: str, params=None, auth=None, headers=None, timeout: float = 10) -> Optional[Any]:
    if httpx is None:  # pragma: no cover
        return None
    with httpx.Client(timeout=timeout) as c:
        r = c.get(url, params=params, auth=auth, headers=headers)
        r.raise_for_status()
        return r.json()
