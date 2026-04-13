"""Pydantic models for chaos experiment results."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ChaosStatus(str, Enum):
    """Status of a chaos experiment run."""

    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"


class ChaosResult(BaseModel):
    """Outcome of a single chaos experiment."""

    name: str
    description: str
    status: ChaosStatus
    duration_seconds: float = 0.0
    error_details: str | None = None
    observations: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ChaosReport(BaseModel):
    """Aggregated report from a chaos experiment run."""

    experiments_run: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0
    total_duration_seconds: float = 0.0
    results: list[ChaosResult] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def pass_rate(self) -> float:
        """Fraction of experiments that passed (0.0–1.0)."""
        if self.experiments_run == 0:
            return 0.0
        return self.passed / self.experiments_run

    def summary(self) -> dict[str, Any]:
        """Return a plain-dict summary suitable for JSON serialisation."""
        return {
            "experiments_run": self.experiments_run,
            "passed": self.passed,
            "failed": self.failed,
            "errors": self.errors,
            "skipped": self.skipped,
            "pass_rate": round(self.pass_rate, 4),
            "total_duration_seconds": round(self.total_duration_seconds, 4),
            "generated_at": self.generated_at.isoformat(),
        }
