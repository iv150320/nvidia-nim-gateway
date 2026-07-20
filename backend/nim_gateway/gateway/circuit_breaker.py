"""Circuit breaker pattern for upstream NIM providers.

States: CLOSED (normal) → OPEN (failing) → HALF_OPEN (probing) → CLOSED or OPEN.
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Callable, Optional

from loguru import logger


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Per-provider circuit breaker."""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 3,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: float = 0.0
        self._half_open_calls = 0

    @property
    def state(self) -> CircuitState:
        # Check if it's time to transition OPEN → HALF_OPEN
        if self._state is CircuitState.OPEN:
            if time.monotonic() - self._last_failure_time >= self.recovery_timeout:
                logger.info("Circuit {!r} transitioning OPEN → HALF_OPEN", self.name)
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
        return self._state

    def call(self, func: Callable, *args, **kwargs):
        """Execute *func* through the circuit breaker.

        Raises CircuitBreakerOpen if circuit is OPEN.
        """
        st = self.state  # may transition OPEN → HALF_OPEN

        if st is CircuitState.OPEN:
            raise CircuitBreakerOpen(self.name)

        if st is CircuitState.HALF_OPEN and self._half_open_calls >= self.half_open_max_calls:
            raise CircuitBreakerOpen(self.name)

        try:
            result = func(*args, **kwargs)
        except Exception as exc:
            self._record_failure()
            raise

        self._record_success()
        return result

    def _record_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = time.monotonic()

        if self._failure_count >= self.failure_threshold:
            logger.warning(
                "Circuit {!r} CLOSED → OPEN (failures={})",
                self.name,
                self._failure_count,
            )
            self._state = CircuitState.OPEN

    def _record_success(self) -> None:
        if self._state is CircuitState.HALF_OPEN:
            logger.info("Circuit {!r} HALF_OPEN → CLOSED (probe succeeded)", self.name)
            self._state = CircuitState.CLOSED
            self._failure_count = 0
        elif self._state is CircuitState.CLOSED:
            # Reset failure count on success for sliding-window semantics
            self._failure_count = 0

    def reset(self) -> None:
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._half_open_calls = 0

    def __repr__(self) -> str:
        return f"CircuitBreaker({self.name}, state={self.state.value}, failures={self._failure_count})"


class CircuitBreakerOpen(Exception):
    """Raised when a call is rejected because the circuit is open."""

    def __init__(self, name: str) -> None:
        self.provider_name = name
        super().__init__(f"Circuit breaker is OPEN for provider {name!r}")
