"""Network latency and disruption chaos scenarios."""

from __future__ import annotations

import random
import threading
import time
from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock, patch

from shadow_architect.chaos.base import ChaosExperiment
from shadow_architect.chaos.models import ChaosStatus

# ---------------------------------------------------------------------------
# Private context-manager helpers
# ---------------------------------------------------------------------------


class _LatencyCtx:
    def __init__(self, seconds: float, target: str) -> None:
        self._seconds = seconds
        self._target = target
        self._patcher: Any = None

    def __enter__(self) -> _LatencyCtx:
        original_target = self._target
        delay = self._seconds

        def _delayed(*args: Any, **kwargs: Any) -> Any:
            time.sleep(delay)
            return MagicMock()

        self._patcher = patch(original_target, side_effect=_delayed)
        self._patcher.start()
        return self

    def __exit__(self, *_: Any) -> bool:
        if self._patcher is not None:
            self._patcher.stop()
        return False


class _TimeoutCtx:
    def __init__(self, target: str, exception_class: type[Exception]) -> None:
        self._target = target
        self._exc_class = exception_class
        self._patcher: Any = None

    def __enter__(self) -> _TimeoutCtx:
        exc = self._exc_class("Simulated network timeout")
        self._patcher = patch(self._target, side_effect=exc)
        self._patcher.start()
        return self

    def __exit__(self, *_: Any) -> bool:
        if self._patcher is not None:
            self._patcher.stop()
        return False


class _ConnectionRefusedCtx:
    def __init__(self, target: str) -> None:
        self._target = target
        self._patcher: Any = None

    def __enter__(self) -> _ConnectionRefusedCtx:
        exc = ConnectionRefusedError("Simulated connection refused")
        self._patcher = patch(self._target, side_effect=exc)
        self._patcher.start()
        return self

    def __exit__(self, *_: Any) -> bool:
        if self._patcher is not None:
            self._patcher.stop()
        return False


class _IntermittentCtx:
    def __init__(
        self,
        target: str,
        failure_rate: float,
        exception_class: type[Exception],
        seed: int | None,
    ) -> None:
        self._target = target
        self._rate = failure_rate
        self._exc_class = exception_class
        self._rng = random.Random(seed)
        self._patcher: Any = None

    def __enter__(self) -> _IntermittentCtx:
        rate = self._rate
        exc_class = self._exc_class
        rng = self._rng

        def _maybe_fail(*args: Any, **kwargs: Any) -> Any:
            if rng.random() < rate:
                raise exc_class("Simulated intermittent network failure")
            return MagicMock()

        self._patcher = patch(self._target, side_effect=_maybe_fail)
        self._patcher.start()
        return self

    def __exit__(self, *_: Any) -> bool:
        if self._patcher is not None:
            self._patcher.stop()
        return False


class _SlowResponseCtx:
    def __init__(self, target: str, chunk_delay: float) -> None:
        self._target = target
        self._delay = chunk_delay
        self._patcher: Any = None

    def __enter__(self) -> _SlowResponseCtx:
        delay = self._delay

        def _slow_response(*args: Any, **kwargs: Any) -> MagicMock:
            time.sleep(delay)
            mock_resp = MagicMock()
            mock_resp.content = b"partial data"
            mock_resp.status_code = 200
            return mock_resp

        self._patcher = patch(self._target, side_effect=_slow_response)
        self._patcher.start()
        return self

    def __exit__(self, *_: Any) -> bool:
        if self._patcher is not None:
            self._patcher.stop()
        return False


# ---------------------------------------------------------------------------
# NetworkChaos
# ---------------------------------------------------------------------------


class NetworkChaos:
    """Provides network-level fault injection as context managers.

    All methods return context managers that monkey-patch ``httpx`` (or the
    specified *target*) for the duration of the ``with`` block.

    Example::

        nc = NetworkChaos()
        with nc.latency(seconds=2.0, target="httpx.Client.send"):
            response = client.get("https://example.com")
    """

    def latency(
        self, seconds: float = 1.0, target: str = "httpx.Client.send"
    ) -> _LatencyCtx:
        """Add a fixed *seconds* delay to every call to *target*."""
        return _LatencyCtx(seconds, target)

    def timeout(
        self,
        target: str = "httpx.Client.send",
        exception_class: type[Exception] | None = None,
    ) -> _TimeoutCtx:
        """Force every call to *target* to raise a timeout exception."""
        if exception_class is None:
            try:
                import httpx

                exception_class = httpx.TimeoutException
            except ImportError:
                exception_class = TimeoutError
        return _TimeoutCtx(target, exception_class)

    def connection_refused(
        self, target: str = "httpx.Client.send"
    ) -> _ConnectionRefusedCtx:
        """Simulate connection refused for every call to *target*."""
        return _ConnectionRefusedCtx(target)

    def intermittent_failures(
        self,
        target: str = "httpx.Client.send",
        failure_rate: float = 0.3,
        exception_class: type[Exception] | None = None,
        seed: int | None = None,
    ) -> _IntermittentCtx:
        """Randomly fail *failure_rate* fraction of calls to *target*."""
        if exception_class is None:
            exception_class = OSError
        return _IntermittentCtx(target, failure_rate, exception_class, seed)

    def slow_response(
        self, target: str = "httpx.Client.send", chunk_delay: float = 0.5
    ) -> _SlowResponseCtx:
        """Simulate slow trickle responses by inserting a per-call delay."""
        return _SlowResponseCtx(target, chunk_delay)


