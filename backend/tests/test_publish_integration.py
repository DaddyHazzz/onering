from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from backend.core.database import get_db, create_all_tables
from backend.features.enforcement.contracts import EnforcementReceipt
from backend.features.tokens import publish as publish_module
from backend.features.tokens.reconciliation import run_reconciliation


@pytest.fixture
def db_session():
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()


def _ensure_publish_events_table(db_session):
    create_all_tables()


def _cleanup_publish_rows(db_session, event_id: str):
    db_session.execute(text("DELETE FROM publish_events WHERE id = :id"), {"id": event_id})
    db_session.execute(
        text("DELETE FROM ring_pending WHERE metadata->>'publish_event_id' = :id"),
        {"id": event_id},
    )
    db_session.execute(
        text("DELETE FROM ring_ledger WHERE metadata->>'publish_event_id' = :id"),
        {"id": event_id},
    )
    db_session.commit()


def test_publish_event_idempotency_shadow(db_session, monkeypatch):
    _ensure_publish_events_table(db_session)
    event_id = "evt-test-1"
    _cleanup_publish_rows(db_session, event_id)

    receipt = EnforcementReceipt(
        receipt_id="rec-1",
        request_id="req-1",
        draft_id=None,
        ring_id=None,
        turn_id=None,
        qa_status="PASS",
        qa_decision_hash="hash",
        policy_version="v1",
        created_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )

    monkeypatch.setattr(publish_module, "_validate_receipt", lambda **kwargs: (receipt, None, {"status": "PASS"}))
    monkeypatch.setattr(publish_module, "get_token_issuance_mode", lambda: "shadow")
    monkeypatch.setattr("backend.features.tokens.ledger.get_token_issuance_mode", lambda: "shadow")

    first = publish_module.handle_publish_event(
        db_session,
        event_id=event_id,
        user_id="user-1",
        platform="x",
        content_hash="hash",
        published_at=datetime.now(timezone.utc),
        platform_post_id="post-1",
        enforcement_request_id="req-1",
        enforcement_receipt_id="rec-1",
        metadata={},
    )
    second = publish_module.handle_publish_event(
        db_session,
        event_id=event_id,
        user_id="user-1",
        platform="x",
        content_hash="hash",
        published_at=datetime.now(timezone.utc),
        platform_post_id="post-1",
        enforcement_request_id="req-1",
        enforcement_receipt_id="rec-1",
        metadata={},
    )

    assert first["token_result"]["mode"] == "shadow"
    assert first["token_result"]["pending_amount"] >= 0
    assert second["token_result"]["reason_code"] in {"PENDING", "IDEMPOTENT_REPLAY"}


def test_publish_event_requires_receipt(db_session, monkeypatch):
    _ensure_publish_events_table(db_session)
    event_id = "evt-test-2"
    _cleanup_publish_rows(db_session, event_id)

    monkeypatch.setattr(publish_module, "get_token_issuance_mode", lambda: "shadow")

    result = publish_module.handle_publish_event(
        db_session,
        event_id=event_id,
        user_id="user-1",
        platform="x",
        content_hash="hash",
        published_at=datetime.now(timezone.utc),
        platform_post_id="post-2",
        enforcement_request_id=None,
        enforcement_receipt_id=None,
        metadata={},
    )

    assert result["token_result"]["reason_code"] == "ENFORCEMENT_RECEIPT_REQUIRED"


def test_reconciliation_detects_missing_publish_issuance(db_session, monkeypatch):
    _ensure_publish_events_table(db_session)
    event_id = "evt-test-3"
    _cleanup_publish_rows(db_session, event_id)

    db_session.execute(
        text(
            """
            INSERT INTO publish_events
            (id, user_id, platform, content_hash, published_at, platform_post_id,
             enforcement_request_id, enforcement_receipt_id, qa_status, audit_ok,
             token_mode, token_reason_code)
            VALUES
            (:id, :user_id, :platform, :content_hash, :published_at, :platform_post_id,
             :req_id, :rec_id, :qa_status, :audit_ok, :token_mode, :token_reason_code)
            """
        ),
        {
            "id": event_id,
            "user_id": "user-1",
            "platform": "x",
            "content_hash": "hash",
            "published_at": datetime.now(timezone.utc),
            "platform_post_id": "post-3",
            "req_id": "req-3",
            "rec_id": "rec-3",
            "qa_status": "PASS",
            "audit_ok": True,
            "token_mode": "live",
            "token_reason_code": "ISSUED",
        },
    )
    db_session.commit()

    monkeypatch.setattr("backend.features.tokens.reconciliation.get_token_issuance_mode", lambda: "shadow")
    report = run_reconciliation(db_session)
    assert any(item["event_id"] == event_id for item in report["publish_missing"])
