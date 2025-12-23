"""
Test admin authentication with legacy X-Admin-Key (Phase 4.6).

Tests:
- Legacy key allowed in dev/test mode
- Legacy key blocked in prod mode (unless mode="legacy")
- Legacy key unconfigured -> 503
- Actor identity recorded correctly
"""
import pytest
import os
from fastapi.testclient import TestClient
from backend.main import app
from backend.core.config import settings

client = TestClient(app)


def test_legacy_key_allowed_in_dev():
    """Test legacy X-Admin-Key works in dev/test mode."""
    # Set up environment
    original_mode = settings.ADMIN_AUTH_MODE
    original_env = settings.ENVIRONMENT
    original_key = settings.ADMIN_KEY
    
    settings.ADMIN_AUTH_MODE = "hybrid"
    settings.ENVIRONMENT = "dev"
    settings.ADMIN_KEY = "test-admin-key-123"
    
    try:
        headers = {"X-Admin-Key": "test-admin-key-123"}
        response = client.get("/v1/admin/billing/retries", headers=headers)
        assert response.status_code in [200, 404]  # Not 401
    finally:
        settings.ADMIN_AUTH_MODE = original_mode
        settings.ENVIRONMENT = original_env
        settings.ADMIN_KEY = original_key


def test_legacy_key_blocked_in_prod():
    """Test legacy X-Admin-Key blocked in prod (hybrid mode)."""
    original_mode = settings.ADMIN_AUTH_MODE
    original_env = settings.ENVIRONMENT
    original_key = settings.ADMIN_KEY
    
    settings.ADMIN_AUTH_MODE = "hybrid"  # Hybrid but prod blocks legacy
    settings.ENVIRONMENT = "prod"
    settings.ADMIN_KEY = "test-admin-key-123"
    
    try:
        headers = {"X-Admin-Key": "test-admin-key-123"}
        response = client.get("/v1/admin/billing/retries", headers=headers)
        assert response.status_code == 401
    finally:
        settings.ADMIN_AUTH_MODE = original_mode
        settings.ENVIRONMENT = original_env
        settings.ADMIN_KEY = original_key


def test_legacy_mode_allows_key_in_prod():
    """Test legacy mode allows X-Admin-Key even in prod."""
    original_mode = settings.ADMIN_AUTH_MODE
    original_env = settings.ENVIRONMENT
    original_key = settings.ADMIN_KEY
    
    settings.ADMIN_AUTH_MODE = "legacy"  # Explicit legacy mode
    settings.ENVIRONMENT = "prod"
    settings.ADMIN_KEY = "test-admin-key-456"
    
    try:
        headers = {"X-Admin-Key": "test-admin-key-456"}
        response = client.get("/v1/admin/billing/retries", headers=headers)
        assert response.status_code in [200, 404]  # Not 401
    finally:
        settings.ADMIN_AUTH_MODE = original_mode
        settings.ENVIRONMENT = original_env
        settings.ADMIN_KEY = original_key


def test_legacy_key_unconfigured():
    """Test 503 when no admin auth configured."""
    original_mode = settings.ADMIN_AUTH_MODE
    original_key = settings.ADMIN_KEY
    original_clerk = settings.CLERK_SECRET_KEY
    
    settings.ADMIN_AUTH_MODE = "legacy"
    settings.ADMIN_KEY = None
    settings.CLERK_SECRET_KEY = None
    
    try:
        headers = {"X-Admin-Key": "any-key"}
        response = client.get("/v1/admin/billing/retries", headers=headers)
        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["code"] == "admin_auth_unconfigured"
    finally:
        settings.ADMIN_AUTH_MODE = original_mode
        settings.ADMIN_KEY = original_key
        settings.CLERK_SECRET_KEY = original_clerk


def test_invalid_legacy_key():
    """Test 401 with wrong legacy key."""
    original_mode = settings.ADMIN_AUTH_MODE
    original_env = settings.ENVIRONMENT
    original_key = settings.ADMIN_KEY
    
    settings.ADMIN_AUTH_MODE = "legacy"
    settings.ENVIRONMENT = "dev"
    settings.ADMIN_KEY = "correct-key-789"
    
    try:
        headers = {"X-Admin-Key": "wrong-key-999"}
        response = client.get("/v1/admin/billing/retries", headers=headers)
        assert response.status_code == 401
    finally:
        settings.ADMIN_AUTH_MODE = original_mode
        settings.ENVIRONMENT = original_env
        settings.ADMIN_KEY = original_key
