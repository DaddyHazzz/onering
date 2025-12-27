"""
Phase 10.3: External Platform API Tests

Tests cover:
- API key generation, validation, and hashing
- Scope enforcement
- Rate limiting
- External API endpoint access control
- Webhook signing and verification
- Kill switch behavior
"""
import pytest
import os
import bcrypt
from datetime import datetime, timedelta
from sqlalchemy import text
from backend.core.database import get_db
from backend.features.external.api_keys import (
    generate_api_key,
    hash_api_key,
    verify_api_key,
    create_api_key,
    validate_api_key,
    revoke_api_key,
    check_scope,
    check_rate_limit,
    is_external_api_enabled,
    VALID_SCOPES,
    RATE_LIMIT_TIERS,
)
from backend.features.external.webhooks import (
    generate_webhook_secret,
    sign_webhook_payload,
    verify_webhook_signature,
    create_webhook_subscription,
    emit_webhook_event,
    is_webhooks_enabled,
)


@pytest.fixture
def db_session():
    """Get database session."""
    db = next(get_db())
    try:
        db.execute(
            text("ALTER TABLE external_api_keys ADD COLUMN IF NOT EXISTS ip_allowlist TEXT[] NOT NULL DEFAULT '{}'::TEXT[]")
        )
        db.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS webhook_events (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    event_type TEXT NOT NULL,
                    user_id TEXT NULL,
                    payload JSONB NOT NULL DEFAULT '{}',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
        )
        db.execute(
            text("ALTER TABLE webhook_deliveries ADD COLUMN IF NOT EXISTS next_attempt_at TIMESTAMPTZ")
        )
        db.execute(
            text("ALTER TABLE webhook_deliveries ADD COLUMN IF NOT EXISTS event_timestamp TIMESTAMPTZ")
        )
        db.commit()
        yield db
    finally:
        db.close()


@pytest.fixture
def clean_test_user(db_session):
    """Create and clean up test user."""
    import uuid
    test_user_id = f"test_ext_user_{datetime.utcnow().timestamp()}"
    user_uuid = str(uuid.uuid4())
    
    db_session.execute(
        text('INSERT INTO users (id, "clerkId", "ringBalance", "createdAt", "updatedAt") VALUES (:id, :clerk_id, 100, NOW(), NOW()) ON CONFLICT DO NOTHING'),
        {"id": user_uuid, "clerk_id": test_user_id}
    )
    db_session.commit()
    
    yield test_user_id
    
    # Cleanup
    db_session.execute(text('DELETE FROM external_api_keys WHERE owner_user_id = :user_id'), {"user_id": test_user_id})
    db_session.execute(text('DELETE FROM external_webhooks WHERE owner_user_id = :user_id'), {"user_id": test_user_id})
    db_session.execute(text('DELETE FROM users WHERE "clerkId" = :user_id'), {"user_id": test_user_id})
    db_session.commit()


class TestApiKeyGeneration:
    def test_generate_api_key_format(self):
        """API keys should have proper format."""
        key_id, full_key = generate_api_key()
        
        assert key_id.startswith("osk_")
        assert full_key.startswith("osk_")
        assert len(full_key) > 20
        assert key_id != full_key
    
    def test_hash_api_key(self):
        """API keys should be hashed with bcrypt."""
        _, key = generate_api_key()
        key_hash = hash_api_key(key)
        
        assert key_hash != key
        assert len(key_hash) == 60  # bcrypt hash length
        assert bcrypt.checkpw(key.encode(), key_hash.encode())
    
    def test_verify_api_key(self):
        """API key verification should work correctly."""
        _, key = generate_api_key()
        key_hash = hash_api_key(key)
        
        assert verify_api_key(key, key_hash) is True
        assert verify_api_key("wrong_key", key_hash) is False


