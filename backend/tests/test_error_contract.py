"""Tests for normalized error responses."""

from fastapi.testclient import TestClient

from backend.main import app
from backend.core.middleware.request_id import RequestIdMiddleware
from backend.core.middleware.ratelimit import RateLimitMiddleware
from backend.core.ratelimit import RateLimitConfig
from fastapi import FastAPI


def test_validation_error_has_standard_shape():
    client = TestClient(app)
    resp = client.get("/v1/analytics/leaderboard", params={"metric": "invalid"})
    assert resp.status_code == 400
    body = resp.json()
    rid = resp.headers.get("x-request-id")
    assert body["error"]["code"] == "validation_error"
    assert body["error"]["request_id"] == rid


def test_permission_error_normalized():
    client = TestClient(app)
    create_resp = client.post(
        "/v1/collab/drafts",
        headers={"X-User-Id": "owner"},
        json={"title": "draft", "platform": "twitter", "initial_segment": "hi"},
    )
    draft_id = create_resp.json()["data"]["draft_id"]

    append_resp = client.post(
        f"/v1/collab/drafts/{draft_id}/segments",
        headers={"X-User-Id": "other"},
        json={"content": "new", "idempotency_key": "k1"},
    )
    assert append_resp.status_code == 403
    body = append_resp.json()
    rid = append_resp.headers.get("x-request-id")
    assert body["error"]["code"] == "forbidden"
    assert body["error"]["request_id"] == rid


def test_rate_limit_error_code():
    test_app = FastAPI()
    config = RateLimitConfig(enabled=True, per_minute_default=1, burst_default=1)
    test_app.add_middleware(RequestIdMiddleware)
    test_app.add_middleware(RateLimitMiddleware, config=config)

    @test_app.get("/v1/collab/drafts")
    async def drafts():
        return {"ok": True}

    client = TestClient(test_app)

    first = client.get("/v1/collab/drafts", headers={"X-User-Id": "rl-user"})
    assert first.status_code == 200

    second = client.get("/v1/collab/drafts", headers={"X-User-Id": "rl-user"})
    assert second.status_code == 429
    assert second.json()["error"]["code"] == "rate_limited"
