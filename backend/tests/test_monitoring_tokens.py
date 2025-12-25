from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import insert

from backend.core.config import settings
from backend.core.database import create_all_tables, get_db_session, publish_events
from backend.main import app

client = TestClient(app)


def _insert_publish_event(created_at, token_mode="shadow", issued=0, pending=10, reason_code="PENDING"):
    return {
        "id": f"evt-{created_at.timestamp()}",
        "user_id": "u1",
        "platform": "x",
        "content_hash": "hash",
        "published_at": created_at,
        "platform_post_id": "post-1",
        "enforcement_request_id": "req-1",
        "enforcement_receipt_id": "rec-1",
        "qa_status": "PASS",
        "violation_codes": [],
        "audit_ok": True,
        "metadata": {"issuance_latency_ms": 120},
        "token_mode": token_mode,
        "token_issued_amount": issued,
        "token_pending_amount": pending,
        "token_reason_code": reason_code,
        "token_ledger_id": None,
        "token_pending_id": "pend-1",
    }


def test_monitoring_tokens_endpoints(monkeypatch):
    create_all_tables()
    now = datetime.now(timezone.utc)
    with get_db_session() as session:
        session.execute(insert(publish_events).values(**_insert_publish_event(now)))
        session.execute(
            insert(publish_events).values(
                **_insert_publish_event(now - timedelta(hours=1), token_mode="live", issued=10, pending=0, reason_code="ISSUED")
            )
        )

    monkeypatch.setattr(settings, "ADMIN_KEY", "test-key")
    monkeypatch.setattr(settings, "ADMIN_AUTH_MODE", "legacy")

    recent = client.get(
        "/v1/monitoring/tokens/recent?limit=10",
        headers={"X-Admin-Key": "test-key"},
    )
    assert recent.status_code == 200
    items = recent.json().get("items", [])
    assert len(items) >= 2
    assert items[0]["event_id"].startswith("evt-")

    metrics = client.get(
        "/v1/monitoring/tokens/metrics",
        headers={"X-Admin-Key": "test-key"},
    )
    assert metrics.status_code == 200
    payload = metrics.json()
    assert payload["metrics"]["total_pending"] >= 0
    assert payload["metrics"]["total_issued"] >= 0
