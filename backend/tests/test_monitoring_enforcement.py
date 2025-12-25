from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import insert

from backend.core.config import settings
from backend.core.database import audit_agent_decisions, create_all_tables, get_db_session
from backend.main import app

client = TestClient(app)


def _insert_decision(created_at, qa_status="PASS", mode="advisory"):
    return {
        "request_id": f"req-{qa_status}",
        "draft_id": None,
        "ring_id": None,
        "turn_id": None,
        "user_id": "u",
        "agent_name": "qa_gatekeeper",
        "agent_version": "v1",
        "contract_version": "10.1",
        "policy_version": "10.1",
        "input_hash": "h1",
        "output_hash": "h2",
        "prompt_hash": "h3",
        "decision_json": {
            "meta": {"latency_ms": 12},
            "output": {
                "mode": mode,
                "qa": {"status": qa_status, "violation_codes": []},
                "receipt": {"receipt_id": f"r-{qa_status}", "expires_at": created_at.isoformat()},
            },
        },
        "status": qa_status,
        "created_at": created_at,
    }


def test_monitoring_recent_and_metrics(monkeypatch):
    create_all_tables()
    now = datetime.now(timezone.utc)
    with get_db_session() as session:
        session.execute(insert(audit_agent_decisions).values(**_insert_decision(now, "PASS", "enforced")))
        session.execute(insert(audit_agent_decisions).values(**_insert_decision(now - timedelta(hours=1), "FAIL", "enforced")))

    monkeypatch.setattr(settings, "ADMIN_KEY", "test-key")
    monkeypatch.setattr(settings, "ADMIN_AUTH_MODE", "legacy")

    recent = client.get(
        "/v1/monitoring/enforcement/recent?limit=10",
        headers={"X-Admin-Key": "test-key"},
    )
    assert recent.status_code == 200
    items = recent.json().get("items", [])
    assert len(items) >= 2
    assert items[0]["mode"] in {"enforced", "advisory", "off", None}

    metrics = client.get(
        "/v1/monitoring/enforcement/metrics",
        headers={"X-Admin-Key": "test-key"},
    )
    assert metrics.status_code == 200
    payload = metrics.json()
    assert payload["metrics"]["qa_blocked"] >= 1
