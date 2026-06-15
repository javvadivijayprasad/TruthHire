"""Webhook delivery retry/backoff (S10 / TH-024)."""
import asyncio
from app.webhooks import deliver


class FakeResp:
    def __init__(self, status): self.status_code = status


class FakeClient:
    def __init__(self, statuses): self.statuses = list(statuses); self.calls = 0
    async def post(self, url, json=None):
        i = min(self.calls, len(self.statuses) - 1); self.calls += 1
        s = self.statuses[i]
        if s == "raise":
            raise RuntimeError("network")
        return FakeResp(s)
    async def aclose(self): pass


def test_success_first_try():
    c = FakeClient([200])
    ok = asyncio.run(deliver("u", {}, client=c, base_delay=0))
    assert ok and c.calls == 1


def test_retries_then_succeeds():
    c = FakeClient([500, "raise", 200])
    ok = asyncio.run(deliver("u", {}, retries=3, client=c, base_delay=0))
    assert ok and c.calls == 3


def test_gives_up_after_retries():
    c = FakeClient([500, 500, 500])
    ok = asyncio.run(deliver("u", {}, retries=3, client=c, base_delay=0))
    assert not ok and c.calls == 3
