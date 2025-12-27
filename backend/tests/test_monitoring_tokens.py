from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import insert, text

from backend.core.config import settings
from backend.core.database import create_all_tables, get_db_session, publish_events, publish_event_conflicts, ring_clerk_sync
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
        session.execute(
            text(
                """
                INSERT INTO ring_clerk_sync (user_id, last_sync_at, last_error, last_error_at)
                VALUES (:user_id, :last_sync_at, :last_error, :last_error_at)
                ON CONFLICT (user_id)
                DO UPDATE SET last_sync_at = EXCLUDED.last_sync_at,
                              last_error = EXCLUDED.last_error,
                              last_error_at = EXCLUDED.last_error_at,
                              updated_at = NOW()
                """
            ),
            {
                "user_id": "u1",
                "last_sync_at": now - timedelta(minutes=5),
                "last_error": "clerk_timeout",
                "last_error_at": now - timedelta(minutes=4),
            },
        )
        session.execute(
            insert(publish_event_conflicts).values(
                event_id="evt-conflict",
                user_id="u1",
                reason="idempotent_replay",
                created_at=now,
            )
        )
        session.execute(
            text(
                """
                INSERT INTO ring_ledger (user_id, event_type, reason_code, amount, balance_after, metadata, created_at)
                VALUES (:user_id, 'ADJUSTMENT', 'reconciliation_mismatch', 0, 0, '{}'::jsonb, :created_at)
                """
            ),
            {"user_id": "u1", "created_at": now},
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
    assert payload["metrics"]["reconciliation_mismatches"] >= 1
    assert payload["metrics"]["clerk_sync_failures_24h"] >= 1
    assert payload["metrics"]["idempotency_conflicts_24h"] >= 1
