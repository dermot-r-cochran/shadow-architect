"""Test validator module.

Validates that a test suite meets a set of quality and completeness criteria,
returning structured findings for each criterion that is not satisfied.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from shadow_architect.core.analyzer import StrategyAnalysis
from shadow_architect.core.models import Finding, Recommendation, Severity, TestType


@dataclass
class ValidationResult:
    """Outcome of a validation run."""

    passed: bool
    score: float  # 0.0 – 100.0
    findings: list[Finding] = field(default_factory=list)
    recommendations: list[Recommendation] = field(default_factory=list)
    criteria_results: dict[str, bool] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def grade(self) -> str:
        """Letter grade based on score."""
        if self.score >= 90:
            return "A"
        if self.score >= 80:
            return "B"
        if self.score >= 70:
            return "C"
        if self.score >= 60:
            return "D"
        return "F"


class ValidationCriterion:
    """Base class for a single validation criterion."""

    id: str = ""
    title: str = ""
    weight: float = 1.0  # relative weight in the final score

    def evaluate(self, analysis: StrategyAnalysis) -> tuple[bool, Finding | None]:
        """Return (passed, optional_finding)."""
        raise NotImplementedError


class HasTestsCriterion(ValidationCriterion):
    id = "has-tests"
    title = "Test suite contains tests"
    weight = 5.0

    def evaluate(self, analysis: StrategyAnalysis) -> tuple[bool, Finding | None]:
        if analysis.test_count > 0:
            return True, None
        return False, Finding(
            id=self.id,
            title=self.title,
            description="The test suite contains zero test functions.",
            severity=Severity.CRITICAL,
            category="coverage",
        )


class AssertionDensityCriterion(ValidationCriterion):
    id = "assertion-density"
    title = "Adequate assertion density"
    weight = 3.0
    min_density: float = 1.0

    def evaluate(self, analysis: StrategyAnalysis) -> tuple[bool, Finding | None]:
        density = analysis.assertion_density
        if density >= self.min_density:
            return True, None
        return False, Finding(
            id=self.id,
            title=self.title,
            description=(
                f"Assertion density is {density:.2f} (minimum recommended: {self.min_density})."
            ),
            severity=Severity.MEDIUM,
            category="quality",
        )


class UnitTestPresenceCriterion(ValidationCriterion):
    id = "unit-tests-present"
    title = "Unit tests present"
    weight = 4.0

    def evaluate(self, analysis: StrategyAnalysis) -> tuple[bool, Finding | None]:
        if TestType.UNIT in analysis.test_types_found:
            return True, None
        return False, Finding(
            id=self.id,
            title=self.title,
            description="No unit tests were detected in the suite.",
            severity=Severity.HIGH,
            category="coverage",
        )


class IntegrationTestPresenceCriterion(ValidationCriterion):
    id = "integration-tests-present"
    title = "Integration tests present"
    weight = 3.0

    def evaluate(self, analysis: StrategyAnalysis) -> tuple[bool, Finding | None]:
        if TestType.INTEGRATION in analysis.test_types_found:
            return True, None
        return False, Finding(
            id=self.id,
            title=self.title,
            description="No integration tests were detected.",
            severity=Severity.MEDIUM,
            category="coverage",
        )


class AdversarialTestPresenceCriterion(ValidationCriterion):
    id = "adversarial-tests-present"
    title = "Adversarial / robustness tests present"
    weight = 4.0

    def evaluate(self, analysis: StrategyAnalysis) -> tuple[bool, Finding | None]:
        product_lower = (
            analysis.suite.product + " " + analysis.suite.use_case
        ).lower()
        is_ai = any(
            kw in product_lower for kw in ("ai", "ml", "model", "llm", "gpt")
        )
        if not is_ai:
            # Not applicable – criterion passes by default
            return True, None
        if TestType.ADVERSARIAL in analysis.test_types_found:
            return True, None
        return False, Finding(
            id=self.id,
            title=self.title,
            description=(
                "AI/ML product detected but no adversarial or robustness tests were found."
            ),
            severity=Severity.HIGH,
            category="ai_safety",
        )


class SecurityTestPresenceCriterion(ValidationCriterion):
    id = "security-tests-present"
    title = "Security tests present"
    weight = 3.0

    def evaluate(self, analysis: StrategyAnalysis) -> tuple[bool, Finding | None]:
        product_lower = (
            analysis.suite.product + " " + analysis.suite.use_case
        ).lower()
        is_security_relevant = any(
            kw in product_lower
            for kw in ("api", "endpoint", "auth", "cloud", "azure", "ai", "ml")
        )
        if not is_security_relevant:
            return True, None
        if TestType.SECURITY in analysis.test_types_found:
            return True, None
        return False, Finding(
            id=self.id,
            title=self.title,
            description=(
                "Product / use-case context suggests security testing is required, "
                "but no security tests were found."
            ),
            severity=Severity.HIGH,
            category="security",
        )


class TestIsolationCriterion(ValidationCriterion):
    id = "test-isolation"
    title = "Tests use mocks / test doubles"
    weight = 2.0

    def evaluate(self, analysis: StrategyAnalysis) -> tuple[bool, Finding | None]:
        if analysis.mock_count > 0 or analysis.test_count <= 5:
            return True, None
        return False, Finding(
            id=self.id,
            title=self.title,
            description=(
                "No mocking patterns detected. Tests may rely on real external services, "
                "making them slow and flaky."
            ),
            severity=Severity.LOW,
            category="isolation",
        )


class ParametrizedTestsCriterion(ValidationCriterion):
    id = "parametrized-tests"
    title = "Parametrized tests used"
    weight = 1.5

    def evaluate(self, analysis: StrategyAnalysis) -> tuple[bool, Finding | None]:
        if analysis.parametrized_count > 0 or analysis.test_count <= 3:
            return True, None
        return False, Finding(
            id=self.id,
            title=self.title,
            description=(
                "No parametrized tests detected. Parametrization improves coverage of "
                "boundary values and equivalence classes."
            ),
            severity=Severity.LOW,
            category="quality",
        )


# Default set of criteria applied by TestValidator
_DEFAULT_CRITERIA: list[ValidationCriterion] = [
    HasTestsCriterion(),
    AssertionDensityCriterion(),
    UnitTestPresenceCriterion(),
    IntegrationTestPresenceCriterion(),
    AdversarialTestPresenceCriterion(),
    SecurityTestPresenceCriterion(),
    TestIsolationCriterion(),
    ParametrizedTestsCriterion(),
]


class TestValidator:
    """Validates a :class:`StrategyAnalysis` against a configurable set of criteria.

    Usage::

        analyzer = TestStrategyAnalyzer()
        analysis = analyzer.analyze(suite)
        validator = TestValidator()
        result = validator.validate(analysis)
        print(result.grade, result.score)
    """

    def __init__(self, criteria: list[ValidationCriterion] | None = None) -> None:
        self._criteria = criteria if criteria is not None else _DEFAULT_CRITERIA

    def validate(self, analysis: StrategyAnalysis) -> ValidationResult:
        """Run all criteria and produce a :class:`ValidationResult`."""
        total_weight = sum(c.weight for c in self._criteria)
        earned_weight = 0.0
        findings: list[Finding] = []
        criteria_results: dict[str, bool] = {}

        for criterion in self._criteria:
            passed, finding = criterion.evaluate(analysis)
            criteria_results[criterion.id] = passed
            if passed:
                earned_weight += criterion.weight
            elif finding is not None:
                findings.append(finding)

        score = (earned_weight / total_weight * 100) if total_weight > 0 else 0.0
        passed = score >= 60.0

        recommendations = self._build_recommendations(findings)

        return ValidationResult(
            passed=passed,
            score=round(score, 1),
            findings=findings,
            recommendations=recommendations,
            criteria_results=criteria_results,
        )

    # ------------------------------------------------------------------
    def _build_recommendations(
        self, findings: list[Finding]
    ) -> list[Recommendation]:
        recs: list[Recommendation] = []
        for finding in findings:
            rec = _FINDING_TO_RECOMMENDATION.get(finding.id)
            if rec is not None:
                recs.append(rec)
        return recs


_FINDING_TO_RECOMMENDATION: dict[str, Recommendation] = {
    "has-tests": Recommendation(
        id="rec-add-tests",
        title="Add tests to the test suite",
        description=(
            "Create at least one test function (prefixed with 'test_') so that the "
            "framework can evaluate coverage and quality."
        ),
        priority=Severity.CRITICAL,
        category="coverage",
        effort="medium",
        example="def test_example():\n    assert 1 + 1 == 2",
    ),
    "assertion-density": Recommendation(
        id="rec-add-assertions",
        title="Add more assertions to tests",
        description=(
            "Each test should contain at least one 'assert' statement to verify "
            "observable behaviour."
        ),
        priority=Severity.MEDIUM,
        category="quality",
        effort="low",
        example="assert result == expected_value",
    ),
    "unit-tests-present": Recommendation(
        id="rec-add-unit-tests",
        title="Add unit tests",
        description=(
            "Create a dedicated unit test file (e.g., 'tests/test_unit_*.py') that "
            "tests individual functions and classes in isolation."
        ),
        priority=Severity.HIGH,
        category="coverage",
        effort="medium",
    ),
    "integration-tests-present": Recommendation(
        id="rec-add-integration-tests",
        title="Add integration tests",
        description=(
            "Create integration tests that validate the interaction between components "
            "and external services such as Azure APIs."
        ),
        priority=Severity.MEDIUM,
        category="coverage",
        effort="high",
    ),
    "adversarial-tests-present": Recommendation(
        id="rec-add-adversarial-tests",
        title="Add adversarial / robustness tests for the AI capability",
        description=(
            "For AI/ML products, create tests that inject adversarial inputs "
            "(e.g., prompt injections, out-of-distribution data) to verify "
            "robustness and safety."
        ),
        priority=Severity.HIGH,
        category="ai_safety",
        effort="high",
        references=[
            "https://owasp.org/www-project-top-10-for-large-language-model-applications/",
            "https://learn.microsoft.com/en-us/azure/ai-services/responsible-use-of-ai-overview",
        ],
    ),
    "security-tests-present": Recommendation(
        id="rec-add-security-tests",
        title="Add security tests",
        description=(
            "Introduce tests that check authentication, authorisation, input validation, "
            "and secrets handling."
        ),
        priority=Severity.HIGH,
        category="security",
        effort="high",
    ),
    "test-isolation": Recommendation(
        id="rec-add-mocks",
        title="Use mocks and test doubles",
        description=(
            "Replace direct calls to external services with mocks (e.g., using "
            "unittest.mock or pytest-mock) to make tests fast and deterministic."
        ),
        priority=Severity.LOW,
        category="isolation",
        effort="medium",
        example=(
            "from unittest.mock import patch\n\n"
            "@patch('my_module.azure_client')\n"
            "def test_my_function(mock_client):\n"
            "    mock_client.return_value = 'mocked'\n"
            "    assert my_function() == 'mocked'"
        ),
    ),
    "parametrized-tests": Recommendation(
        id="rec-add-parametrize",
        title="Use pytest.mark.parametrize for data-driven tests",
        description=(
            "Parametrize tests to cover multiple inputs / edge cases without "
            "code duplication."
        ),
        priority=Severity.LOW,
        category="quality",
        effort="low",
        example=(
            "import pytest\n\n"
            "@pytest.mark.parametrize('value,expected', [(1, 2), (2, 4)])\n"
            "def test_double(value, expected):\n"
            "    assert value * 2 == expected"
        ),
    ),
}
