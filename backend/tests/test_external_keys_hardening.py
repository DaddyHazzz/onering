"""Tests for external API key rotation and IP allowlist enforcement."""
import pytest
from sqlalchemy import text
from backend.features.external.api_keys import (
    create_api_key,
    validate_api_key,
    rotate_api_key,
    check_rate_limit,
)
from backend.core.database import get_db


@pytest.fixture
def db():
    """Get test database session."""
    session = next(get_db())
    session.execute(
        text("ALTER TABLE external_api_keys ADD COLUMN IF NOT EXISTS ip_allowlist TEXT[] NOT NULL DEFAULT '{}'::TEXT[]")
    )
    session.execute(
        text("ALTER TABLE external_api_keys ADD COLUMN IF NOT EXISTS rotated_at TIMESTAMPTZ NULL")
    )
    session.commit()
    try:
        yield session
    finally:
        session.close()


def test_api_key_creation_with_ip_allowlist(db):
    """Test creating API key with IP allowlist."""
    key_data = create_api_key(
        db,
        owner_user_id="user123",
        scopes=["read:rings"],
        tier="pro",
        ip_allowlist=["192.168.1.1", "10.0.0.1"],
    )
    assert key_data["key_id"].startswith("osk_")
    assert key_data["full_key"].startswith("osk_")
    assert key_data["ip_allowlist"] == ["192.168.1.1", "10.0.0.1"]


def test_validate_key_with_ip_allowlist_pass(db):
    """Test validation passes when client IP is in allowlist."""
    key_data = create_api_key(
        db,
        owner_user_id="user123",
        scopes=["read:rings"],
        tier="free",
        ip_allowlist=["192.168.1.100"],
    )
    full_key = key_data["full_key"]

    # Validate from allowed IP
    result = validate_api_key(db, full_key, client_ip="192.168.1.100")
    assert result is not None
    assert result["key_id"] == key_data["key_id"]


def test_validate_key_with_ip_allowlist_reject(db):
    """Test validation fails when client IP is not in allowlist."""
    key_data = create_api_key(
        db,
        owner_user_id="user123",
        scopes=["read:rings"],
        tier="free",
        ip_allowlist=["192.168.1.100"],
    )
    full_key = key_data["full_key"]

    # Validate from disallowed IP
    result = validate_api_key(db, full_key, client_ip="10.0.0.1")
    assert result is None


def test_rotate_api_key_preserve_key_id(db):
    """Test key rotation preserving key_id."""
    key_data = create_api_key(
        db,
        owner_user_id="user123",
        scopes=["read:rings"],
        tier="pro",
        ip_allowlist=["192.168.1.1"],
    )
    original_key_id = key_data["key_id"]
    original_full_key = key_data["full_key"]

    # Rotate with preserve
    rotated = rotate_api_key(db, original_key_id, preserve_key_id=True, ip_allowlist=["10.0.0.1"])
    assert rotated is not None
    assert rotated["key_id"] == original_key_id
    assert rotated["full_key"] != original_full_key
    assert rotated["ip_allowlist"] == ["10.0.0.1"]

    # Old key should be invalid
    result = validate_api_key(db, original_full_key)
    assert result is None

    # New key should work
    result = validate_api_key(db, rotated["full_key"], client_ip="10.0.0.1")
    assert result is not None


def test_rotate_api_key_new_key_id(db):
    """Test key rotation issuing new key_id."""
    key_data = create_api_key(
        db,
        owner_user_id="user123",
        scopes=["read:rings"],
        tier="pro",
    )
    original_key_id = key_data["key_id"]
    original_full_key = key_data["full_key"]

    # Rotate without preserve
    rotated = rotate_api_key(db, original_key_id, preserve_key_id=False)
    assert rotated is not None
    assert rotated["key_id"] != original_key_id
    assert rotated["full_key"] != original_full_key

    # Old key invalid
    result = validate_api_key(db, original_full_key)
    assert result is None

    # New key valid
    result = validate_api_key(db, rotated["full_key"])
    assert result is not None


def test_rate_limit_concurrency_safe(db):
    """Test rate limit increments are atomic and concurrency-safe."""
    key_data = create_api_key(
        db,
        owner_user_id="user123",
        scopes=["read:rings"],
        tier="free",  # 100/hour limit
    )
    key_id = key_data["key_id"]

    # Simulate 105 requests in the same window
    allowed_count = 0
    rejected_count = 0

    for i in range(105):
        allowed, current, limit, reset_at = check_rate_limit(db, key_id, "free")
        if allowed:
            allowed_count += 1
        else:
            rejected_count += 1

    # Should allow exactly 100
    assert allowed_count == 100
    assert rejected_count == 5


def test_rate_limit_headers_values(db):
    """Test rate limit headers return correct values."""
    key_data = create_api_key(
        db,
        owner_user_id="user123",
        scopes=["read:rings"],
        tier="pro",  # 1000/hour limit
    )
    key_id = key_data["key_id"]

    # First request
    allowed, current, limit, reset_at = check_rate_limit(db, key_id, "pro")
    assert allowed is True
    assert current == 1
    assert limit == 1000
    assert reset_at is not None

    # Second request
    allowed, current, limit, reset_at = check_rate_limit(db, key_id, "pro")
    assert allowed is True
    assert current == 2
    assert limit == 1000
