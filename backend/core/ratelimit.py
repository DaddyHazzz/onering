"""
Token-bucket rate limiter (Phase 6.3).

- In-memory, keyed by user_id+route or ip+route.
- Defaults are safe (disabled unless enabled via env/settings).
"""

import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple, Callable


@dataclass
class RateLimitConfig:
    enabled: bool = False
    per_minute_default: int = 120
    burst_default: int = 30


class TokenBucket:
    def __init__(self, capacity: int, refill_rate_per_sec: float, time_fn: Callable[[], float] = time.monotonic):
        self.capacity = max(1, capacity)
        self.tokens = float(self.capacity)
        self.refill_rate = max(0.0, refill_rate_per_sec)
        self.time_fn = time_fn
        self.last_refill = self.time_fn()

    def _refill(self) -> None:
        now = self.time_fn()
        elapsed = now - self.last_refill
        if elapsed <= 0:
            return
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

    def allow(self, cost: float = 1.0) -> bool:
        self._refill()
        if self.tokens >= cost:
            self.tokens -= cost
            return True
        return False


class InMemoryRateLimiter:
    def __init__(self, config: RateLimitConfig, time_fn: Callable[[], float] = time.monotonic):
        self.config = config
        self.time_fn = time_fn
        self.buckets: Dict[str, TokenBucket] = {}

    def _bucket_for(self, key: str, per_minute: int, burst: int) -> TokenBucket:
        if key not in self.buckets:
            refill_rate = per_minute / 60.0
            self.buckets[key] = TokenBucket(capacity=burst, refill_rate_per_sec=refill_rate, time_fn=self.time_fn)
        return self.buckets[key]

    def allow(self, key: str, *, per_minute: int, burst: int) -> bool:
        bucket = self._bucket_for(key, per_minute, burst)
        return bucket.allow()


def build_rate_limit_config_from_env(env: dict) -> RateLimitConfig:
    def _bool(name: str, default: bool) -> bool:
        raw = env.get(name)
        if raw is None:
            return default
        return str(raw).lower() in {"1", "true", "yes", "on"}

    def _int(name: str, default: int) -> int:
        raw = env.get(name)
        if raw is None:
            return default
        try:
            value = int(raw)
            return value if value > 0 else default
        except Exception:
            return default

    return RateLimitConfig(
        enabled=_bool("RATE_LIMIT_ENABLED", False),
        per_minute_default=_int("RATE_LIMIT_PER_MINUTE_DEFAULT", 120),
        burst_default=_int("RATE_LIMIT_BURST_DEFAULT", 30),
    )
