"""Input corruption scenarios for chaos engineering."""

from __future__ import annotations

import json
import random
import string
from collections.abc import Callable
from typing import Any

from shadow_architect.chaos.base import ChaosExperiment
from shadow_architect.chaos.models import ChaosStatus


class InputCorruptor:
    """Provides methods to corrupt various types of inputs.

    Each method returns a *corrupted* version (or list of corrupted versions)
    of a given value.  The methods are stateless and safe to call in any order.
    """

    # ------------------------------------------------------------------
    # Null / empty injection
    # ------------------------------------------------------------------

    def null_variants(self, value: Any) -> list[Any]:  # noqa: ARG002
        """Return null/empty replacements for *value*."""
        return [None, "", [], {}, 0, False]

    # ------------------------------------------------------------------
    # Type confusion
    # ------------------------------------------------------------------

    def type_confusion(self, value: Any) -> list[Any]:
        """Return wrongly-typed variants of *value*."""
        alternatives: list[Any] = []
        if not isinstance(value, str):
            alternatives.append(str(value))
        if not isinstance(value, int):
            alternatives.append(42)
        if not isinstance(value, list):
            alternatives.append([value])
        if not isinstance(value, dict):
            alternatives.append({"__chaos__": value})
        if not isinstance(value, float):
            alternatives.append(3.14)
        if not isinstance(value, bool):
            alternatives.append(True)
        return alternatives

    # ------------------------------------------------------------------
    # Encoding corruption
    # ------------------------------------------------------------------

    def encoding_corruption(self, value: str) -> list[Any]:
        """Return variants with invalid/mixed encodings."""
        return [
            # Raw bytes that are not valid UTF-8
            b"\xff\xfe" + value.encode("utf-8", errors="replace"),
            # Latin-1 decoded as UTF-8
            value.encode("latin-1", errors="replace"),
            # Null bytes embedded
            value + "\x00\x01\x02",
            # Mixed: valid UTF-8 prefix + garbage
            value[:5] + "\udcff\udcfe",
        ]

    # ------------------------------------------------------------------
    # Boundary values
    # ------------------------------------------------------------------

    def boundary_values(self, value: Any) -> list[Any]:
        """Return extreme / boundary versions of *value*."""
        variants: list[Any] = [
            # Very large string
            "A" * 100_000,
            # Negative numbers
            -1,
            -2**31,
            # Zero
            0,
            # Empty containers
            [],
            {},
            # Max int
            2**63 - 1,
            # Single character
            "x",
        ]
        if isinstance(value, str):
            variants.append(value * 10_000)
        if isinstance(value, (int, float)):
            variants.extend([float("inf"), float("-inf"), float("nan")])
        return variants

    # ------------------------------------------------------------------
    # Malformed Python source
    # ------------------------------------------------------------------

    def malformed_python_source(self, source: str) -> list[str]:
        """Return syntactically broken variants of a Python source string."""
        truncated = source[: max(1, len(source) // 2)]
        return [
            # Missing colon after def
            "def broken_function\n    pass\n",
            # Unmatched parenthesis
            "def test_oops(:\n    pass\n",
            # Truncated at midpoint
            truncated,
            # Binary garbage prepended
            "\x00\x01\x02\x03" + source,
            # Only whitespace
            "   \n\t\n   ",
        ]

    # ------------------------------------------------------------------
    # JSON corruption
    # ------------------------------------------------------------------

    def corrupt_json(self, data: dict[str, Any]) -> list[Any]:
        """Return malformed JSON strings or broken dict structures."""
        valid_json = json.dumps(data)
        variants: list[Any] = [
            # Truncated JSON string
            valid_json[: max(1, len(valid_json) // 2)],
            # Extra trailing garbage
            valid_json + "}}}}",
            # Missing closing brace
            valid_json[:-1],
            # Wrong types for every key
            {k: None for k in data},
            # Deeply nested corruption
            {"__chaos_nested__": {"__inner__": None}},
            # Empty JSON object
            "{}",
            # Not JSON at all
            "not-json",
            # List instead of object
            "[1, 2, 3]",
        ]
        return variants


class CorruptInputExperiment(ChaosExperiment):
    """Apply a battery of input corruption strategies to a callable.

    The experiment passes each corrupted input to *target* and considers the
    system to handle the fault gracefully if it does **not** raise an
    unhandled exception (or raises an explicitly allowed exception type).

    Args:
        target: The callable to test.
        sample_input: A representative valid input to use as the basis for
            corruption.  Must be a positional argument to *target*.
        allowed_exceptions: Exception types that are considered graceful
            failure responses (e.g., ``ValueError``, ``TypeError``).
        name: Override the experiment name.
    """

    name = "corrupt-inputs"
    description = (
        "Applies null injection, type confusion, encoding corruption, boundary "
        "values, malformed source, and JSON corruption to a target callable."
    )

    def __init__(
        self,
        target: Callable[..., Any],
        sample_input: Any = "",
        allowed_exceptions: tuple[type[Exception], ...] = (
            ValueError,
            TypeError,
            KeyError,
            AttributeError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ),
        name: str | None = None,
    ) -> None:
        super().__init__()
        self._target = target
        self._sample_input = sample_input
        self._allowed = allowed_exceptions
        if name is not None:
            self.name = name

    def setup(self) -> None:
        self._corruptor = InputCorruptor()

    def execute(self) -> None:
        """Feed each corruption variant to the target and record outcomes."""
        variants: list[Any] = []
        variants.extend(self._corruptor.null_variants(self._sample_input))
        variants.extend(self._corruptor.type_confusion(self._sample_input))
        variants.extend(self._corruptor.boundary_values(self._sample_input))

        if isinstance(self._sample_input, str):
            variants.extend(self._corruptor.encoding_corruption(self._sample_input))
            variants.extend(
                self._corruptor.malformed_python_source(self._sample_input)
            )

        if isinstance(self._sample_input, dict):
            variants.extend(self._corruptor.corrupt_json(self._sample_input))

        unhandled: list[str] = []
        for variant in variants:
            try:
                self._target(variant)
                self._observe(
                    f"Input {type(variant).__name__!r} accepted without error"
                )
            except self._allowed as exc:
                self._observe(
                    f"Graceful failure for {type(variant).__name__!r}: "
                    f"{type(exc).__name__}"
                )
            except Exception as exc:  # noqa: BLE001
                unhandled.append(
                    f"Unhandled {type(exc).__name__} for input "
                    f"{type(variant).__name__!r}: {exc}"
                )

        if unhandled:
            raise AssertionError(
                f"{len(unhandled)} unhandled exception(s):\n"
                + "\n".join(f"  • {e}" for e in unhandled)
            )

    def teardown(self) -> None:
        pass

    @property
    def status(self) -> ChaosStatus:
        """Convenience property – not set until :meth:`run` completes."""
        return ChaosStatus.PASSED

    # Expose corruptor for direct use after setup()
    @property
    def corruptor(self) -> InputCorruptor:
        if not hasattr(self, "_corruptor"):
            self._corruptor = InputCorruptor()
        return self._corruptor


# Alias for convenience
_sentinel: object = object()


def corrupt_call(
    target: Callable[..., Any],
    sample_input: Any = _sentinel,
    *,
    random_seed: int | None = None,
) -> list[str]:
    """Quick helper: run all corruption strategies against *target*.

    Returns a list of observation strings.  Raises nothing – all exceptions
    from *target* are captured as observations.
    """
    if random_seed is not None:
        random.seed(random_seed)
    if sample_input is _sentinel:
        sample_input = "".join(random.choices(string.ascii_letters, k=10))

    exp = CorruptInputExperiment(target=target, sample_input=sample_input)
    result = exp.run()
    return result.observations
