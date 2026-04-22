"""
shadow-architect: Enforces system boundaries, decision gates, and constraints
for AI-enabled systems.
"""

from shadow_architect.core.analyzer import TestStrategyAnalyzer
from shadow_architect.core.improver import TestImprover
from shadow_architect.core.reporter import TestReport, TestReporter
from shadow_architect.core.validator import TestValidator

__all__ = [
    "TestStrategyAnalyzer",
    "TestValidator",
    "TestImprover",
    "TestReporter",
    "TestReport",
]

__version__ = "0.1.0"
