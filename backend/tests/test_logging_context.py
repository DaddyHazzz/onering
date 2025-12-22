"""Tests for structured logging and request_id propagation."""

import logging
from fastapi.testclient import TestClient

from backend.main import app


def test_request_id_in_response_and_logs(caplog):
    client = TestClient(app)
    with caplog.at_level(logging.INFO, logger="onering"):
        response = client.get("/healthz")
    rid = response.headers.get("x-request-id")
    assert rid
    records = [r for r in caplog.records if getattr(r, "request_id", None) == rid]
    assert records, "Expected logs to contain request_id from response"
    assert len({r.request_id for r in records}) == 1


def test_request_id_in_error_response():
    client = TestClient(app)
    response = client.get("/v1/collab/drafts/non-existent")
    rid = response.headers.get("x-request-id")
    assert response.status_code == 404
    assert rid
    payload = response.json()
    assert payload["error"]["request_id"] == rid
