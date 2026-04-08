"""Core models shared across the shadow-architect framework."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Severity(str, Enum):
    """Severity level for findings and recommendations."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class TestType(str, Enum):
    """Supported test types."""

    UNIT = "unit"
    INTEGRATION = "integration"
    END_TO_END = "end_to_end"
    PERFORMANCE = "performance"
    SECURITY = "security"
    ADVERSARIAL = "adversarial"
    SMOKE = "smoke"
    REGRESSION = "regression"


class Finding(BaseModel):
    """A single finding discovered during analysis or validation."""

    id: str
    title: str
    description: str
    severity: Severity
    category: str
    location: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def __str__(self) -> str:
        location_str = f" [{self.location}]" if self.location else ""
        return f"[{self.severity.value.upper()}] {self.title}{location_str}: {self.description}"


class Recommendation(BaseModel):
    """An actionable recommendation to improve test quality."""

    id: str
    title: str
    description: str
    priority: Severity
    category: str
    effort: str = "medium"  # low, medium, high
    example: str | None = None
    references: list[str] = Field(default_factory=list)

    def __str__(self) -> str:
        return f"[{self.priority.value.upper()}] {self.title}: {self.description}"


class TestSuite(BaseModel):
    """Represents a test suite under analysis."""

    name: str
    description: str = ""
    use_case: str = ""
    product: str = ""
    test_files: list[str] = Field(default_factory=list)
    test_types: list[TestType] = Field(default_factory=list)
    source_files: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
