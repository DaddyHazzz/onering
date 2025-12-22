"""Tests for soft rate limiting middleware."""

from fastapi.testclient import TestClient

from backend.main import app


class FakeTime:
    def __init__(self):
        self.current = 0.0

    def advance(self, seconds: float):
        self.current += seconds

    def __call__(self):
        return self.current


def test_health_rate_limit_enforced_and_resets():
    client = TestClient(app)

    # Prime middleware to expose limiters on app.state
    client.get("/api/health/db")
    limiters = getattr(app.state, "rate_limiters", {})
    health_limiter = limiters.get("health")
    assert health_limiter is not None

    fake_time = FakeTime()
    health_limiter.limit = 2
    health_limiter.windows.clear()
    health_limiter.time_fn = fake_time

    resp1 = client.get("/api/health/db")
    resp2 = client.get("/api/health/db")
    resp3 = client.get("/api/health/db")

    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert resp3.status_code == 429

    rid = resp3.headers.get("x-request-id")
    payload = resp3.json()
    assert payload["error"]["code"] == "rate_limit"
    assert payload["error"]["request_id"] == rid

    fake_time.advance(61)
    resp4 = client.get("/api/health/db")
    assert resp4.status_code == 200
