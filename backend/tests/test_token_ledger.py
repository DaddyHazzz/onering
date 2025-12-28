"""
Phase 10.2: Tests for RING Token Ledger and Issuance
"""
import pytest
from datetime import datetime, timedelta
from sqlalchemy import text
from backend.core.database import get_db
from backend.features.tokens.ledger import (
    append_ledger_entry,
    LedgerEntry,
    get_user_balance,
    update_user_balance,
    check_guardrails,
    update_guardrail_state,
    issue_ring_for_publish,
    get_user_ledger,
    get_pending_rewards,
    add_pending_reward,
    spend_ring,
    earn_ring,
    DAILY_EARN_CAP,
    MIN_EARN_INTERVAL_SECONDS,
)
from backend.features.tokens.reconciliation import run_reconciliation


@pytest.fixture
def db_session():
    """Get database session."""
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def clean_test_user(db_session):
    """Create and clean up test user."""
    import uuid
    test_user_id = f"test_user_{datetime.utcnow().timestamp()}"
    user_uuid = str(uuid.uuid4())
    
    # Ensure user exists in users table with proper UUID id and timestamps
    db_session.execute(
        text('INSERT INTO users (id, "clerkId", "ringBalance", "createdAt", "updatedAt") VALUES (:id, :clerk_id, 0, NOW(), NOW()) ON CONFLICT DO NOTHING'),
        {"id": user_uuid, "clerk_id": test_user_id}
    )
    db_session.commit()
    
    yield test_user_id
    
    # Cleanup
    db_session.execute(text('DELETE FROM ring_ledger WHERE user_id = :user_id'), {"user_id": test_user_id})
    db_session.execute(text('DELETE FROM ring_pending WHERE user_id = :user_id'), {"user_id": test_user_id})
    db_session.execute(text('DELETE FROM ring_guardrails_state WHERE user_id = :user_id'), {"user_id": test_user_id})
    db_session.execute(text('DELETE FROM users WHERE "clerkId" = :user_id'), {"user_id": test_user_id})
    db_session.commit()


class TestLedgerAppend:
    def test_append_ledger_entry_earn(self, db_session, clean_test_user):
        """Test appending EARN entry to ledger."""
        entry = LedgerEntry(
            user_id=clean_test_user,
            event_type="EARN",
            reason_code="test_earn",
            amount=10,
            balance_after=10,
            metadata={"test": "data"},
        )
        
        ledger_id = append_ledger_entry(db_session, entry)
        assert ledger_id is not None
        
        # Verify entry
        result = db_session.execute(
            text("SELECT amount, event_type FROM ring_ledger WHERE id = :id"),
            {"id": ledger_id}
        )
        row = result.fetchone()
        assert row[0] == 10
        assert row[1] == "EARN"
    
    def test_append_ledger_entry_penalty(self, db_session, clean_test_user):
        """Test appending PENALTY entry with negative amount."""
        entry = LedgerEntry(
            user_id=clean_test_user,
            event_type="PENALTY",
            reason_code="test_penalty",
            amount=-5,
            balance_after=5,
        )
        
        ledger_id = append_ledger_entry(db_session, entry)
        assert ledger_id is not None
    
    def test_ledger_is_append_only(self, db_session, clean_test_user):
        """Ledger should be append-only (no updates)."""
        entry = LedgerEntry(
            user_id=clean_test_user,
            event_type="EARN",
            reason_code="test",
            amount=10,
            balance_after=10,
        )
        ledger_id = append_ledger_entry(db_session, entry)
        
        # Try to update (should not be allowed by design)
        # This is a design constraint - we don't expose update methods
        entries = get_user_ledger(db_session, clean_test_user)
        assert len(entries) == 1


