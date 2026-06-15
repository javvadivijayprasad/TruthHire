"""Pluggable OSINT signal providers (Phase 2: S4, S7-S9).

Each provider implements check(candidate) -> list[Signal]. Offline (default)
implementations read a provider-specific slice from candidate.osint, so the whole
pipeline runs and is fully testable without API keys. Live implementations would
populate the same slices from real APIs (GitHub, Holehe, SerpAPI, OpenCorporates,
Twilio). See app/providers/base.py.
"""
from .base import Signal, Provider, default_registry  # noqa: F401
