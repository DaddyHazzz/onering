import pytest
from uuid import uuid4
from fastapi.testclient import TestClient

from backend.main import app
from backend.features.collaboration.service import (
    create_draft,
    append_segment,
    clear_store,
)
from backend.models.collab import CollabDraftRequest, SegmentAppendRequest
from backend.core.ratelimit import InMemoryRateLimiter, RateLimitConfig
import backend.api.ai as ai_api


@pytest.fixture(autouse=True)
def reset_state():
    clear_store()
    # Fresh rate limiter per test to avoid token carry-over
    app.state.rate_limiter = InMemoryRateLimiter(RateLimitConfig(enabled=True, per_minute_default=1000, burst_default=1000))
    yield
    clear_store()
    app.state.rate_limiter = InMemoryRateLimiter(RateLimitConfig(enabled=True, per_minute_default=1000, burst_default=1000))


def _make_draft(with_segment: bool = True):
    user_id = str(uuid4())
    draft = create_draft(user_id, CollabDraftRequest(title="AI Test", platform="x", initial_segment="First" if with_segment else None))
    if with_segment and not draft.segments:
        append_segment(draft.draft_id, user_id, SegmentAppendRequest(content="seed", idempotency_key=str(uuid4())))
    return user_id, draft


def _client():
    return TestClient(app)


def test_ring_holder_can_request_mutative_modes():
    user_id, draft = _make_draft(with_segment=True)
    client = _client()

    resp = client.post(
        "/v1/ai/suggest",
        json={"draft_id": draft.draft_id, "mode": "next", "platform": "x"},
        headers={"X-User-Id": user_id},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["mode"] == "next"
    assert body["data"]["ring_holder"] is True
    assert body["data"]["content"]


def test_non_holder_blocked_for_mutative_modes():
    holder_id, draft = _make_draft(with_segment=True)
    non_holder = str(uuid4())
    client = _client()

    resp = client.post(
        "/v1/ai/suggest",
        json={"draft_id": draft.draft_id, "mode": "rewrite"},
        headers={"X-User-Id": non_holder},
    )

    assert resp.status_code == 403
    payload = resp.json()
    assert payload["error"]["code"] == "ring_required"


def test_commentary_allowed_for_non_holder():
    holder_id, draft = _make_draft(with_segment=True)
    other_id = str(uuid4())
    client = _client()

    resp = client.post(
        "/v1/ai/suggest",
        json={"draft_id": draft.draft_id, "mode": "commentary", "platform": "blog"},
        headers={"X-User-Id": other_id},
    )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["ring_holder"] is False
    assert data["content"]


def test_rate_limit_enforced(monkeypatch):
    # Tighten limits for this test only
    monkeypatch.setattr(ai_api, "AI_RATE_LIMIT_PER_MINUTE", 2)
    monkeypatch.setattr(ai_api, "AI_RATE_LIMIT_BURST", 2)
    app.state.rate_limiter = InMemoryRateLimiter(RateLimitConfig(enabled=True, per_minute_default=1, burst_default=1))

    user_id, draft = _make_draft(with_segment=True)
    client = _client()

    first = client.post(
        "/v1/ai/suggest",
        json={"draft_id": draft.draft_id, "mode": "next"},
        headers={"X-User-Id": user_id},
    )
    second = client.post(
        "/v1/ai/suggest",
        json={"draft_id": draft.draft_id, "mode": "summary"},
        headers={"X-User-Id": user_id},
    )
    third = client.post(
        "/v1/ai/suggest",
        json={"draft_id": draft.draft_id, "mode": "summary"},
        headers={"X-User-Id": user_id},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429
    payload = third.json()
    assert payload["error"]["code"] == "rate_limited"
