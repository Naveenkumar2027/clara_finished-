"""Small, deterministic, process-local token-bucket rate limiters."""

from __future__ import annotations

import time
from dataclasses import dataclass
from threading import Lock
from typing import Callable

Clock = Callable[[], float]


@dataclass
class TokenBucket:
    capacity: float
    refill_per_second: float
    clock: Clock = time.monotonic

    def __post_init__(self) -> None:
        if self.capacity <= 0 or self.refill_per_second <= 0:
            raise ValueError("token bucket values must be positive")
        self.tokens = float(self.capacity)
        self.updated_at = self.clock()
        self.last_seen = self.updated_at

    def allow(self, cost: float = 1.0) -> bool:
        if cost <= 0:
            raise ValueError("token cost must be positive")
        now = self.clock()
        elapsed = max(0.0, now - self.updated_at)
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_per_second)
        self.updated_at = now
        self.last_seen = now
        if self.tokens < cost:
            return False
        self.tokens -= cost
        return True


class BoundedKeyedRateLimiter:
    """Thread-safe keyed buckets with stale cleanup and a hard memory bound."""

    def __init__(
        self,
        capacity: float,
        refill_per_second: float,
        *,
        stale_after_seconds: float = 600.0,
        max_entries: int = 5000,
        clock: Clock = time.monotonic,
    ) -> None:
        if stale_after_seconds <= 0 or max_entries <= 0:
            raise ValueError("cleanup values must be positive")
        self.capacity = capacity
        self.refill_per_second = refill_per_second
        self.stale_after_seconds = stale_after_seconds
        self.max_entries = max_entries
        self.clock = clock
        self._buckets: dict[str, TokenBucket] = {}
        self._lock = Lock()

    def _cleanup(self, now: float) -> None:
        stale = [
            key
            for key, bucket in self._buckets.items()
            if now - bucket.last_seen >= self.stale_after_seconds
        ]
        for key in stale:
            self._buckets.pop(key, None)

    def allow(self, key: str, cost: float = 1.0) -> bool:
        safe_key = key or "unknown"
        with self._lock:
            now = self.clock()
            self._cleanup(now)
            bucket = self._buckets.get(safe_key)
            if bucket is None:
                if len(self._buckets) >= self.max_entries:
                    oldest = min(self._buckets, key=lambda item: self._buckets[item].last_seen)
                    self._buckets.pop(oldest, None)
                bucket = TokenBucket(self.capacity, self.refill_per_second, self.clock)
                self._buckets[safe_key] = bucket
            return bucket.allow(cost)

    def entry_count(self) -> int:
        with self._lock:
            self._cleanup(self.clock())
            return len(self._buckets)

    def clear(self) -> None:
        with self._lock:
            self._buckets.clear()
