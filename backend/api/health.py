"""
Health and diagnostics API for OneRing backend (Phase 3.7).

Provides lightweight endpoints for operational monitoring without exposing secrets.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from pydantic import BaseModel
import time

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from sqlalchemy import text, inspect

from backend.core.database import get_db_session, check_connection, get_engine
from backend.core.logging import latency_bucket_ms, get_request_id

logger = logging.getLogger("onering")

router = APIRouter(prefix="/api/health", tags=["health"])
root_router = APIRouter(tags=["health"])


class DBHealth(BaseModel):
    """Database health status."""
    connected: bool
    database: Optional[str] = None
    user: Optional[str] = None
    latency_ms: Optional[float] = None  # Can be None for determinism in tests
    tables_present: list[str] = []


class HealthResponse(BaseModel):
    """Health check response."""
    ok: bool
    db: DBHealth
    computed_at: str  # UTC ISO format


@root_router.get("/healthz")
def healthz():
    """Lightweight liveness check (no deps)."""
    return {"status": "ok"}


@root_router.get("/readyz")
def readyz():
    """Readiness check: DB connectivity + required tables."""
    required_tables = [
        "drafts",
        "draft_segments",
        "draft_collaborators",
        "ring_passes",
        "audit_events",
    ]

    try:
        engine = get_engine()
        # Connection probe
        with engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")

        # Table existence probe (non-fatal per-table)
        inspector = inspect(engine)
        missing = [t for t in required_tables if not inspector.has_table(t)]
        if missing:
            detail = f"missing tables: {', '.join(missing)}"
            logger.warning(f"[readyz] {detail}")
            return JSONResponse(status_code=503, content={"status": "error", "detail": detail})

        return {"status": "ok"}
    except Exception as e:
        logger.error(f"[readyz] readiness check failed: {e}")
        return JSONResponse(status_code=503, content={"status": "error", "detail": "database unreachable"})


@router.get("/db", response_model=HealthResponse)
async def health_db(now: Optional[str] = Query(None)):
    """
    Check database health and connectivity.
    
    This is a lightweight internal endpoint (no auth required).
    Safe to expose: returns no secrets, passwords, or stack traces.
    
    Args:
        now: Optional ISO timestamp for deterministic testing (overrides system time)
    
    Returns:
        HealthResponse with db connection status
    """
    try:
        # Measure connection latency
        start = time.perf_counter()
        is_connected = check_connection()
        latency_ms = (time.perf_counter() - start) * 1000
        
        db_health = DBHealth(
            connected=is_connected,
            database=None,  # Don't expose DB name for security
            user=None,      # Don't expose user for security
            latency_ms=None if now else latency_ms,  # Exclude latency if testing
            tables_present=[]
        )
        
        latency_bucket = latency_bucket_ms(latency_ms if now is None else None)

        if is_connected:
            # List tables that exist
            try:
                with get_db_session() as session:
                    result = session.execute(text(
                        """
                        SELECT table_name FROM information_schema.tables
                        WHERE table_schema = 'public'
                        ORDER BY table_name
                        """
                    ))
                    tables = [row[0] for row in result]
                    db_health.tables_present = tables
            except Exception as e:
                logger.warning(f"[health] Failed to list tables: {e}")
                # Still return ok=True if connection works, just no table list
        
        # Compute timestamp (use provided 'now' for determinism in tests)
        timestamp = now or datetime.now(timezone.utc).isoformat()

        logger.info(
            "health.db",
            extra={
                "request_id": get_request_id(),
                "ok": is_connected,
                "latency_bucket": latency_bucket,
            },
        )

        return HealthResponse(
            ok=is_connected,
            db=db_health,
            computed_at=timestamp
        )
    
    except Exception as e:
        logger.error(
            f"[health/db] Error: {e}",
            extra={"request_id": get_request_id()},
        )
        # Return error without exposing details
        return HealthResponse(
            ok=False,
            db=DBHealth(
                connected=False,
                database=None,
                user=None,
                latency_ms=None,
                tables_present=[]
            ),
            computed_at=now or datetime.now(timezone.utc).isoformat()
        )
