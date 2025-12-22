"""
Structured logging with request ID support (Phase 3.8).

Features:
- JSON logs in production, pretty logs in development.
- Context-bound request_id for correlation.
- RequestIdMiddleware adds request_id to headers and log context.
"""

import json
import logging
import os
import sys
import time
from contextvars import ContextVar
from datetime import datetime
from typing import Optional
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware

request_id_ctx_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


def get_request_id(default: Optional[str] = None) -> Optional[str]:
    """Fetch the current request_id from context (if any)."""
    rid = request_id_ctx_var.get()
    return rid if rid is not None else default


def _format_timestamp(record: logging.LogRecord) -> str:
    return datetime.utcfromtimestamp(record.created).isoformat() + "Z"


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


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Attach a request_id to each request and log completion."""

    def __init__(self, app, header_name: str = "x-request-id"):
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request, call_next):
        incoming = request.headers.get(self.header_name)
        rid = incoming or str(uuid4())
        request.state.request_id = rid
        token = request_id_ctx_var.set(rid)

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        response.headers[self.header_name] = rid

        logger = logging.getLogger("onering")
        logger.info(
            "request.complete",
            extra={
                "request_id": rid,
                "path": request.url.path,
                "method": request.method,
                "status": getattr(response, "status_code", None),
                "latency_bucket": latency_bucket_ms(duration_ms),
            },
        )

        request_id_ctx_var.reset(token)
        return response

