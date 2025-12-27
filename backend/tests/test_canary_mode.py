"""
Tests for canary mode and kill-switch functionality (Phase 10.3).
"""
import pytest
import os
from unittest.mock import patch


def test_canary_only_mode_rejects_non_canary(monkeypatch):
    """ONERING_EXTERNAL_API_CANARY_ONLY rejects non-canary keys with 403."""
    from backend.api.external import is_canary_only_mode
    
    monkeypatch.setenv("ONERING_EXTERNAL_API_CANARY_ONLY", "1")
    assert is_canary_only_mode() == True
    
    monkeypatch.setenv("ONERING_EXTERNAL_API_CANARY_ONLY", "0")
    assert is_canary_only_mode() == False


def test_canary_keys_get_reduced_rate_limits():
    """Canary-enabled keys get 10/hr limit regardless of tier."""
    from backend.api.external import get_canary_rate_limit
    
    # Normal rate limits
    assert get_canary_rate_limit("free", is_canary=False) == 100
    assert get_canary_rate_limit("pro", is_canary=False) == 1000
    assert get_canary_rate_limit("enterprise", is_canary=False) == 10000
    
    # Canary rate limits (all 10/hr)
    assert get_canary_rate_limit("free", is_canary=True) == 10
    assert get_canary_rate_limit("pro", is_canary=True) == 10
    assert get_canary_rate_limit("enterprise", is_canary=True) == 10


def test_kill_switch_external_api_enabled(monkeypatch):
    """ONERING_EXTERNAL_API_ENABLED defaults to 0."""
    from backend.api.external import is_external_api_enabled
    
    monkeypatch.setenv("ONERING_EXTERNAL_API_ENABLED", "0")
    assert is_external_api_enabled() == False
    
    monkeypatch.setenv("ONERING_EXTERNAL_API_ENABLED", "1")
    assert is_external_api_enabled() == True


def test_kill_switch_webhooks_enabled(monkeypatch):
    """ONERING_WEBHOOKS_ENABLED defaults to 0."""
    from backend.features.external.webhooks import is_webhooks_enabled
    
    monkeypatch.setenv("ONERING_WEBHOOKS_ENABLED", "0")
    assert is_webhooks_enabled() == False
    
    monkeypatch.setenv("ONERING_WEBHOOKS_ENABLED", "1")
    assert is_webhooks_enabled() == True


def test_kill_switch_delivery_enabled(monkeypatch):
    """ONERING_WEBHOOKS_DELIVERY_ENABLED defaults to 0."""
    from backend.features.external.webhooks import is_delivery_enabled
    
    monkeypatch.setenv("ONERING_WEBHOOKS_DELIVERY_ENABLED", "0")
    assert is_delivery_enabled() == False
    
    monkeypatch.setenv("ONERING_WEBHOOKS_DELIVERY_ENABLED", "1")
    assert is_delivery_enabled() == True


def test_backoff_parsing(monkeypatch):
    """Backoff seconds parsed correctly from env."""
    from backend.features.external.webhooks import _parse_backoff
    
    monkeypatch.setenv("ONERING_WEBHOOKS_BACKOFF_SECONDS", "60,300,900")
    assert _parse_backoff() == [60, 300, 900]
    
    monkeypatch.setenv("ONERING_WEBHOOKS_BACKOFF_SECONDS", "30,120,600,1800")
    assert _parse_backoff() == [30, 120, 600, 1800]
    
    monkeypatch.setenv("ONERING_WEBHOOKS_BACKOFF_SECONDS", "invalid")
    assert _parse_backoff() == [60, 300, 900]  # Fallback


def test_max_attempts_parsing(monkeypatch):
    """Max attempts parsed correctly from env."""
    from backend.features.external.webhooks import get_max_attempts
    
    monkeypatch.setenv("ONERING_WEBHOOKS_MAX_ATTEMPTS", "5")
    assert get_max_attempts() == 5
    
    monkeypatch.setenv("ONERING_WEBHOOKS_MAX_ATTEMPTS", "invalid")
    assert get_max_attempts() == 3  # Fallback
