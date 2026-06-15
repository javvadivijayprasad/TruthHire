"""Settings + sandbox/production separation + global live toggle (S5)."""
from __future__ import annotations
import os


def _flag(name, default="0"):
    return os.environ.get(name, default).strip().lower() in ("1", "true", "yes", "on")


class Settings:
    env = os.environ.get("TRUTHHIRE_ENV", "sandbox")          # sandbox | production
    rate_limit_per_sec = int(os.environ.get("TRUTHHIRE_RATE_LIMIT", "10"))
    default_layers = ["timeline", "digital", "company", "network"]
    live = _flag("TRUTHHIRE_LIVE")     # turn on real API calls for ready providers

    @property
    def is_sandbox(self) -> bool:
        return self.env != "production"


settings = Settings()