class TestApiKeyCreation:
    def test_create_api_key_success(self, db_session, clean_test_user):
        """Should create API key with valid parameters."""
        result = create_api_key(
            db_session,
            owner_user_id=clean_test_user,
            scopes=["read:rings"],
            tier="free",
        )
        
        assert "key_id" in result
        assert "full_key" in result
        assert result["full_key"].startswith("osk_")
        assert result["scopes"] == ["read:rings"]
        assert result["tier"] == "free"
    
    def test_create_api_key_invalid_scope(self, db_session, clean_test_user):
        """Should reject invalid scopes."""
        with pytest.raises(ValueError, match="Invalid scopes"):
            create_api_key(
                db_session,
                owner_user_id=clean_test_user,
                scopes=["invalid:scope"],
                tier="free",
            )
    
    def test_create_api_key_invalid_tier(self, db_session, clean_test_user):
        """Should reject invalid tiers."""
        with pytest.raises(ValueError, match="Invalid tier"):
            create_api_key(
                db_session,
                owner_user_id=clean_test_user,
                scopes=["read:rings"],
                tier="invalid_tier",
            )
    
    def test_create_api_key_with_expiry(self, db_session, clean_test_user):
        """Should create key with expiration."""
        result = create_api_key(
            db_session,
            owner_user_id=clean_test_user,
            scopes=["read:rings"],
            tier="free",
            expires_in_days=30,
        )
        
        assert result["expires_at"] is not None


class TestApiKeyValidation:
    def test_validate_api_key_success(self, db_session, clean_test_user):
        """Should validate correct API key."""
        created = create_api_key(
            db_session,
            owner_user_id=clean_test_user,
            scopes=["read:rings", "read:ledger"],
            tier="pro",
        )
        
        validated = validate_api_key(db_session, created["full_key"])
        
        assert validated is not None
        assert validated["owner_user_id"] == clean_test_user
        assert "read:rings" in validated["scopes"]
        assert validated["rate_limit_tier"] == "pro"
    
    def test_validate_api_key_invalid(self, db_session):
        """Should reject invalid API key."""
        validated = validate_api_key(db_session, "osk_invalid_key_12345")
        assert validated is None
    
    def test_validate_api_key_updates_last_used(self, db_session, clean_test_user):
        """Should update last_used_at on validation."""
        created = create_api_key(
            db_session,
            owner_user_id=clean_test_user,
            scopes=["read:rings"],
            tier="free",
        )
        
        # First validation
        validate_api_key(db_session, created["full_key"])
        
        # Check last_used_at was set
        row = db_session.execute(
            text("SELECT last_used_at FROM external_api_keys WHERE key_id = :key_id"),
            {"key_id": created["key_id"]}
        ).fetchone()
        
        assert row[0] is not None


class TestApiKeyRevocation:
    def test_revoke_api_key_success(self, db_session, clean_test_user):
        """Should revoke API key."""
        created = create_api_key(
            db_session,
            owner_user_id=clean_test_user,
            scopes=["read:rings"],
            tier="free",
        )
        
        # Revoke
        success = revoke_api_key(db_session, created["key_id"])
        assert success is True
        
        # Key should no longer validate
        validated = validate_api_key(db_session, created["full_key"])
        assert validated is None
    
    def test_revoke_nonexistent_key(self, db_session):
        """Should return False for nonexistent key."""
        success = revoke_api_key(db_session, "osk_nonexistent")
        assert success is False


class TestScopeEnforcement:
    def test_check_scope_success(self):
        """Should allow valid scopes."""
        key_info = {"scopes": ["read:rings", "read:ledger"]}
        assert check_scope(key_info, "read:rings") is True
        assert check_scope(key_info, "read:ledger") is True
    
    def test_check_scope_failure(self):
        """Should deny missing scopes."""
        key_info = {"scopes": ["read:rings"]}
        assert check_scope(key_info, "read:ledger") is False


class TestRateLimiting:
    def test_rate_limit_free_tier(self, db_session, clean_test_user):
        """Should enforce free tier rate limit (100/hr)."""
        created = create_api_key(
            db_session,
            owner_user_id=clean_test_user,
            scopes=["read:rings"],
            tier="free",
        )
        
        # First request should be allowed
        allowed, current, limit, _ = check_rate_limit(db_session, created["key_id"], "free")
        assert allowed is True
        assert current == 1
        assert limit == 100
    
    def test_rate_limit_enforcement(self, db_session, clean_test_user):
        """Should block requests after limit."""
        created = create_api_key(
            db_session,
            owner_user_id=clean_test_user,
            scopes=["read:rings"],
            tier="free",
        )
        
        # Simulate reaching limit
        window_start = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        db_session.execute(
            text("""
                INSERT INTO external_api_rate_limits (key_id, window_start, request_count)
                VALUES (:key_id, :window_start, 100)
            """),
            {"key_id": created["key_id"], "window_start": window_start}
        )
        db_session.commit()
        
        # Next request should be blocked
        allowed, current, limit, _ = check_rate_limit(db_session, created["key_id"], "free")
        assert allowed is False
        assert current == 100
        assert limit == 100


