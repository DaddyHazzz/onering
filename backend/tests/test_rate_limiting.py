"""Tests for token-bucket rate limiting middleware."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.core.middleware.request_id import RequestIdMiddleware
from backend.core.middleware.ratelimit import RateLimitMiddleware
from backend.core.ratelimit import RateLimitConfig


class FakeTime:
    def __init__(self):
        self.current = 0.0

    def advance(self, seconds: float):
        self.current += seconds

    def __call__(self):
        return self.current


def test_health_rate_limit_enforced_and_resets():
    fake_time = FakeTime()
    config = RateLimitConfig(enabled=True, per_minute_default=2, burst_default=2)

    test_app = FastAPI()
    test_app.add_middleware(RequestIdMiddleware)
    test_app.add_middleware(RateLimitMiddleware, config=config, time_fn=fake_time)

    @test_app.get("/api/health/db")
    async def health_db():
        return {"ok": True}

    client = TestClient(test_app)

    resp1 = client.get("/api/health/db", headers={"X-User-Id": "user1"})
    resp2 = client.get("/api/health/db", headers={"X-User-Id": "user1"})
    resp3 = client.get("/api/health/db", headers={"X-User-Id": "user1"})

    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert resp3.status_code == 429

    rid = resp3.headers.get("x-request-id")
    payload = resp3.json()
    assert payload["error"]["code"] == "rate_limited"
    assert payload["error"]["request_id"] == rid

    fake_time.advance(61)
    resp4 = client.get("/api/health/db", headers={"X-User-Id": "user1"})
    assert resp4.status_code == 200