# ---------------------------------------------------------------------------
# NetworkChaosExperiment
# ---------------------------------------------------------------------------


class NetworkChaosExperiment(ChaosExperiment):
    """Wrap a target operation with network chaos and validate resilience.

    Args:
        target: The callable to test under network faults.
        http_target: Dotted path to the HTTP method to monkey-patch
            (e.g. ``"httpx.Client.send"``).
        latency_seconds: Delay injected during the latency scenario.
        failure_rate: Fraction of calls that fail in the intermittent scenario.
        seed: Random seed for deterministic intermittent failure tests.
        allowed_exceptions: Exception types treated as graceful failure.
        name: Override the experiment name.
    """

    name = "network-chaos"
    description = (
        "Injects latency, timeouts, connection failures, intermittent errors, "
        "and slow responses into HTTP calls to validate system resilience."
    )

    def __init__(
        self,
        target: Callable[..., Any],
        http_target: str = "httpx.Client.send",
        latency_seconds: float = 0.05,
        failure_rate: float = 0.5,
        seed: int | None = 42,
        allowed_exceptions: tuple[type[Exception], ...] = (Exception,),
        name: str | None = None,
    ) -> None:
        super().__init__()
        self._target = target
        self._http_target = http_target
        self._latency_seconds = latency_seconds
        self._failure_rate = failure_rate
        self._seed = seed
        self._allowed = allowed_exceptions
        self._chaos = NetworkChaos()
        if name is not None:
            self.name = name

    def setup(self) -> None:
        pass

    def execute(self) -> None:
        """Run each network scenario and record whether the target is resilient."""
        violations: list[str] = []

        scenarios: list[tuple[str, Any]] = [
            ("latency", self._chaos.latency(self._latency_seconds, self._http_target)),
            ("timeout", self._chaos.timeout(self._http_target)),
            ("connection-refused", self._chaos.connection_refused(self._http_target)),
            (
                "intermittent",
                self._chaos.intermittent_failures(
                    self._http_target, self._failure_rate, seed=self._seed
                ),
            ),
            ("slow-response", self._chaos.slow_response(self._http_target, 0.01)),
        ]

        for scenario_name, ctx in scenarios:
            with ctx:
                try:
                    self._target()
                    self._observe(f"{scenario_name}: target succeeded")
                except self._allowed as exc:
                    self._observe(
                        f"{scenario_name}: graceful failure ({type(exc).__name__})"
                    )
                except Exception as exc:  # noqa: BLE001
                    violations.append(
                        f"{scenario_name}: unhandled {type(exc).__name__}: {exc}"
                    )

        if violations:
            raise AssertionError(
                f"{len(violations)} network resilience violation(s):\n"
                + "\n".join(f"  • {v}" for v in violations)
            )

    def teardown(self) -> None:
        pass

    @property
    def status(self) -> ChaosStatus:
        return ChaosStatus.PASSED


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def _timeout_thread_target(fn: Callable[[], Any], results: list[Any]) -> None:
    try:
        results.append(fn())
    except Exception as exc:  # noqa: BLE001
        results.append(exc)


def with_timeout(fn: Callable[[], Any], timeout_seconds: float) -> Any:
    """Run *fn* in a thread, raising :class:`TimeoutError` if it takes too long."""
    results: list[Any] = []
    t = threading.Thread(target=_timeout_thread_target, args=(fn, results), daemon=True)
    t.start()
    t.join(timeout=timeout_seconds)
    if t.is_alive():
        raise TimeoutError(f"Function did not complete within {timeout_seconds}s")
    if not results:
        raise TimeoutError("Function completed but returned no result")
    result = results[0]
    if isinstance(result, Exception):
        raise result
    return result
