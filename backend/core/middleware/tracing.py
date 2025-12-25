from starlette.middleware.base import BaseHTTPMiddleware

from backend.core.tracing import start_span
from backend.core.logging import get_request_id


class TracingMiddleware(BaseHTTPMiddleware):
    """Create an HTTP span if tracing is enabled."""

    async def dispatch(self, request, call_next):
        request_id = getattr(request.state, "request_id", None) or get_request_id()
        with start_span(
            "http.request",
            {
                "http.method": request.method,
                "http.target": request.url.path,
                "request_id": request_id,
            },
        ):
            response = await call_next(request)
            return response
