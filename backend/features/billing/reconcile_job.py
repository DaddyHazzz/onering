"""
Scheduled reconciliation job (Phase 4.5).

Runs the same reconciliation logic as the admin endpoint, writing job runs
and audits with actor="system_job".
"""
from __future__ import annotations

from datetime import datetime
from typing import Dict, Any
from sqlalchemy import select, update, insert

from backend.core.database import (
    get_db_session,
    billing_subscriptions,
    billing_events,
    billing_admin_audit,
    billing_job_runs,
)


def run_reconcile_job(now: datetime, fix: bool = False, limit: int = 100) -> Dict[str, Any]:
    issues = []
    corrections = 0
    valid_statuses = {"active", "past_due", "canceled", "unpaid"}

    with get_db_session() as session:
        subs = session.execute(select(billing_subscriptions)).fetchall()
        corrected = []
        for s in subs:
            if s.status not in valid_statuses:
                issues.append({
                    "type": "invalid_status",
                    "subscription_id": s.id,
                    "user_id": s.user_id,
                    "status": s.status,
                })
                if fix and len(corrected) < limit:
                    session.execute(
                        update(billing_subscriptions)
                        .where(billing_subscriptions.c.id == s.id)
                        .values(status='unpaid')
                    )
                    corrections += 1
                    corrected.append(s)

        # Audit corrections
        for s in corrected:
            session.execute(
                insert(billing_admin_audit).values(
                    actor="system_job",
                    action="reconcile_fix",
                    target_user_id=s.user_id,
                    target_resource=str(s.id),
                    payload_json="{\"new_status\": \"unpaid\"}",
                )
            )

        # Record job run
        stats = {
            "issues_found": len(issues),
            "corrections_applied": corrections,
        }
        session.execute(
            insert(billing_job_runs).values(
                job_name="system.reconcile",
                started_at=now,
                finished_at=datetime.utcnow(),
                status="success",
                stats_json=str(stats),
            )
        )
        session.commit()

    return {
        "issues_found": len(issues),
        "corrections_applied": corrections,
        "timestamp": now.isoformat(),
    }
