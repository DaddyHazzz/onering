"""
Phase 10.2: Clerk sync worker for ring balances.

Best-effort, dry-run by default. Uses ledger truth from tokens summary.
"""
from __future__ import annotations

import argparse
import os
import time
from datetime import datetime, timezone
from typing import Optional, Dict

import httpx
from sqlalchemy import text

from backend.core.config import settings
from backend.core.database import get_db_session
from backend.features.tokens.balance import get_effective_ring_balance


CLERK_API_BASE = "https://api.clerk.com/v1"


def _parse_bool(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _mark_sync(db, user_id: str, *, last_sync_at: Optional[datetime], last_error: Optional[str]) -> None:
    db.execute(
        text(
            """
            INSERT INTO ring_clerk_sync (user_id, last_sync_at, last_error, last_error_at)
            VALUES (:user_id, :last_sync_at, :last_error, :last_error_at)
            ON CONFLICT (user_id)
            DO UPDATE SET last_sync_at = :last_sync_at,
                          last_error = :last_error,
                          last_error_at = :last_error_at,
                          updated_at = NOW()
            """
        ),
        {
            "user_id": user_id,
            "last_sync_at": last_sync_at,
            "last_error": last_error,
            "last_error_at": None if last_error is None else datetime.now(timezone.utc),
        },
    )
    db.commit()


def sync_user(user_id: str, *, dry_run: bool) -> bool:
    if not settings.CLERK_SECRET_KEY:
        raise RuntimeError("CLERK_SECRET_KEY is not configured")

    with get_db_session() as session:
        summary = get_effective_ring_balance(session, user_id)
        effective_balance = summary["effective_balance"]

    if dry_run:
        return True

    payload = {
        "public_metadata": {
            "ring": effective_balance,
            "ring_last_synced_at": datetime.now(timezone.utc).isoformat(),
        }
    }
    headers = {
        "Authorization": f"Bearer {settings.CLERK_SECRET_KEY}",
        "Content-Type": "application/json",
    }
    url = f"{CLERK_API_BASE}/users/{user_id}"

    with httpx.Client(timeout=10.0) as client:
        response = client.patch(url, headers=headers, json=payload)
        if response.status_code >= 300:
            raise RuntimeError(f"Clerk sync failed: {response.status_code} {response.text}")
    return True


def run_sync(user_id: Optional[str] = None, *, dry_run: bool = True, per_minute: int = 60) -> Dict:
    results = {"synced": 0, "failed": 0, "dry_run": dry_run}
    delay = 0 if per_minute <= 0 else max(0.0, 60.0 / float(per_minute))

    with get_db_session() as session:
        if user_id:
            user_ids = [user_id]
        else:
            rows = session.execute(text('SELECT "clerkId" FROM users')).fetchall()
            user_ids = [row[0] for row in rows if row and row[0]]

    for uid in user_ids:
        try:
            sync_user(uid, dry_run=dry_run)
            with get_db_session() as session:
                _mark_sync(session, uid, last_sync_at=datetime.now(timezone.utc), last_error=None)
            results["synced"] += 1
        except Exception as exc:
            with get_db_session() as session:
                _mark_sync(session, uid, last_sync_at=None, last_error=str(exc))
            results["failed"] += 1
        if delay:
            time.sleep(delay)

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync Clerk ring balances from ledger truth.")
    parser.add_argument("--user-id", dest="user_id", help="Optional Clerk user ID to sync.")
    parser.add_argument("--dry-run", dest="dry_run", action="store_true", help="Run without calling Clerk.")
    parser.add_argument("--live", dest="dry_run", action="store_false", help="Perform live Clerk updates.")
    parser.add_argument("--per-minute", dest="per_minute", type=int, default=int(os.getenv("ONERING_CLERK_SYNC_PER_MINUTE", "60")))
    parser.set_defaults(dry_run=_parse_bool(os.getenv("ONERING_CLERK_SYNC_DRY_RUN", "1"), True))
    args = parser.parse_args()

    result = run_sync(args.user_id, dry_run=args.dry_run, per_minute=args.per_minute)
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
