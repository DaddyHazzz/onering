"""
Phase 10.2: Backfill validator tests.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import text

from backend.core.database import get_db
from backend.workers.backfill_ring_ledger import backfill_balances


def test_backfill_reports_mismatch_and_missing_publish():
    db_session = next(get_db())
    user_id = f"backfill_user_{uuid.uuid4()}"
    db_session.execute(
        text('INSERT INTO users (id, "clerkId", "ringBalance", "createdAt", "updatedAt") VALUES (:id, :clerk_id, 0, NOW(), NOW())'),
        {"id": str(uuid.uuid4()), "clerk_id": user_id},
    )
    db_session.execute(
        text(
            """
            INSERT INTO ring_ledger (user_id, event_type, reason_code, amount, balance_after, metadata, created_at)
            VALUES (:user_id, 'EARN', 'test', 10, 5, '{}'::jsonb, :created_at)
            """
        ),
        {"user_id": user_id, "created_at": datetime.now(timezone.utc)},
    )
    db_session.execute(
        text(
            """
            INSERT INTO publish_events
            (id, user_id, platform, content_hash, published_at, platform_post_id, audit_ok, metadata)
            VALUES (:id, :user_id, 'x', 'hash', :published_at, 'post-1', true, '{}'::jsonb)
            """
        ),
        {"id": f"evt-{uuid.uuid4()}", "user_id": user_id, "published_at": datetime.now(timezone.utc)},
    )
    db_session.commit()
    db_session.close()

    report = backfill_balances(dry_run=True)
    assert report["mismatched_rows"] >= 1
    assert report["publish_events_missing_ledger"] >= 1

    db_session = next(get_db())
    db_session.execute(text('DELETE FROM ring_ledger WHERE user_id = :user_id'), {"user_id": user_id})
    db_session.execute(text('DELETE FROM publish_events WHERE user_id = :user_id'), {"user_id": user_id})
    db_session.execute(text('DELETE FROM users WHERE "clerkId" = :user_id'), {"user_id": user_id})
    db_session.commit()
    db_session.close()
