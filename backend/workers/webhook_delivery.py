"""Webhook delivery worker.

Usage:
    python -m backend.workers.webhook_delivery --once
    python -m backend.workers.webhook_delivery --loop

Environment flags:
- ONERING_WEBHOOKS_DELIVERY_ENABLED (0/1) default 0
- ONERING_WEBHOOKS_MAX_ATTEMPTS (default 3)
- ONERING_WEBHOOKS_BACKOFF_SECONDS (csv, default 60,300,900)
- ONERING_WEBHOOKS_DELIVERY_LOOP_SECONDS (default 5)
"""
from __future__ import annotations

import argparse
import asyncio
import os
import time
from typing import List

from backend.core.database import get_db
from backend.features.external.webhooks import (
    get_pending_deliveries,
    deliver_webhook,
    is_delivery_enabled,
)


DEFAULT_LOOP_SECONDS = int(os.getenv("ONERING_WEBHOOKS_DELIVERY_LOOP_SECONDS", "5") or 5)


async def _process_once(limit: int = 100) -> int:
    delivered = 0
    db = next(get_db())
    try:
        pending: List[str] = get_pending_deliveries(db, limit=limit)
        for delivery_id in pending:
            success = await deliver_webhook(db, delivery_id)
            if success:
                delivered += 1
    finally:
        db.close()
    return delivered


def main() -> None:
    parser = argparse.ArgumentParser(description="Webhook delivery worker")
    parser.add_argument("--once", action="store_true", help="Process pending deliveries once and exit")
    parser.add_argument("--loop", action="store_true", help="Run in continuous loop")
    parser.add_argument("--limit", type=int, default=100, help="Batch size per iteration")
    parser.add_argument(
        "--sleep",
        type=int,
        default=DEFAULT_LOOP_SECONDS,
        help="Seconds to sleep between loops (when --loop)",
    )
    args = parser.parse_args()

    if not is_delivery_enabled():
        print("[webhook-worker] Delivery disabled (ONERING_WEBHOOKS_DELIVERY_ENABLED=0). Exiting.")
        return

    if args.once:
        delivered = asyncio.run(_process_once(limit=args.limit))
        print(f"[webhook-worker] Delivered: {delivered}")
        return

    # Default to loop mode when not explicitly once
    print(
        f"[webhook-worker] Starting loop (sleep={args.sleep}s, batch={args.limit}). CTRL+C to stop."
    )
    try:
        while True:
            delivered = asyncio.run(_process_once(limit=args.limit))
            if delivered:
                print(f"[webhook-worker] Delivered {delivered} notifications")
            time.sleep(args.sleep)
    except KeyboardInterrupt:
        print("[webhook-worker] Stopped")


if __name__ == "__main__":
    main()