class TestGuardrails:
    def test_initial_guardrails_pass(self, db_session, clean_test_user):
        """First earn should pass all guardrails."""
        allowed, violations, reduction = check_guardrails(db_session, clean_test_user)
        assert allowed is True
        assert len(violations) == 0
        assert reduction == 0
    
    def test_daily_cap_enforced(self, db_session, clean_test_user):
        """Daily earn cap should block further earns."""
        # Simulate reaching cap
        db_session.execute(
            text("""
                INSERT INTO ring_guardrails_state (user_id, daily_earn_total, reset_at)
                VALUES (:user_id, :cap, NOW())
            """),
            {"user_id": clean_test_user, "cap": DAILY_EARN_CAP}
        )
        db_session.commit()
        
        allowed, violations, reduction = check_guardrails(db_session, clean_test_user)
        assert allowed is False
        assert reduction == 100
        assert any("daily_cap" in v for v in violations)
    
    def test_min_interval_enforced(self, db_session, clean_test_user):
        """Minimum interval between earns should apply penalty."""
        # Set last earn very recently
        db_session.execute(
            text("""
                INSERT INTO ring_guardrails_state (user_id, last_earn_at, reset_at)
                VALUES (:user_id, NOW(), NOW())
            """),
            {"user_id": clean_test_user}
        )
        db_session.commit()
        
        allowed, violations, reduction = check_guardrails(db_session, clean_test_user)
        assert reduction >= 50  # At least 50% penalty
        assert any("min_interval" in v for v in violations)
    
    def test_guardrail_state_updates(self, db_session, clean_test_user):
        """Guardrail state should update after earn."""
        # Create initial state
        check_guardrails(db_session, clean_test_user)
        
        update_guardrail_state(db_session, clean_test_user, 10)
        
        # Verify update
        result = db_session.execute(
            text("SELECT daily_earn_count, daily_earn_total FROM ring_guardrails_state WHERE user_id = :user_id"),
            {"user_id": clean_test_user}
        )
        row = result.fetchone()
        assert row[0] == 1  # Count incremented
        assert row[1] == 10  # Total updated


class TestIssuanceRules:
    def test_issuance_requires_qa_pass(self, db_session, clean_test_user, monkeypatch):
        """Issuance requires QA PASS status."""
        monkeypatch.setattr("backend.features.tokens.ledger.get_token_issuance_mode", lambda: "live")
        
        result = issue_ring_for_publish(
            db_session, clean_test_user, None, "req1", "rec1",
            qa_status="FAIL", audit_ok=True, platform="x"
        )
        
        assert result["issued"] is False
        assert "qa_not_pass" in result["violations"]
    
    def test_issuance_requires_audit_ok(self, db_session, clean_test_user, monkeypatch):
        """Issuance requires audit_ok=True."""
        monkeypatch.setattr("backend.features.tokens.ledger.get_token_issuance_mode", lambda: "live")
        
        result = issue_ring_for_publish(
            db_session, clean_test_user, None, "req1", "rec1",
            qa_status="PASS", audit_ok=False, platform="x"
        )
        
        assert result["issued"] is False
        assert "audit_not_ok" in result["violations"]
    
    def test_shadow_mode_creates_pending(self, db_session, clean_test_user, monkeypatch):
        """Shadow mode should create pending entry."""
        monkeypatch.setattr("backend.features.tokens.ledger.get_token_issuance_mode", lambda: "shadow")
        
        result = issue_ring_for_publish(
            db_session, clean_test_user, None, "req1", "rec1",
            qa_status="PASS", audit_ok=True, platform="x"
        )
        
        assert result["mode"] == "shadow"
        assert result["pending_id"] is not None
        assert result["amount"] > 0
        
        # Verify pending entry
        pending = get_pending_rewards(db_session, clean_test_user)
        assert pending["totalPending"] > 0
    
    def test_live_mode_issues_tokens(self, db_session, clean_test_user, monkeypatch):
        """Live mode should issue tokens and update ledger."""
        monkeypatch.setattr("backend.features.tokens.ledger.get_token_issuance_mode", lambda: "live")
        
        initial_balance = get_user_balance(db_session, clean_test_user)
        
        result = issue_ring_for_publish(
            db_session, clean_test_user, None, "req1", "rec1",
            qa_status="PASS", audit_ok=True, platform="x"
        )
        
        assert result["issued"] is True
        assert result["ledger_id"] is not None
        assert result["amount"] > 0
        
        # Verify balance updated
        new_balance = get_user_balance(db_session, clean_test_user)
        assert new_balance == initial_balance + result["amount"]
        
        # Verify ledger entry
        entries = get_user_ledger(db_session, clean_test_user)
        assert len(entries) == 1
        assert entries[0]["amount"] == result["amount"]
    
    def test_guardrails_reduce_issuance(self, db_session, clean_test_user, monkeypatch):
        """Guardrails should reduce issuance amount."""
        monkeypatch.setattr("backend.features.tokens.ledger.get_token_issuance_mode", lambda: "live")
        
        # Set last earn very recently to trigger penalty
        db_session.execute(
            text("""
                INSERT INTO ring_guardrails_state (user_id, last_earn_at, reset_at)
                VALUES (:user_id, NOW(), NOW())
            """),
            {"user_id": clean_test_user}
        )
        db_session.commit()
        
        result = issue_ring_for_publish(
            db_session, clean_test_user, None, "req1", "rec1",
            qa_status="PASS", audit_ok=True, platform="x"
        )
        
        # Should have violations and reduced amount
        assert len(result["violations"]) > 0