class TestWebhookSigning:
    def test_generate_webhook_secret(self):
        """Should generate valid webhook secret."""
        secret = generate_webhook_secret()
        assert secret.startswith("whsec_")
        assert len(secret) > 20
    
    def test_sign_webhook_payload(self):
        """Should sign payload with HMAC-SHA256."""
        payload = {"event": "test", "data": {"foo": "bar"}}
        secret = "whsec_test_secret"
        timestamp = int(datetime.utcnow().timestamp())
        
        signature = sign_webhook_payload(payload, secret, timestamp)
        
        assert signature.startswith("v1,")
        assert len(signature) > 10
    
    def test_verify_webhook_signature_success(self):
        """Should verify valid signature."""
        payload = {"event": "test", "data": {"foo": "bar"}}
        secret = "whsec_test_secret"
        timestamp = int(datetime.utcnow().timestamp())
        
        signature = sign_webhook_payload(payload, secret, timestamp)
        verified = verify_webhook_signature(payload, signature, secret, timestamp)
        
        assert verified is True
    
    def test_verify_webhook_signature_invalid(self):
        """Should reject invalid signature."""
        payload = {"event": "test"}
        secret = "whsec_test_secret"
        timestamp = int(datetime.utcnow().timestamp())
        
        verified = verify_webhook_signature(payload, "v1,invalid_sig", secret, timestamp)
        
        assert verified is False
    
    def test_verify_webhook_signature_replay_protection(self):
        """Should reject old timestamps."""
        payload = {"event": "test"}
        secret = "whsec_test_secret"
        old_timestamp = int((datetime.utcnow() - timedelta(hours=1)).timestamp())
        
        signature = sign_webhook_payload(payload, secret, old_timestamp)
        verified = verify_webhook_signature(payload, signature, secret, old_timestamp, tolerance_seconds=300)
        
        assert verified is False


class TestWebhookSubscription:
    def test_create_webhook_subscription(self, db_session, clean_test_user):
        """Should create webhook subscription."""
        result = create_webhook_subscription(
            db_session,
            owner_user_id=clean_test_user,
            url="https://example.com/webhook",
            events=["draft.published", "ring.earned"],
        )
        
        assert "id" in result
        assert "secret" in result
        assert result["secret"].startswith("whsec_")
        assert result["url"] == "https://example.com/webhook"
        assert result["events"] == ["draft.published", "ring.earned"]


class TestWebhookEmission:
    def test_emit_webhook_event(self, db_session, clean_test_user, monkeypatch):
        """Should create delivery records for matching webhooks."""
        # Enable webhooks
        monkeypatch.setattr("backend.features.external.webhooks.is_webhooks_enabled", lambda: True)
        
        # Create webhook subscription
        webhook = create_webhook_subscription(
            db_session,
            owner_user_id=clean_test_user,
            url="https://example.com/webhook",
            events=["ring.earned"],
        )
        
        # Emit event
        count = emit_webhook_event(
            db_session,
            event_type="ring.earned",
            payload={"amount": 10},
            user_id=clean_test_user,
        )
        
        assert count == 1
        
        # Verify delivery record
        row = db_session.execute(
            text("SELECT status, event_type FROM webhook_deliveries WHERE webhook_id = :id LIMIT 1"),
            {"id": webhook["id"]}
        ).fetchone()
        
        assert row is not None
        assert row[0] == "pending"
        assert row[1] == "ring.earned"


class TestKillSwitches:
    def test_external_api_disabled_by_default(self, monkeypatch):
        """External API should be disabled by default."""
        monkeypatch.delenv("ONERING_EXTERNAL_API_ENABLED", raising=False)
        assert is_external_api_enabled() is False
    
    def test_webhooks_disabled_by_default(self, monkeypatch):
        """Webhooks should be disabled by default."""
        monkeypatch.delenv("ONERING_WEBHOOKS_ENABLED", raising=False)
        assert is_webhooks_enabled() is False
    
    def test_external_api_can_be_enabled(self, monkeypatch):
        """External API can be enabled via env var."""
        monkeypatch.setenv("ONERING_EXTERNAL_API_ENABLED", "1")
        assert is_external_api_enabled() is True
    
    def test_webhooks_can_be_enabled(self, monkeypatch):
        """Webhooks can be enabled via env var."""
        monkeypatch.setenv("ONERING_WEBHOOKS_ENABLED", "1")
        assert is_webhooks_enabled() is True
