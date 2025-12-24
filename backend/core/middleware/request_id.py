import logging
import time
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware

from backend.core.logging import request_id_ctx_var, latency_bucket_ms, get_request_id


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
