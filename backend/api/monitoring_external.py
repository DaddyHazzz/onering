"""Monitoring endpoints for external API + webhooks (admin only)."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.core.admin_auth import require_admin, AdminActor
from backend.core.database import get_db


router = APIRouter(prefix="/v1/monitoring", tags=["monitoring-external"])


class ExternalKeyMetrics(BaseModel):
    tier: str
    active: int
    revoked: int


class ExternalKeySummary(BaseModel):
    totals: List[ExternalKeyMetrics]
    total_active: int
    total_revoked: int
    last_used_at: Optional[str]


@router.get("/external/keys", response_model=ExternalKeySummary)
async def get_external_key_metrics(
    admin: AdminActor = Depends(require_admin),
    db: Session = Depends(get_db),
):
    rows = db.execute(
        text(
            """
            SELECT rate_limit_tier,
                   COUNT(*) FILTER (WHERE is_active = true) AS active,
                   COUNT(*) FILTER (WHERE is_active = false) AS revoked
            FROM external_api_keys
            GROUP BY rate_limit_tier
            """
        )
    ).fetchall()

    last_used = db.execute(text("SELECT MAX(last_used_at) FROM external_api_keys"))
    last_used_at = last_used.scalar()

    total_active = sum(row[1] or 0 for row in rows)
    total_revoked = sum(row[2] or 0 for row in rows)

    return ExternalKeySummary(
        totals=[ExternalKeyMetrics(tier=row[0], active=row[1] or 0, revoked=row[2] or 0) for row in rows],
        total_active=total_active,
        total_revoked=total_revoked,
        last_used_at=last_used_at.isoformat() if last_used_at else None,
    )


class WebhookMetrics(BaseModel):
    delivered: int
    failed: int
    dead: int
    pending: int
    delivering: int
    retrying: int


@router.get("/webhooks/metrics", response_model=WebhookMetrics)
async def get_webhook_metrics(
    admin: AdminActor = Depends(require_admin),
    db: Session = Depends(get_db),
):
    row = db.execute(
        text(
            """
            SELECT
              COUNT(*) FILTER (WHERE status = 'succeeded') AS delivered,
              COUNT(*) FILTER (WHERE status = 'failed') AS failed,
              COUNT(*) FILTER (WHERE status = 'dead') AS dead,
              COUNT(*) FILTER (WHERE status = 'pending') AS pending,
              COUNT(*) FILTER (WHERE status = 'delivering') AS delivering,
              COUNT(*) FILTER (WHERE status = 'pending' AND attempts > 0) AS retrying
            FROM webhook_deliveries
            """
        )
    ).fetchone()

    delivered, failed, dead, pending, delivering, retrying = row or (0, 0, 0, 0, 0, 0)

    return WebhookMetrics(
        delivered=delivered or 0,
        failed=failed or 0,
        dead=dead or 0,
        pending=pending or 0,
        delivering=delivering or 0,
        retrying=retrying or 0,
    )


class WebhookDeliveryItem(BaseModel):
    id: str
    webhook_id: str
    event_id: str
    event_type: str
    status: str
    attempts: int
    last_status_code: Optional[int]
    last_error: Optional[str]
    created_at: str
    next_attempt_at: Optional[str]


class WebhookRecentResponse(BaseModel):
    deliveries: List[WebhookDeliveryItem]


@router.get("/webhooks/recent", response_model=WebhookRecentResponse)
async def get_recent_webhook_deliveries(
    status: Optional[str] = None,
    event_type: Optional[str] = None,
    webhook_id: Optional[str] = None,
    limit: int = 20,
    admin: AdminActor = Depends(require_admin),
    db: Session = Depends(get_db),
):
    clauses = ["1=1"]
    params = {"limit": min(limit, 100)}
    if status:
        clauses.append("status = :status")
        params["status"] = status
    if event_type:
        clauses.append("event_type = :event_type")
        params["event_type"] = event_type
    if webhook_id:
        clauses.append("webhook_id = :webhook_id")
        params["webhook_id"] = webhook_id

    where_clause = " AND ".join(clauses)
    rows = db.execute(
        text(
            f"""
            SELECT id, webhook_id, event_id, event_type, status, attempts, last_status_code, last_error, created_at, next_attempt_at
            FROM webhook_deliveries
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT :limit
            """
        ),
        params,
    ).fetchall()

    return WebhookRecentResponse(
        deliveries=[
            WebhookDeliveryItem(
                id=str(row[0]),
                webhook_id=str(row[1]),
                event_id=str(row[2]),
                event_type=row[3],
                status=row[4],
                attempts=row[5],
                last_status_code=row[6],
                last_error=row[7],
                created_at=row[8].isoformat(),
                next_attempt_at=row[9].isoformat() if row[9] else None,
            )
            for row in rows
        ]
    )
