"""
Phase 10.2: Tests for Clerk sync worker (dry-run safe).
"""
import uuid

from sqlalchemy import text

from backend.core.database import get_db
from backend.workers import sync_clerk_ring_balance as worker


def _create_user(db_session, clerk_id: str) -> None:
    db_session.execute(
        text('INSERT INTO users (id, "clerkId", "ringBalance", "createdAt", "updatedAt") VALUES (:id, :clerk_id, 0, NOW(), NOW())'),
        {"id": str(uuid.uuid4()), "clerk_id": clerk_id},
    )
    db_session.commit()


def test_sync_worker_marks_success(monkeypatch):
    db_session = next(get_db())
    user_id = f"sync_user_{uuid.uuid4()}"
    _create_user(db_session, user_id)
    db_session.close()

    monkeypatch.setattr(worker, "sync_user", lambda *_args, **_kwargs: True)
    result = worker.run_sync(user_id=user_id, dry_run=True, per_minute=0)
    assert result["synced"] == 1

    db_session = next(get_db())
    row = db_session.execute(
        text("SELECT last_sync_at, last_error FROM ring_clerk_sync WHERE user_id = :user_id"),
        {"user_id": user_id},
    ).fetchone()
    db_session.close()
    assert row is not None
    assert row[0] is not None
    assert row[1] is None


def test_sync_worker_marks_failure(monkeypatch):
    db_session = next(get_db())
    user_id = f"sync_user_{uuid.uuid4()}"
    _create_user(db_session, user_id)
    db_session.close()

    def _boom(*_args, **_kwargs):
        raise RuntimeError("clerk down")

    monkeypatch.setattr(worker, "sync_user", _boom)
    result = worker.run_sync(user_id=user_id, dry_run=True, per_minute=0)
    assert result["failed"] == 1

    db_session = next(get_db())
    row = db_session.execute(
        text("SELECT last_error, last_error_at FROM ring_clerk_sync WHERE user_id = :user_id"),
        {"user_id": user_id},
    ).fetchone()
    db_session.close()
    assert row is not None
    assert row[0] == "clerk down"
    assert row[1] is not None
