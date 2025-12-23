"""
Schema tests for Phase 4.5 billing retry and job run tables.
"""

from sqlalchemy import inspect

from backend.core.database import create_all_tables, get_engine


def test_billing_retry_queue_table_exists_and_columns():
    create_all_tables()
    engine = get_engine()
    insp = inspect(engine)

    assert "billing_retry_queue" in insp.get_table_names()
    cols = {c["name"] for c in insp.get_columns("billing_retry_queue")}
    for col in [
        "id",
        "stripe_event_id",
        "last_error",
        "attempt_count",
        "next_attempt_at",
        "locked_at",
        "lock_owner",
        "status",
        "created_at",
        "updated_at",
    ]:
        assert col in cols


def test_billing_retry_queue_indexes_and_constraints():
    create_all_tables()
    engine = get_engine()
    insp = inspect(engine)

    # Unique constraint on stripe_event_id
    uks = insp.get_unique_constraints("billing_retry_queue")
    uk_names = {uk.get("name") for uk in uks}
    assert "uq_billing_retry_stripe_event_id" in uk_names

    # Due index on (status, next_attempt_at)
    idxs = {idx["name"]: idx for idx in insp.get_indexes("billing_retry_queue")}
    assert "idx_billing_retry_due" in idxs
    cols = idxs["idx_billing_retry_due"]["column_names"]
    assert cols == ["status", "next_attempt_at"]


def test_billing_job_runs_table_exists_and_columns():
    create_all_tables()
    engine = get_engine()
    insp = inspect(engine)

    assert "billing_job_runs" in insp.get_table_names()
    cols = {c["name"] for c in insp.get_columns("billing_job_runs")}
    for col in [
        "id",
        "job_name",
        "started_at",
        "finished_at",
        "status",
        "stats_json",
        "error",
    ]:
        assert col in cols


def test_billing_job_runs_indexes():
    create_all_tables()
    engine = get_engine()
    insp = inspect(engine)
    idxs = {idx["name"]: idx for idx in insp.get_indexes("billing_job_runs")}
    assert "idx_billing_job_runs_job_name" in idxs
    assert "idx_billing_job_runs_started" in idxs
