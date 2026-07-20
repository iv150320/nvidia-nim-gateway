"""Tests for the circuit breaker pattern."""

import time
from unittest.mock import MagicMock

import pytest

from nim_gateway.gateway.circuit_breaker import CircuitBreaker, CircuitBreakerOpen, CircuitState


class TestCircuitBreaker:
    """Circuit breaker state machine tests."""

    def test_initial_state(self):
        cb = CircuitBreaker("test", failure_threshold=3, recovery_timeout=0.1)
        assert cb.state is CircuitState.CLOSED
        assert cb._failure_count == 0

    def test_transitions_to_open_after_threshold(self):
        cb = CircuitBreaker("test", failure_threshold=3, recovery_timeout=60)

        mock = MagicMock(side_effect=ValueError("fail"))

        for _ in range(3):
            with pytest.raises(ValueError):
                cb.call(mock)

        assert cb.state is CircuitState.OPEN

    def test_open_rejects_calls(self):
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=60)
        mock = MagicMock(side_effect=ValueError("fail"))

        with pytest.raises(ValueError):
            cb.call(mock)

        # Circuit is OPEN — next call should be rejected
        with pytest.raises(CircuitBreakerOpen):
            cb.call(MagicMock())

    def test_transitions_to_half_open_after_timeout(self):
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=0.05)

        mock_fail = MagicMock(side_effect=ValueError("fail"))
        with pytest.raises(ValueError):
            cb.call(mock_fail)

        assert cb.state is CircuitState.OPEN

        # Wait for recovery timeout
        time.sleep(0.06)

        # State should now be HALF_OPEN
        assert cb.state is CircuitState.HALF_OPEN

    def test_half_open_success_closes_circuit(self):
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=0.05)

        # Trip the breaker
        mock_fail = MagicMock(side_effect=ValueError("fail"))
        with pytest.raises(ValueError):
            cb.call(mock_fail)

        time.sleep(0.06)  # Wait for recovery

        # Success in HALF_OPEN should close the circuit
        mock_success = MagicMock(return_value="ok")
        result = cb.call(mock_success)
        assert result == "ok"
        assert cb.state is CircuitState.CLOSED
        assert cb._failure_count == 0

    def test_half_open_failure_reopens(self):
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=0.05)

        # Trip the breaker
        with pytest.raises(ValueError):
            cb.call(MagicMock(side_effect=ValueError("fail")))

        time.sleep(0.06)  # Wait for recovery

        # Failure in HALF_OPEN should reopen
        with pytest.raises(ValueError):
            cb.call(MagicMock(side_effect=ValueError("fail")))

        assert cb.state is CircuitState.OPEN

    def test_reset(self):
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=60)
        with pytest.raises(ValueError):
            cb.call(MagicMock(side_effect=ValueError("fail")))

        cb.reset()
        assert cb.state is CircuitState.CLOSED
        assert cb._failure_count == 0

    def test_half_open_success_closes_immediately(self):
        """A single successful probe in half-open state closes the circuit."""
        cb = CircuitBreaker(
            "test",
            failure_threshold=1,
            recovery_timeout=0.05,
            half_open_max_calls=3,
        )

        # Trip the breaker
        with pytest.raises(ValueError):
            cb.call(MagicMock(side_effect=ValueError("fail")))

        time.sleep(0.06)  # Wait for recovery

        # First HALF_OPEN call succeeds → circuit closes immediately
        result = cb.call(MagicMock(return_value="ok"))
        assert result == "ok"
        assert cb.state is CircuitState.CLOSED

        # Now circuit is CLOSED — calls work normally
        result = cb.call(MagicMock(return_value="ok"))
        assert result == "ok"
        assert cb.state is CircuitState.CLOSED

    def test_continuous_success_resets_count(self):
        cb = CircuitBreaker("test", failure_threshold=3, recovery_timeout=60)
        mock = MagicMock(return_value="ok")

        # Simulate one failure, then many successes
        with pytest.raises(ValueError):
            cb.call(MagicMock(side_effect=ValueError("fail")))

        assert cb._failure_count == 1

        # Success should reset the counter
        cb.call(mock)
        assert cb._failure_count == 0
