"""
Phase 10.2: Backfill ledger balances and validate integrity.

Dry-run by default. Use --live to apply updates.
"""
from __future__ import annotations

import argparse
import os
from typing import Dict, Optional

from sqlalchemy import text

from backend.core.database import get_db_session


def _parse_bool(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def backfill_balances(*, dry_run: bool, starting_balance: int = 0) -> Dict:
    report = {
        "users": 0,
        "rows": 0,
        "updated": 0,
        "negative_balances": 0,
        "mismatched_rows": 0,
        "publish_events_missing_ledger": 0,
        "dry_run": dry_run,
    }

    with get_db_session() as session:
        users = session.execute(text("SELECT DISTINCT user_id FROM ring_ledger")).fetchall()

    for row in users:
        user_id = row[0]
        report["users"] += 1
        running = starting_balance

        with get_db_session() as session:
            entries = session.execute(
                text(
                    """
                    SELECT id, amount, balance_after
                    FROM ring_ledger
                    WHERE user_id = :user_id
                    ORDER BY created_at ASC, id ASC
                    """
                ),
                {"user_id": user_id},
            ).fetchall()

        for entry_id, amount, balance_after in entries:
            report["rows"] += 1
            expected = running + (amount or 0)
            if balance_after is None:
                if not dry_run:
                    with get_db_session() as session:
                        session.execute(
                            text(
                                """
                                UPDATE ring_ledger
                                SET balance_after = :balance_after
                                WHERE id = :id
                                """
                            ),
                            {"balance_after": expected, "id": entry_id},
                        )
                        session.commit()
                report["updated"] += 1
                running = expected
            else:
                if int(balance_after) != int(expected):
                    report["mismatched_rows"] += 1
                    running = int(balance_after)
                else:
                    running = expected

            if running < 0:
                report["negative_balances"] += 1

    with get_db_session() as session:
        missing = session.execute(
            text(
                """
                SELECT COUNT(*)
                FROM publish_events pe
                LEFT JOIN ring_ledger rl ON rl.metadata->>'publish_event_id' = pe.id
                LEFT JOIN ring_pending rp ON rp.metadata->>'publish_event_id' = pe.id
                WHERE rl.id IS NULL AND rp.id IS NULL
                """
            )
        ).fetchone()
        report["publish_events_missing_ledger"] = int(missing[0] if missing else 0)

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill ring_ledger balances and validate.")
    parser.add_argument("--live", dest="dry_run", action="store_false", help="Apply updates to ring_ledger.")
    parser.add_argument("--dry-run", dest="dry_run", action="store_true", help="Run without writes.")
    parser.add_argument("--starting-balance", type=int, default=int(os.getenv("ONERING_LEDGER_BACKFILL_START", "0")))
    parser.set_defaults(dry_run=_parse_bool(os.getenv("ONERING_LEDGER_BACKFILL_DRY_RUN", "1"), True))
    args = parser.parse_args()

    report = backfill_balances(dry_run=args.dry_run, starting_balance=args.starting_balance)
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
