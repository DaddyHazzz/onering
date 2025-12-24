from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.core.middleware.request_id import RequestIdMiddleware
from backend.core.middleware.ratelimit import RateLimitMiddleware
from backend.core.ratelimit import build_rate_limit_config_from_env


def _make_app(env_overrides: dict):
    config = build_rate_limit_config_from_env(env_overrides)
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(RateLimitMiddleware, config=config)

    @app.get("/v1/collab/drafts")
    async def read_drafts():
        return {"ok": True}

    @app.post("/v1/collab/drafts")
    async def create_draft():
        return {"ok": True}

    return app


def test_ratelimit_disabled_by_default():
    env = {"RATE_LIMIT_ENABLED": "false", "RATE_LIMIT_PER_MINUTE_DEFAULT": "1", "RATE_LIMIT_BURST_DEFAULT": "1"}
    app = _make_app(env)
    client = TestClient(app)

    # Should allow multiple requests without 429 when disabled
    for _ in range(3):
        resp = client.get("/v1/collab/drafts", headers={"X-User-Id": "user1"})
        assert resp.status_code == 200


def test_ratelimit_blocks_after_limit():
    env = {"RATE_LIMIT_ENABLED": "true", "RATE_LIMIT_PER_MINUTE_DEFAULT": "1", "RATE_LIMIT_BURST_DEFAULT": "1"}
    app = _make_app(env)
    client = TestClient(app)

    first = client.get("/v1/collab/drafts", headers={"X-User-Id": "user1"})
    assert first.status_code == 200

    second = client.get("/v1/collab/drafts", headers={"X-User-Id": "user1"})
    assert second.status_code == 429
    assert second.json()["error"]["code"] == "rate_limited"
    assert second.headers.get("Retry-After")
    assert second.headers.get("X-RateLimit-Limit") == "1"
    assert second.headers.get("X-RateLimit-Remaining") == "0"
    assert second.headers.get("X-RateLimit-Reset") == "60"


def test_mutation_policy_stricter():
    env = {"RATE_LIMIT_ENABLED": "true", "RATE_LIMIT_PER_MINUTE_DEFAULT": "2", "RATE_LIMIT_BURST_DEFAULT": "2"}
    app = _make_app(env)
    client = TestClient(app)

    # Mutation endpoints use stricter policy (half of defaults), so capacity 1, rate ~1/second
    first = client.post("/v1/collab/drafts", headers={"X-User-Id": "user2"})
    assert first.status_code == 200

    second = client.post("/v1/collab/drafts", headers={"X-User-Id": "user2"})
    assert second.status_code == 429
