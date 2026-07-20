"""In-memory sliding-window rate limiter.

For production deployments Redis-backed token-bucket is recommended.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Optional

from fastapi import HTTPException, Request, status


class SlidingWindowRateLimiter:
    """Per-client sliding-window rate limiter (in-memory)."""

    def __init__(self) -> None:
        # client_key -> deque of (timestamp,)
        self._buckets: dict[str, deque] = defaultdict(deque)

    def check(
        self,
        key: str,
        limit: int,
        window_seconds: int = 60,
        raise_on_exceed: bool = True,
    ) -> bool:
        """Return True if request is allowed.

        When *raise_on_exceed* is True (default), raises 429.
        """
        now = time.monotonic()
        window_start = now - window_seconds
        bucket = self._buckets[key]

        # Evict expired entries
        while bucket and bucket[0] < window_start:
            bucket.popleft()

        if len(bucket) >= limit:
            if raise_on_exceed:
                retry_after = int(bucket[0] + window_seconds - now) + 1
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Retry after {retry_after}s.",
                    headers={"Retry-After": str(retry_after)},
                )
            return False

        bucket.append(now)
        return True

    def remaining(self, key: str, limit: int, window_seconds: int = 60) -> int:
        """Return how many requests remain in the current window."""
        now = time.monotonic()
        window_start = now - window_seconds
        bucket = self._buckets[key]
        while bucket and bucket[0] < window_start:
            bucket.popleft()
        return max(0, limit - len(bucket))

    def reset(self, key: str) -> None:
        """Clear all rate-limit state for a client."""
        self._buckets.pop(key, None)


# Singleton
rate_limiter = SlidingWindowRateLimiter()
