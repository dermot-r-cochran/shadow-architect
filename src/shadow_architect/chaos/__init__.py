"""Containment testing module for shadow-architect.

Provides resilience boundary enforcement through fault injection, verifying
that the system isolates and surfaces failures rather than propagating or
silently swallowing them.  Three boundary classes are tested:

- Input boundary (corrupt inputs): null injection, type confusion, encoding
  corruption, boundary values, malformed source, JSON corruption.
- Credential and authorisation boundary (security): missing credentials, RBAC
  403/401 responses, expired tokens, wrong tenant/subscription.
- Infrastructure boundary (network): latency injection, timeouts, connection
  refused, intermittent failures.

A containment experiment passes when the system isolates the fault and
surfaces it cleanly.  It fails when the fault propagates, causes silent
data corruption, or is swallowed without visibility.

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
