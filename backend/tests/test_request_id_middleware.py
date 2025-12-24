from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from backend.core.middleware.request_id import RequestIdMiddleware


def _make_app():
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)

    @app.get("/")
    async def root(request: Request):
        return {"request_id": getattr(request.state, "request_id", None)}

    return app


def test_generates_request_id_when_missing():
    app = _make_app()
    client = TestClient(app)

    resp = client.get("/")
    assert resp.status_code == 200
    rid_header = resp.headers.get("x-request-id")
    body_rid = resp.json().get("request_id")

    assert rid_header
    assert body_rid
    assert rid_header == body_rid


def test_echoes_provided_request_id():
    app = _make_app()
    client = TestClient(app)

    provided = "test-rid-123"
    resp = client.get("/", headers={"X-Request-Id": provided})

    assert resp.status_code == 200
    assert resp.headers.get("x-request-id") == provided
    assert resp.json().get("request_id") == provided
