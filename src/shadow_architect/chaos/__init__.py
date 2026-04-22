"""Containment testing module for shadow-architect.

Provides fault-injection primitives that enforce containment boundaries under
adverse conditions.  Each experiment targets a specific boundary — it is not
general resilience exploration.

- Corrupt inputs: the system must not fail uncontrollably under malformed,
  null, or adversarial input.
- Security permission misalignment: the system must not silently succeed when
  credentials are missing, expired, or insufficient.
- Network disruption: the system must surface failures from latency, timeout,
  and connection loss — not swallow them.

An experiment that returns ``FAILED`` status means a containment boundary was
crossed, not that a metric fell below a threshold.

Quick start::

    from shadow_architect.chaos import (
        ChaosRunner,
        CorruptInputExperiment,
        NetworkChaosExperiment,
        SecurityChaosExperiment,
    )

    runner = ChaosRunner([
        CorruptInputExperiment(target=my_function, sample_input="hello"),
        NetworkChaosExperiment(target=my_api_call),
    ])
    report = runner.run()
    runner.print_report(report)
"""

from __future__ import annotations

from shadow_architect.chaos.base import ChaosExperiment
from shadow_architect.chaos.corrupt_inputs import CorruptInputExperiment, InputCorruptor
from shadow_architect.chaos.models import ChaosReport, ChaosResult, ChaosStatus
from shadow_architect.chaos.network import NetworkChaos, NetworkChaosExperiment
from shadow_architect.chaos.runner import ChaosRunner
from shadow_architect.chaos.security import PermissionChaos, SecurityChaosExperiment

__all__ = [
    "ChaosExperiment",
    "ChaosReport",
    "ChaosResult",
    "ChaosRunner",
    "ChaosStatus",
    "CorruptInputExperiment",
    "InputCorruptor",
    "NetworkChaos",
    "NetworkChaosExperiment",
    "PermissionChaos",
    "SecurityChaosExperiment",
]
