"""
Tests for health and diagnostics endpoints (Phase 3.7).
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


def test_health_db_success(client):
    """Test health endpoint with successful database connection."""
    response = client.get("/api/health/db")
    
    assert response.status_code == 200
    data = response.json()
    
    assert 'ok' in data
    assert 'db' in data
    assert 'computed_at' in data
    
    # Should be successful (assuming DB is running)
    assert data['ok'] is True
    assert data['db']['connected'] is True
    
    # Should list tables without exposing credentials
    assert 'tables_present' in data['db']
    assert isinstance(data['db']['tables_present'], list)
    
    # Should NOT expose credentials
    assert data['db']['database'] is None
    assert data['db']['user'] is None


def test_health_db_deterministic_with_now_param(client):
    """Test that health endpoint is deterministic when 'now' param is provided."""
    test_timestamp = "2025-12-22T10:00:00+00:00"
    response = client.get(f"/api/health/db?now={test_timestamp}")
    
    assert response.status_code == 200
    data = response.json()
    
    # Should use provided timestamp (may be slightly transformed by JSON encoder)
    # Just verify it contains the core timestamp
    assert "2025-12-22T10:00:00" in data['computed_at']
    
    # Should exclude latency for determinism
    assert data['db']['latency_ms'] is None


def test_health_db_includes_latency_without_now(client):
    """Test that latency is included when 'now' parameter is not provided."""
    response = client.get("/api/health/db")
    
    assert response.status_code == 200
    data = response.json()
    
    # Should include latency as a number
    # (We don't assert exact value as it varies, just that it exists and is reasonable)
    if data['db']['connected']:
        assert data['db']['latency_ms'] is not None
        assert isinstance(data['db']['latency_ms'], (int, float))
        assert 0 <= data['db']['latency_ms'] < 5000  # Sanity check: under 5 seconds


def test_health_db_response_shape(client):
    """Test that health response conforms to the expected schema."""
    response = client.get("/api/health/db")
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify structure
    assert isinstance(data, dict)
    assert isinstance(data['ok'], bool)
    assert isinstance(data['db'], dict)
    assert isinstance(data['computed_at'], str)
    
    # Verify db sub-structure
    db = data['db']
    assert isinstance(db['connected'], bool)
    assert db['database'] is None or isinstance(db['database'], str)
    assert db['user'] is None or isinstance(db['user'], str)
    assert db['latency_ms'] is None or isinstance(db['latency_ms'], (int, float))
    assert isinstance(db['tables_present'], list)
    
    for table in db['tables_present']:
        assert isinstance(table, str)


def test_health_db_no_secrets_leak(client):
    """Test that health endpoint doesn't leak sensitive information."""
    response = client.get("/api/health/db")
    
    assert response.status_code == 200
    data = response.json()
    response_str = str(data)
    
    # Should not contain password-like strings
    # (This is a basic check; real secrets shouldn't be in response anyway)
    assert 'password' not in response_str.lower()
    assert 'secret' not in response_str.lower()
    assert 'token' not in response_str.lower()
    
    # Should not expose postgres connection details
    assert 'localhost' not in response_str or 'postgres' not in response_str
