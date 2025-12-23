"""
Admin API tests for billing retry endpoints.
Uses FastAPI TestClient with DB override and StaticPool.
"""

import os
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, insert
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from backend.main import app
from backend.core.database import billing_retry_queue, get_db


client = TestClient(app)


def _override_get_db(session):
    def _gen():
        try:
            yield session
        finally:
            pass
    return _gen


def test_admin_retries_endpoint_exists():
    """Verify admin retry endpoints are registered."""
    from fastapi.testclient import TestClient
    from backend.main import app
    
    client = TestClient(app)
    
    # Set up admin key
    import os
    os.environ["ADMIN_API_KEY"] = "test-key"
    
    # Endpoint should exist (returns 401 without proper auth to verify registered)
    response = client.get("/v1/admin/billing/retries")
    assert response.status_code == 401
