import os
import time
from dataclasses import dataclass
from typing import Optional, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from backend.core.errors import RateLimitError, app_error_handler
from backend.core.metrics import ratelimit_block_total, normalize_path
from backend.core.logging import get_request_id
from backend.core.ratelimit import InMemoryRateLimiter, RateLimitConfig, build_rate_limit_config_from_env


@dataclass
class RoutePolicy:
    per_minute: int
    burst: int


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Token-bucket rate limiting middleware (opt-in via env)."""

    def __init__(self, app, *, config: Optional[RateLimitConfig] = None, env: Optional[dict] = None, time_fn: Optional[Callable[[], float]] = None):
        super().__init__(app)
        self.config = config or build_rate_limit_config_from_env(env or os.environ)
        self.limiter = InMemoryRateLimiter(self.config, time_fn=time_fn or time.monotonic)
        if hasattr(app, "state"):
            setattr(app.state, "rate_limiter", self.limiter)

    def _policy_for_request(self, request: Request) -> Optional[RoutePolicy]:
        path = request.url.path
        method = request.method.upper()

        # Stricter for collab mutations
        if path.startswith("/v1/collab") and method in {"POST", "PUT", "PATCH", "DELETE"}:
            per_minute = max(1, int(self.config.per_minute_default * 0.5))
            burst = max(1, int(self.config.burst_default * 0.5))
            return RoutePolicy(per_minute=per_minute, burst=burst)

        # Default read policy
        return RoutePolicy(per_minute=self.config.per_minute_default, burst=self.config.burst_default)

    def _client_key(self, request: Request, category: str) -> str:
        user_id = request.headers.get("X-User-Id")
        if not user_id:
            auth = request.headers.get("Authorization")
            if auth:
                # Use a stable hash of the auth header prefix without logging it
                user_id = auth[:16]
        if user_id:
            return f"user:{user_id}:{category}"

        ip = request.headers.get("x-forwarded-for") or (request.client.host if request.client else "unknown")
        return f"ip:{ip}:{category}"

    async def dispatch(self, request: Request, call_next):
        if not self.config.enabled:
            return await call_next(request)

        policy = self._policy_for_request(request)
        if not policy:
            return await call_next(request)

        category = "mutation" if request.method.upper() in {"POST", "PUT", "PATCH", "DELETE"} else "read"
        key = self._client_key(request, category)

        allowed = self.limiter.allow(key, per_minute=policy.per_minute, burst=policy.burst)
        if allowed:
            return await call_next(request)

        rid = getattr(request.state, "request_id", None) or get_request_id()
        ratelimit_block_total.inc(labels={"scope": normalize_path(request.url.path)})

        response = await app_error_handler(
            request,
            RateLimitError("Rate limit exceeded for this endpoint", request_id=rid),
        )
        retry_after = max(1, int(60 / max(1, policy.per_minute)))
        response.headers["Retry-After"] = str(retry_after)
        response.headers["X-RateLimit-Limit"] = str(policy.per_minute)
        response.headers["X-RateLimit-Remaining"] = "0"
        response.headers["X-RateLimit-Reset"] = "60"
        return response
