"""
Structured logging with request ID support (Phase 6.3).

Features:
- JSON logs in production, pretty logs in development.
- Context-bound request_id for correlation.
- log_event helper for consistent structured logs with safe truncation.
"""

import json
import logging
import os
import sys
import time
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Dict, Optional
from uuid import uuid4

request_id_ctx_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


def get_request_id(default: Optional[str] = None) -> Optional[str]:
    """Fetch the current request_id from context (if any)."""
    rid = request_id_ctx_var.get()
    return rid if rid is not None else default


def _format_timestamp(record: logging.LogRecord) -> str:
    return datetime.fromtimestamp(record.created, timezone.utc).isoformat().replace('+00:00', 'Z')


def latency_bucket_ms(latency_ms: Optional[float]) -> str:
    if latency_ms is None:
        return "unknown"
    if latency_ms < 10:
        return "<10ms"
    if latency_ms < 100:
        return "10-100ms"
    if latency_ms < 500:
        return "100-500ms"
    if latency_ms < 1000:
        return "500-1000ms"
    return ">=1000ms"

class RequestIdFilter(logging.Filter):
    """Inject request_id into log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        if getattr(record, "request_id", None) is None:
            record.request_id = get_request_id()
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": _format_timestamp(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", None),
        }
        return json.dumps(payload, default=str)


class PrettyFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        rid = getattr(record, "request_id", None)
        rid_part = f" [rid={rid}]" if rid else ""
        ts = _format_timestamp(record)
        return f"{ts} {record.levelname} [onering]{rid_part} {record.getMessage()}"


def configure_logging(env: str = "development") -> None:
    """Configure structured logging based on environment."""
    logger = logging.getLogger("onering")
    logger.setLevel(logging.INFO)

    formatter: logging.Formatter
    if env.lower() == "production":
        formatter = JsonFormatter()
    else:
        formatter = PrettyFormatter()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.addFilter(RequestIdFilter())

    logger.handlers = [handler]
    logger.propagate = True

    # Reduce noise from uvicorn loggers but keep error output
    logging.getLogger("uvicorn").propagate = False
    logging.getLogger("uvicorn.error").propagate = False

def _safe_truncate(value, limit: int = 500):
    try:
        text = str(value)
    except Exception:
        return "<unserializable>"
    if len(text) <= limit:
        return text
    return text[:limit] + "...<truncated>"


def log_event(
    level: str,
    msg: str,
    *,
    request_id: Optional[str],
    user_id: Optional[str] = None,
    draft_id: Optional[str] = None,
    event_type: Optional[str] = None,
    error_code: Optional[str] = None,
    extra: Optional[Dict[str, object]] = None,
):
    """Structured logging helper with safe truncation and request correlation."""

    logger = logging.getLogger("onering")
    if not logger.handlers:
        # Ensure logging configured in edge cases (tests)
        configure_logging(os.getenv("ENV", "development"))

    payload = {
        "request_id": request_id or get_request_id(),
        "user_id": user_id,
        "draft_id": draft_id,
    }
    if event_type:
        payload["event_type"] = event_type
    if error_code:
        payload["error_code"] = error_code
    if extra:
        for k, v in extra.items():
            payload[k] = _safe_truncate(v)

    log_fn = getattr(logger, level, logger.info)
    log_fn(msg, extra=payload)