class TestReconciliation:
    def test_reconciliation_detects_mismatch(self, db_session, clean_test_user, monkeypatch):
        """Reconciliation should detect balance mismatch."""
        monkeypatch.setattr("backend.features.tokens.reconciliation.get_token_issuance_mode", lambda: "shadow")
        
        # Create mismatch: ledger says 10, balance says 0
        entry = LedgerEntry(
            user_id=clean_test_user,
            event_type="EARN",
            reason_code="test",
            amount=10,
            balance_after=10,
        )
        append_ledger_entry(db_session, entry)
        
        # Balance is still 0 (not updated)
        report = run_reconciliation(db_session)
        
        assert report["status"] == "completed"
        assert report["mismatches_found"] > 0
        assert any(m["user_id"] == clean_test_user for m in report["mismatches"])
    
    def test_reconciliation_shadow_mode_logs_adjustment(self, db_session, clean_test_user, monkeypatch):
        """Shadow mode reconciliation should log adjustment."""
        monkeypatch.setattr("backend.features.tokens.reconciliation.get_token_issuance_mode", lambda: "shadow")
        
        # Create mismatch
        entry = LedgerEntry(
            user_id=clean_test_user,
            event_type="EARN",
            reason_code="test",
            amount=10,
            balance_after=10,
        )
        append_ledger_entry(db_session, entry)
        
        report = run_reconciliation(db_session)
        
        # Should create ADJUSTMENT entry
        assert len(report["adjustments"]) > 0
        
        # Verify adjustment in ledger
        entries = get_user_ledger(db_session, clean_test_user)
        assert any(e["eventType"] == "ADJUSTMENT" for e in entries)
    
    def test_reconciliation_live_mode_applies_adjustment(self, db_session, clean_test_user, monkeypatch):
        """Live mode reconciliation should apply adjustment."""
        monkeypatch.setattr("backend.features.tokens.reconciliation.get_token_issuance_mode", lambda: "live")
        
        # Create mismatch
        entry = LedgerEntry(
            user_id=clean_test_user,
            event_type="EARN",
            reason_code="test",
            amount=10,
            balance_after=10,
        )
        append_ledger_entry(db_session, entry)
        
        initial_balance = get_user_balance(db_session, clean_test_user)
        
        report = run_reconciliation(db_session)
        
        # Balance should be updated
        new_balance = get_user_balance(db_session, clean_test_user)
        assert new_balance != initial_balance


