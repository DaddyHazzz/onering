"""Simple in-memory rate limiting middleware (Phase 3.8)."""

import os
import time
from typing import Callable, Dict, Optional, Tuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from backend.core.errors import RateLimitError, app_error_handler
from backend.core.logging import get_request_id


PREFIX_MAP = {
    "health": ["/api/health"],
    "analytics": ["/api/analytics", "/v1/analytics"],
}


def _parse_limit(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    try:
        limit = int(value)
        return limit if limit > 0 else None
    except (TypeError, ValueError):
        return None


class FixedWindowLimiter:
    def __init__(self, limit_per_minute: int, time_fn: Callable[[], float]):
        self.limit = limit_per_minute
        self.time_fn = time_fn
        self.windows: Dict[str, Tuple[float, int]] = {}

    def allow(self, key: str) -> bool:
        now = self.time_fn()
        window_start, count = self.windows.get(key, (now, 0))
        if now - window_start >= 60:
            window_start, count = now, 0
        if count >= self.limit:
            self.windows[key] = (window_start, count)
            return False
        self.windows[key] = (window_start, count + 1)
        return True


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limits: Dict[str, Optional[int]], time_fn: Optional[Callable[[], float]] = None):
        super().__init__(app)
        self.time_fn = time_fn or time.monotonic
        self.limiters: Dict[str, FixedWindowLimiter] = {}
        for name, limit in limits.items():
            if limit:
                self.limiters[name] = FixedWindowLimiter(limit, self.time_fn)
        # Expose for tests
        self.state_name = "rate_limiters"

    def _category_for_path(self, path: str) -> Optional[str]:
        for category, prefixes in PREFIX_MAP.items():
            if any(path.startswith(prefix) for prefix in prefixes):
                return category
        return None

    def _client_key(self, request: Request, category: str) -> str:
        ip = request.headers.get("x-forwarded-for") or (request.client.host if request.client else "unknown")
        return f"{category}:{ip}:{request.url.path}"

    async def dispatch(self, request: Request, call_next):
        category = self._category_for_path(request.url.path)
        limiter = self.limiters.get(category)

        # Fail-open when limit not configured or category not matched
        if not limiter:
            return await call_next(request)

        key = self._client_key(request, category)
        if not limiter.allow(key):
            rid = getattr(request.state, "request_id", None) or get_request_id()
            return await app_error_handler(
                request,
                RateLimitError("Rate limit exceeded for this endpoint", request_id=rid),
            )

        # Store on app state for test visibility
        if hasattr(request.app, "state"):
            setattr(request.app.state, self.state_name, self.limiters)

        return await call_next(request)


def build_rate_limit_config() -> Dict[str, Optional[int]]:
    return {
        "health": _parse_limit(os.getenv("HEALTH_RATE_LIMIT", "60")),
        "analytics": _parse_limit(os.getenv("ANALYTICS_RATE_LIMIT", "120")),
    }
