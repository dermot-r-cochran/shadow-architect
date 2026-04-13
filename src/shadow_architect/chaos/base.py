"""Abstract base class for chaos experiments."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from types import TracebackType
from typing import Any

from shadow_architect.chaos.models import ChaosResult, ChaosStatus


class ChaosExperiment(ABC):
    """Abstract base for all chaos experiments.

    Sub-classes implement :meth:`setup`, :meth:`execute`, and
    :meth:`teardown`.  The :meth:`run` method orchestrates the lifecycle with
    proper error handling and timing, returning a :class:`ChaosResult`.

    Example::

        class MyExperiment(ChaosExperiment):
            name = "my-experiment"
            description = "Inject a custom fault"

            def setup(self) -> None: ...
            def execute(self) -> None: ...
            def teardown(self) -> None: ...

        with MyExperiment() as exp:
            result = exp.run()
    """

    name: str = "unnamed-experiment"
    description: str = ""

    def __init__(self) -> None:
        self._observations: list[str] = []
        self._metadata: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Abstract lifecycle hooks
    # ------------------------------------------------------------------

    @abstractmethod
    def setup(self) -> None:
        """Prepare the experiment (e.g. patch modules, set env vars)."""

    @abstractmethod
    def execute(self) -> None:
        """Run the fault injection logic.

        Raise :class:`AssertionError` or any exception to indicate that the
        system under test did *not* handle the fault gracefully.
        """

    @abstractmethod
    def teardown(self) -> None:
        """Restore normal state (always called, even if execute fails)."""

    # ------------------------------------------------------------------
    # Orchestration
    # ------------------------------------------------------------------

    def run(self) -> ChaosResult:
        """Run the full experiment lifecycle and return a :class:`ChaosResult`."""
        start = time.monotonic()
        status = ChaosStatus.PASSED
        error_details: str | None = None

        try:
            self.setup()
        except Exception as exc:  # noqa: BLE001
            duration = time.monotonic() - start
            return ChaosResult(
                name=self.name,
                description=self.description,
                status=ChaosStatus.ERROR,
                duration_seconds=duration,
                error_details=f"setup() raised {type(exc).__name__}: {exc}",
                observations=list(self._observations),
                metadata=dict(self._metadata),
            )

        try:
            self.execute()
        except AssertionError as exc:
            status = ChaosStatus.FAILED
            error_details = str(exc)
        except Exception as exc:  # noqa: BLE001
            status = ChaosStatus.ERROR
            error_details = f"{type(exc).__name__}: {exc}"
        finally:
            try:
                self.teardown()
            except Exception as exc:  # noqa: BLE001
                # Teardown errors are captured but don't override the primary status
                self._observations.append(
                    f"teardown() raised {type(exc).__name__}: {exc}"
                )

        duration = time.monotonic() - start
        return ChaosResult(
            name=self.name,
            description=self.description,
            status=status,
            duration_seconds=duration,
            error_details=error_details,
            observations=list(self._observations),
            metadata=dict(self._metadata),
        )

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------

    def __enter__(self) -> ChaosExperiment:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool:
        # Ensure teardown is always called when used as a context manager.
        # We do NOT suppress the outer exception.
        try:
            self.teardown()
        except Exception:  # noqa: BLE001
            pass
        return False

    # ------------------------------------------------------------------
    # Helpers for sub-classes
    # ------------------------------------------------------------------

    def _observe(self, message: str) -> None:
        """Record an observation to include in the result."""
        self._observations.append(message)
