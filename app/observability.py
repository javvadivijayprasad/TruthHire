"""Metrics, health, structured logging, request timing (S24)."""
from __future__ import annotations
import logging
import time
from collections import defaultdict
from sqlalchemy import text
from .db import engine

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(name)s %(message)s')
log = logging.getLogger("truthhire")

_metrics = {"requests": 0, "by_status": defaultdict(int), "by_path": defaultdict(int),
            "latency_ms_sum": 0.0}


def record(path: str, status: int, ms: float):
    _metrics["requests"] += 1
    _metrics["by_status"][str(status)] += 1
    _metrics["by_path"][path] += 1
    _metrics["latency_ms_sum"] += ms


def snapshot() -> dict:
    n = _metrics["requests"] or 1
    return {"requests": _metrics["requests"],
            "avg_latency_ms": round(_metrics["latency_ms_sum"] / n, 2),
            "by_status": dict(_metrics["by_status"]),
            "by_path": dict(sorted(_metrics["by_path"].items(), key=lambda x: -x[1])[:10])}


def db_ok() -> bool:
    try:
        with engine.connect() as c:
            c.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
