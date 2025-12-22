"""Tests for normalized error responses."""

from fastapi.testclient import TestClient

from backend.main import app


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
        params={"user_id": "owner"},
        json={"title": "draft", "platform": "twitter", "initial_segment": "hi"},
    )
    draft_id = create_resp.json()["data"]["draft_id"]

    append_resp = client.post(
        f"/v1/collab/drafts/{draft_id}/segments",
        params={"user_id": "other"},
        json={"content": "new", "idempotency_key": "k1"},
    )
    assert append_resp.status_code == 403
    body = append_resp.json()
    rid = append_resp.headers.get("x-request-id")
    assert body["error"]["code"] == "forbidden"
    assert body["error"]["request_id"] == rid
