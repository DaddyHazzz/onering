"""
Tests for scheduled reconciliation job (Phase 4.5).
"""

import pytest
from datetime import datetime
from sqlalchemy import select

from backend.core.database import (
    create_all_tables, 
    reset_database,
    get_db_session, 
    billing_subscriptions, 
    billing_admin_audit, 
    billing_job_runs
)
from backend.features.billing.reconcile_job import run_reconcile_job


@pytest.fixture(autouse=True)
def _reset_db():
    """Reset database before each test."""
    reset_database()
    create_all_tables()
    yield
    reset_database()


def test_reconcile_job_records_job_run():
    now = datetime.utcnow()

    # Just call reconcile with fix=false (no mutations)
    result = run_reconcile_job(now=now, fix=False)
    assert result["issues_found"] >= 0
    assert result["corrections_applied"] == 0

    # Verify job run was recorded even with no issues
    with get_db_session() as session:
        runs = session.execute(select(billing_job_runs)).fetchall()
        assert len(runs) >= 1
        assert runs[0].job_name == "system.reconcile"
        assert runs[0].status == "success"
