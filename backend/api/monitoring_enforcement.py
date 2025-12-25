"""Enforcement monitoring endpoints (Phase 10.1)."""
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, desc

from backend.core.admin_auth import require_admin, AdminActor
from backend.core.database import audit_agent_decisions, get_db_session
from backend.features.enforcement.contracts import QA_AGENT_NAME

router = APIRouter(prefix="/v1/monitoring/enforcement", tags=["monitoring"])


class EnforcementRecentItem(BaseModel):
    request_id: Optional[str]
    receipt_id: Optional[str]
    mode: Optional[str]
    qa_status: Optional[str]
    violation_codes_count: int = 0
    audit_ok: bool = True
    created_at: Optional[str]
    expires_at: Optional[str]
    latency_ms: Optional[int] = None
    last_error_code: Optional[str] = None
    last_error_at: Optional[str] = None


class EnforcementRecentResponse(BaseModel):
    items: List[EnforcementRecentItem]


class EnforcementMetrics(BaseModel):
    qa_blocked: int = 0
    enforcement_receipt_required: int = 0
    enforcement_receipt_expired: int = 0
    audit_write_failed: int = 0
    policy_error: int = 0
    p90_latency_ms: Optional[int] = None


class EnforcementMetricsResponse(BaseModel):
    window_hours: int = 24
    metrics: EnforcementMetrics


def _parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


@router.get("/recent", response_model=EnforcementRecentResponse)
def recent_enforcement(
    limit: int = Query(50, ge=1, le=200),
    since: Optional[str] = Query(None),
    actor: AdminActor = Depends(require_admin),
):
    since_dt = _parse_iso(since)
    items: List[EnforcementRecentItem] = []

    with get_db_session() as session:
        stmt = (
            select(audit_agent_decisions)
            .where(audit_agent_decisions.c.agent_name == QA_AGENT_NAME)
            .order_by(desc(audit_agent_decisions.c.created_at))
            .limit(limit)
        )
        if since_dt:
            stmt = stmt.where(audit_agent_decisions.c.created_at >= since_dt)

        rows = session.execute(stmt).fetchall()
        for row in rows:
            decision_json = row.decision_json or {}
            output = decision_json.get("output") if isinstance(decision_json, dict) else {}
            receipt = output.get("receipt") if isinstance(output, dict) else {}
            qa = output.get("qa") if isinstance(output, dict) else {}
            qa_status = qa.get("status")
            violation_codes = qa.get("violation_codes") or []
            latency_ms = None
            meta = decision_json.get("meta") if isinstance(decision_json, dict) else {}
            if isinstance(meta, dict):
                latency_ms = meta.get("latency_ms")

            last_error_code = None
            last_error_at = None
            if qa_status == "FAIL":
                last_error_code = "QA_BLOCKED"
                last_error_at = row.created_at.isoformat() if row.created_at else None

            items.append(
                EnforcementRecentItem(
                    request_id=row.request_id,
                    receipt_id=receipt.get("receipt_id"),
                    mode=output.get("mode") if isinstance(output, dict) else None,
                    qa_status=qa_status,
                    violation_codes_count=len(violation_codes) if isinstance(violation_codes, list) else 0,
                    audit_ok=True,
                    created_at=row.created_at.isoformat() if row.created_at else None,
                    expires_at=receipt.get("expires_at"),
                    latency_ms=latency_ms,
                    last_error_code=last_error_code,
                    last_error_at=last_error_at,
                )
            )

    return EnforcementRecentResponse(items=items)


@router.get("/metrics", response_model=EnforcementMetricsResponse)
def enforcement_metrics(
    actor: AdminActor = Depends(require_admin),
):
    window_hours = 24
    cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    latencies: List[int] = []
    qa_blocked = 0

    with get_db_session() as session:
        stmt = (
            select(audit_agent_decisions.c.decision_json)
            .where(
                audit_agent_decisions.c.agent_name == QA_AGENT_NAME,
                audit_agent_decisions.c.created_at >= cutoff,
            )
        )
        for row in session.execute(stmt):
            decision_json = row.decision_json or {}
            output = decision_json.get("output") if isinstance(decision_json, dict) else {}
            qa = output.get("qa") if isinstance(output, dict) else {}
            if qa.get("status") == "FAIL":
                qa_blocked += 1
            meta = decision_json.get("meta") if isinstance(decision_json, dict) else {}
            if isinstance(meta, dict):
                latency = meta.get("latency_ms")
                if isinstance(latency, int):
                    latencies.append(latency)

    p90_latency = None
    if latencies:
        latencies.sort()
        index = int(len(latencies) * 0.9) - 1
        index = max(0, min(index, len(latencies) - 1))
        p90_latency = latencies[index]

    metrics = EnforcementMetrics(
        qa_blocked=qa_blocked,
        enforcement_receipt_required=0,
        enforcement_receipt_expired=0,
        audit_write_failed=0,
        policy_error=0,
        p90_latency_ms=p90_latency,
    )
    return EnforcementMetricsResponse(window_hours=window_hours, metrics=metrics)
