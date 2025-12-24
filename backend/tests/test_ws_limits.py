import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from backend.api import realtime
from backend.core.config import settings


def _build_app():
    app = FastAPI()
    app.include_router(realtime.router)
    return app


def test_ws_per_user_limit(monkeypatch):
    monkeypatch.setattr(settings, "WS_LIMITS_ENABLED", True)
    monkeypatch.setattr(settings, "WS_MAX_SOCKETS_PER_USER", 1)
    monkeypatch.setattr(settings, "WS_MAX_SOCKETS_PER_DRAFT", 5)
    monkeypatch.setattr(settings, "WS_MAX_SOCKETS_GLOBAL", 5)
    monkeypatch.setattr(settings, "WS_ALLOWED_ORIGINS", "*")

    app = _build_app()
    client = TestClient(app)

    with client.websocket_connect("/v1/ws/drafts/test-draft", headers={"X-User-Id": "user-1"}) as ws1:
        first = ws1.receive_json()
        assert first["type"] == "connected"

        with client.websocket_connect("/v1/ws/drafts/test-draft", headers={"X-User-Id": "user-1"}) as ws2:
            error_msg = ws2.receive_json()
            assert error_msg["type"] == "error"
            assert error_msg["code"] == "ws_limit"
            with pytest.raises(WebSocketDisconnect):
                ws2.receive_json()

    # After closing first connection, a new one should succeed
    with client.websocket_connect("/v1/ws/drafts/test-draft", headers={"X-User-Id": "user-1"}) as ws3:
        connected = ws3.receive_json()
        assert connected["type"] == "connected"


def test_ws_payload_limit(monkeypatch):
    monkeypatch.setattr(settings, "WS_LIMITS_ENABLED", True)
    monkeypatch.setattr(settings, "WS_MAX_MESSAGE_BYTES", 10)
    monkeypatch.setattr(settings, "WS_MAX_SOCKETS_PER_USER", 5)
    monkeypatch.setattr(settings, "WS_MAX_SOCKETS_PER_DRAFT", 5)
    monkeypatch.setattr(settings, "WS_MAX_SOCKETS_GLOBAL", 5)
    monkeypatch.setattr(settings, "WS_ALLOWED_ORIGINS", "*")

    app = _build_app()
    client = TestClient(app)

    with client.websocket_connect("/v1/ws/drafts/payload", headers={"X-User-Id": "user-2"}) as ws:
        ws.receive_json()
        # Send oversized payload
        ws.send_text("{" + "a" * 20 + "}")
        error_msg = ws.receive_json()
        assert error_msg["type"] == "error"
        assert error_msg["code"] == "payload_too_large"
        with pytest.raises(WebSocketDisconnect):
            ws.receive_json()
