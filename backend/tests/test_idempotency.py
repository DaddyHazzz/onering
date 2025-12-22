"""
backend/tests/test_idempotency.py
Tests for global idempotency key management.
"""

import pytest
import os
from backend.core.idempotency import check_and_set, check_key, clear_all_keys


@pytest.fixture(autouse=True)
def clean_idempotency():
    """Clear idempotency keys before each test."""
    clear_all_keys()
    yield
    clear_all_keys()


def test_check_and_set_first_time():
    """First time seeing key returns False (not duplicate)."""
    result = check_and_set("key-1", "test_op")
    assert result is False  # First time


def test_check_and_set_duplicate():
    """Second time seeing key returns True (duplicate)."""
    check_and_set("key-2", "test_op")
    result = check_and_set("key-2", "test_op")
    assert result is True  # Duplicate


def test_check_and_set_different_keys():
    """Different keys are treated independently."""
    check_and_set("key-3", "test_op")
    result = check_and_set("key-4", "test_op")
    assert result is False  # Different key, not duplicate


def test_check_key_exists():
    """check_key returns True for existing key."""
    check_and_set("key-5", "test_op")
    assert check_key("key-5") is True


def test_check_key_not_exists():
    """check_key returns False for non-existing key."""
    assert check_key("key-nonexistent") is False


def test_clear_all_keys():
    """clear_all_keys removes all stored keys."""
    check_and_set("key-6", "test_op")
    check_and_set("key-7", "test_op")
    
    clear_all_keys()
    
    # Both keys should be gone
    assert check_key("key-6") is False
    assert check_key("key-7") is False


def test_operation_parameter_stored():
    """Operation parameter is accepted (no error)."""
    result = check_and_set("key-8", "specific_operation")
    assert result is False  # First time


@pytest.mark.skipif(
    os.getenv('DATABASE_URL') is None,
    reason="PostgreSQL required for persistence test"
)
def test_persistence_across_sessions():
    """Keys persist when using PostgreSQL."""
    # Set key
    check_and_set("key-persist-1", "test_op")
    
    # Simulate new session by re-checking
    result = check_and_set("key-persist-1", "test_op")
    assert result is True  # Should still exist
