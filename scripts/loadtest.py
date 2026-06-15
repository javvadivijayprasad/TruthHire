"""Tiny concurrent load test: python scripts/loadtest.py [N] [URL].
Fires N concurrent /verify calls and reports throughput + latency percentiles."""
import sys, time, statistics, concurrent.futures as cf
import httpx

N = int(sys.argv[1]) if len(sys.argv) > 1 else 200
URL = sys.argv[2] if len(sys.argv) > 2 else "http://127.0.0.1:8000"
H = {"Authorization": "Bearer th_sandbox_demo_key"}
BODY = {"candidate": {"name": "Load Test", "age": 24, "total_claimed_years": 15},
        "options": {"layers": ["timeline"]}}


def one(_):
    t = time.perf_counter()
    r = httpx.post(f"{URL}/verify", headers=H, json=BODY, timeout=30)
    return r.status_code, (time.perf_counter() - t) * 1000


if __name__ == "__main__":
    t0 = time.perf_counter()
    with cf.ThreadPoolExecutor(max_workers=50) as ex:
        res = list(ex.map(one, range(N)))
    dur = time.perf_counter() - t0
    lat = sorted(ms for _, ms in res)
    ok = sum(1 for s, _ in res if s == 200)
    print(f"{N} requests in {dur:.2f}s = {N/dur:.0f} req/s | {ok}/{N} ok")
    print(f"latency ms: p50={statistics.median(lat):.1f} p95={lat[int(.95*len(lat))-1]:.1f} max={lat[-1]:.1f}")
