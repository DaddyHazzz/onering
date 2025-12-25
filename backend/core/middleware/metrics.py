import time
from starlette.middleware.base import BaseHTTPMiddleware

from backend.core.metrics import http_requests_total, normalize_path


class MetricsMiddleware(BaseHTTPMiddleware):
    """Record HTTP request metrics (Prometheus-style)."""

    async def dispatch(self, request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        _record_request_metric(request, response, duration_ms)
        return response


def _record_request_metric(request, response, duration_ms: float) -> None:
    try:
        method = request.method.upper()
        path = normalize_path(request.url.path)
        status = getattr(response, "status_code", None) or 0
        http_requests_total.inc(labels={
            "method": method,
            "path": path,
            "status": str(status),
        })
    except Exception:
        # Do not fail the request on metrics errors
        return
