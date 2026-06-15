"""Sliding-window rate limiter, per API-key/org (S3 / TH-015)."""
from __future__ import annotations
import time
from collections import defaultdict, deque
from typing import Deque, Dict

from .config import settings


class RateLimiter:
    def __init__(self, per_sec: int = None, window: float = 1.0):
        self.per_sec = per_sec or settings.rate_limit_per_sec
        self.window = window
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        q = self._hits[key]
        while q and now - q[0] > self.window:
            q.popleft()
        if len(q) >= self.per_sec:
            return False
        q.append(now)
        return True


limiter = RateLimiter()
