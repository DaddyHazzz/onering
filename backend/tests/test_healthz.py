import types

from fastapi.testclient import TestClient

import backend.api.health as health_api
from backend.main import app

client = TestClient(app)


def test_healthz_always_ok():
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json().get("status") == "ok"


def test_readyz_ok_with_mocked_db(monkeypatch):
    class FakeConn:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def exec_driver_sql(self, query):
            return None

    class FakeEngine:
        def connect(self):
            return FakeConn()

    class FakeInspector:
        def __init__(self, tables):
            self.tables = set(tables)

        def has_table(self, name):
            return name in self.tables

    monkeypatch.setattr(health_api, "get_engine", lambda: FakeEngine())
    monkeypatch.setattr(health_api, "inspect", lambda engine: FakeInspector([
        "drafts",
        "draft_segments",
        "draft_collaborators",
        "ring_passes",
        "audit_events",
    ]))

    resp = client.get("/readyz")
    assert resp.status_code == 200
    assert resp.json().get("status") == "ok"


def test_readyz_handles_db_down(monkeypatch):
    def boom():
        raise RuntimeError("db down")

    monkeypatch.setattr(health_api, "get_engine", boom)

    resp = client.get("/readyz")
    body = resp.json()
    assert resp.status_code == 503
    assert body.get("status") == "error"
    assert "database" in body.get("detail", "")