class TestLedgerQueries:
    def test_get_user_ledger(self, db_session, clean_test_user):
        """Test fetching user ledger entries."""
        # Add multiple entries
        for i in range(3):
            entry = LedgerEntry(
                user_id=clean_test_user,
                event_type="EARN",
                reason_code=f"test_{i}",
                amount=10,
                balance_after=10 * (i + 1),
            )
            append_ledger_entry(db_session, entry)
        
        entries = get_user_ledger(db_session, clean_test_user, limit=10)
        assert len(entries) == 3
        
        # Should be in reverse chronological order
        assert entries[0]["reasonCode"] == "test_2"
    
    def test_ledger_limit_respected(self, db_session, clean_test_user):
        """Ledger query should respect limit parameter."""
        # Add many entries
        for i in range(10):
            entry = LedgerEntry(
                user_id=clean_test_user,
                event_type="EARN",
                reason_code=f"test_{i}",
                amount=1,
                balance_after=i + 1,
            )
            append_ledger_entry(db_session, entry)
        
        entries = get_user_ledger(db_session, clean_test_user, limit=5)
        assert len(entries) == 5


class TestPendingRewards:
    def test_add_pending_reward(self, db_session, clean_test_user):
        """Test adding pending reward in shadow mode."""
        pending_id = add_pending_reward(
            db_session, clean_test_user, 10, "test_pending", {"platform": "x"}
        )
        assert pending_id is not None
        
        pending = get_pending_rewards(db_session, clean_test_user)
        assert pending["totalPending"] == 10
        assert pending["count"] == 1
    
    def test_multiple_pending_rewards(self, db_session, clean_test_user):
        """Test multiple pending rewards accumulate."""
        add_pending_reward(db_session, clean_test_user, 10, "test1")
        add_pending_reward(db_session, clean_test_user, 15, "test2")
        
        pending = get_pending_rewards(db_session, clean_test_user)
        assert pending["totalPending"] == 25
        assert pending["count"] == 2


class TestSpendEarn:
    def test_spend_live_updates_balance(self, db_session, clean_test_user, monkeypatch):
        monkeypatch.setattr("backend.features.tokens.ledger.get_token_issuance_mode", lambda: "live")
        update_user_balance(db_session, clean_test_user, 100)

        result = spend_ring(
            db_session,
            user_id=clean_test_user,
            amount=10,
            reason_code="test_spend",
            metadata={"source": "test"},
        )
        assert result["ok"] is True
        assert result["balance_after"] == 90
        assert get_user_balance(db_session, clean_test_user) == 90

    def test_earn_shadow_creates_pending(self, db_session, clean_test_user, monkeypatch):
        monkeypatch.setattr("backend.features.tokens.ledger.get_token_issuance_mode", lambda: "shadow")

        result = earn_ring(
            db_session,
            user_id=clean_test_user,
            amount=15,
            reason_code="test_earn",
            metadata={"source": "test"},
        )
        assert result["ok"] is True
        assert result["pending_id"] is not None
        pending = get_pending_rewards(db_session, clean_test_user)
        assert pending["totalPending"] >= 15

    def test_spend_idempotent(self, db_session, clean_test_user, monkeypatch):
        monkeypatch.setattr("backend.features.tokens.ledger.get_token_issuance_mode", lambda: "live")
        update_user_balance(db_session, clean_test_user, 50)

        first = spend_ring(
            db_session,
            user_id=clean_test_user,
            amount=5,
            reason_code="test_spend",
            idempotency_key="idemp-1",
        )
        second = spend_ring(
            db_session,
            user_id=clean_test_user,
            amount=5,
            reason_code="test_spend",
            idempotency_key="idemp-1",
        )
        assert first["ok"] is True
        assert second["ok"] is True
        assert second.get("idempotent") is True
        assert first["ledger_id"] == second["ledger_id"]
