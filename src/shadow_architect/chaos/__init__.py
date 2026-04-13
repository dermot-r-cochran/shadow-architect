"""Chaos engineering module for shadow-architect.

Provides fault-injection primitives for resilience testing, covering:

- Corrupt inputs (null injection, type confusion, encoding corruption, …)
- Security permission misalignment (missing credentials, RBAC, expired tokens, …)
- Network latency and disruption (latency injection, timeouts, intermittent failures, …)

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
