"""Cleanup job for enforcement audit retention (Phase 10.1)."""
from datetime import datetime, timedelta, timezone
import logging

from sqlalchemy import delete, select, func

from backend.core.config import settings
from backend.core.database import audit_agent_decisions, get_db_session

logger = logging.getLogger("onering.cleanup.enforcement")


def cleanup_enforcement_audit(
    *,
    retention_days: int | None = None,
    dry_run: bool | None = None,
) -> dict:
    days = retention_days if retention_days is not None else int(settings.ONERING_AUDIT_RETENTION_DAYS or 30)
    dry = dry_run if dry_run is not None else str(settings.ONERING_AUDIT_CLEANUP_DRY_RUN) == "1"
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    with get_db_session() as session:
        count_stmt = select(func.count()).select_from(audit_agent_decisions).where(
            audit_agent_decisions.c.created_at < cutoff
        )
        to_prune = session.execute(count_stmt).scalar() or 0

        deleted = 0
        if not dry and to_prune:
            delete_stmt = delete(audit_agent_decisions).where(
                audit_agent_decisions.c.created_at < cutoff
            )
            result = session.execute(delete_stmt)
            deleted = result.rowcount or 0

    logger.info(
        "[cleanup] enforcement audit retention",
        extra={"retention_days": days, "dry_run": dry, "candidates": to_prune, "deleted": deleted},
    )
    return {"retention_days": days, "dry_run": dry, "candidates": to_prune, "deleted": deleted}


if __name__ == "__main__":
    result = cleanup_enforcement_audit()
    print(result)
