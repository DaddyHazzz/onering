"""Token monitoring endpoints (Phase 10.2 publish integration)."""
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import text

from backend.core.admin_auth import require_admin, AdminActor
from backend.core.database import get_db_session

router = APIRouter(prefix="/v1/monitoring/tokens", tags=["monitoring"])


class TokenEventItem(BaseModel):
    event_id: str
    user_id: str
    platform: str
    published_at: Optional[str]
    platform_post_id: Optional[str]
    enforcement_request_id: Optional[str]
    enforcement_receipt_id: Optional[str]
    qa_status: Optional[str]
    violation_codes: List[str] = []
    audit_ok: bool
    token_mode: Optional[str]
    token_issued_amount: Optional[int]
    token_pending_amount: Optional[int]
    token_reason_code: Optional[str]
    token_ledger_id: Optional[str]
    token_pending_id: Optional[str]
    issuance_latency_ms: Optional[int] = None
    created_at: Optional[str]


class TokenEventsResponse(BaseModel):
    items: List[TokenEventItem]


class TokenMetrics(BaseModel):
    total_issued: int = 0
    total_pending: int = 0
    blocked_issuance: int = 0
    top_reason_codes: Dict[str, int] = {}
    p90_issuance_latency_ms: Optional[int] = None


class TokenMetricsResponse(BaseModel):
    window_hours: int = 24
    metrics: TokenMetrics


def _parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


@router.get("/recent", response_model=TokenEventsResponse)
def recent_publish_events(
    limit: int = Query(50, ge=1, le=200),
    since: Optional[str] = Query(None),
    actor: AdminActor = Depends(require_admin),
):
    since_dt = _parse_iso(since)
    items: List[TokenEventItem] = []

    with get_db_session() as session:
        stmt = text(
            """
            SELECT id, user_id, platform, published_at, platform_post_id,
                   enforcement_request_id, enforcement_receipt_id, qa_status, violation_codes, audit_ok,
                   token_mode, token_issued_amount, token_pending_amount, token_reason_code,
                   token_ledger_id, token_pending_id, metadata, created_at
            FROM publish_events
            WHERE (:since IS NULL OR created_at >= :since)
            ORDER BY created_at DESC
            LIMIT :limit
            """
        )
        rows = session.execute(stmt, {"since": since_dt, "limit": limit}).fetchall()
        for row in rows:
            metadata = row[16] or {}
            latency = None
            if isinstance(metadata, dict):
                latency = metadata.get("issuance_latency_ms")
            items.append(
                TokenEventItem(
                    event_id=str(row[0]),
                    user_id=row[1],
                    platform=row[2],
                    published_at=row[3].isoformat() if row[3] else None,
                    platform_post_id=row[4],
                    enforcement_request_id=row[5],
                    enforcement_receipt_id=row[6],
                    qa_status=row[7],
                    violation_codes=row[8] or [],
                    audit_ok=bool(row[9]),
                    token_mode=row[10],
                    token_issued_amount=row[11],
                    token_pending_amount=row[12],
                    token_reason_code=row[13],
                    token_ledger_id=row[14],
                    token_pending_id=row[15],
                    issuance_latency_ms=latency if isinstance(latency, int) else None,
                    created_at=row[17].isoformat() if row[17] else None,
                )
            )

    return TokenEventsResponse(items=items)


@router.get("/metrics", response_model=TokenMetricsResponse)
def token_metrics(
    actor: AdminActor = Depends(require_admin),
):
    window_hours = 24
    cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)

    with get_db_session() as session:
        totals_row = session.execute(
            text(
                """
                SELECT COALESCE(SUM(token_issued_amount), 0), COALESCE(SUM(token_pending_amount), 0)
                FROM publish_events
                WHERE created_at >= :cutoff
                """
            ),
            {"cutoff": cutoff},
        ).fetchone()
        total_issued = int(totals_row[0] or 0)
        total_pending = int(totals_row[1] or 0)

        reason_rows = session.execute(
            text(
                """
                SELECT token_reason_code, COUNT(*)
                FROM publish_events
                WHERE created_at >= :cutoff
                  AND token_reason_code IS NOT NULL
                GROUP BY token_reason_code
                """
            ),
            {"cutoff": cutoff},
        ).fetchall()
        top_reason_codes = {row[0]: int(row[1]) for row in reason_rows if row[0]}

        blocked = 0
        for code, count in top_reason_codes.items():
            if code not in {"ISSUED", "PENDING"}:
                blocked += count

        latency_rows = session.execute(
            text(
                """
                SELECT (metadata->>'issuance_latency_ms')::int
                FROM publish_events
                WHERE created_at >= :cutoff
                  AND (metadata->>'issuance_latency_ms') IS NOT NULL
                """
            ),
            {"cutoff": cutoff},
        ).fetchall()
        latencies = [row[0] for row in latency_rows if isinstance(row[0], int)]
        p90_latency = None
        if latencies:
            latencies.sort()
            index = int(len(latencies) * 0.9) - 1
            index = max(0, min(index, len(latencies) - 1))
            p90_latency = latencies[index]

    metrics = TokenMetrics(
        total_issued=total_issued,
        total_pending=total_pending,
        blocked_issuance=blocked,
        top_reason_codes=top_reason_codes,
        p90_issuance_latency_ms=p90_latency,
    )
    return TokenMetricsResponse(window_hours=window_hours, metrics=metrics)
