"""
Phase 10.2: Tests for canonical balance resolution.
"""
from datetime import datetime

import pytest
import uuid
from sqlalchemy import text

from backend.core.database import get_db
from backend.features.tokens import balance as balance_module


@pytest.fixture
def db_session():
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_user(db_session):
    user_id = f"balance_user_{datetime.utcnow().timestamp()}"
    db_session.execute(
        text('INSERT INTO users (id, "clerkId", "ringBalance", "createdAt", "updatedAt") VALUES (:id, :clerk_id, 100, NOW(), NOW()) ON CONFLICT DO NOTHING'),
        {"clerk_id": user_id, "id": str(uuid.uuid4())},
    )
    db_session.commit()
    yield user_id
    db_session.execute(text('DELETE FROM ring_pending WHERE user_id = :user_id'), {"user_id": user_id})
    db_session.execute(text('DELETE FROM ring_ledger WHERE user_id = :user_id'), {"user_id": user_id})
    db_session.execute(text('DELETE FROM ring_guardrails_state WHERE user_id = :user_id'), {"user_id": user_id})
    db_session.execute(text('DELETE FROM ring_clerk_sync WHERE user_id = :user_id'), {"user_id": user_id})
    db_session.execute(text('DELETE FROM users WHERE "clerkId" = :user_id'), {"user_id": user_id})
    db_session.commit()


def test_balance_off_mode_returns_legacy(db_session, test_user, monkeypatch):
    monkeypatch.setattr(balance_module, "get_token_issuance_mode", lambda: "off")
    summary = balance_module.get_effective_ring_balance(db_session, test_user)
    assert summary["mode"] == "off"
    assert summary["balance"] == 100
    assert summary["effective_balance"] == 100


def test_balance_shadow_mode_includes_pending_and_delta(db_session, test_user, monkeypatch):
    monkeypatch.setattr(balance_module, "get_token_issuance_mode", lambda: "shadow")
    db_session.execute(
        text(
            """
            INSERT INTO ring_pending (user_id, amount, reason_code, metadata)
            VALUES (:user_id, 25, 'shadow_test', '{}'::jsonb)
            """
        ),
        {"user_id": test_user},
    )
    db_session.execute(
        text(
            """
            INSERT INTO ring_ledger (user_id, event_type, reason_code, amount, balance_after, metadata)
            VALUES (:user_id, 'SPEND', 'shadow_spend', -10, 90, '{}'::jsonb)
            """
        ),
        {"user_id": test_user},
    )
    db_session.commit()

    summary = balance_module.get_effective_ring_balance(db_session, test_user)
    assert summary["mode"] == "shadow"
    assert summary["balance"] == 100
    assert summary["pending_total"] == 25
    assert summary["effective_balance"] == 115


def test_balance_live_mode_uses_ledger(db_session, test_user, monkeypatch):
    monkeypatch.setattr(balance_module, "get_token_issuance_mode", lambda: "live")
    db_session.execute(
        text(
            """
            INSERT INTO ring_ledger (user_id, event_type, reason_code, amount, balance_after, metadata)
            VALUES (:user_id, 'EARN', 'live_test', 20, 120, '{}'::jsonb)
            """
        ),
        {"user_id": test_user},
    )
    db_session.commit()

    summary = balance_module.get_effective_ring_balance(db_session, test_user)
    assert summary["mode"] == "live"
    assert summary["balance"] == 120
    assert summary["effective_balance"] == 120


def test_legacy_writes_blocked_in_shadow(monkeypatch):
    monkeypatch.setattr(balance_module, "get_token_issuance_mode", lambda: "shadow")
    allowed, mode = balance_module.assert_legacy_ring_writes_allowed()
    assert allowed is False
    assert mode == "shadow"
