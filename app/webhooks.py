"""Async webhook delivery with retry/backoff (S10 / TH-024)."""
from __future__ import annotations
import asyncio
from typing import Any, Dict

try:
    import httpx
except Exception:  # pragma: no cover
    httpx = None


async def deliver(url: str, payload: Dict[str, Any], retries: int = 3,
                  base_delay: float = 0.5, client=None) -> bool:
    """POST payload to url with exponential backoff. Returns True on 2xx.
    `client` may be injected for testing (an object with async post())."""
    if client is None and httpx is None:  # pragma: no cover
        return False
    owns = client is None
    if owns:
        client = httpx.AsyncClient(timeout=10)
    try:
        for attempt in range(retries):
            try:
                resp = await client.post(url, json=payload)
                if 200 <= resp.status_code < 300:
                    return True
            except Exception:
                pass
            if attempt < retries - 1:
                await asyncio.sleep(base_delay * (2 ** attempt))
        return False
    finally:
        if owns:
            await client.aclose()
