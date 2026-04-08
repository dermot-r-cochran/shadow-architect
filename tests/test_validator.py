"""Tests for shadow_architect.core.validator."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from shadow_architect.core.analyzer import TestStrategyAnalyzer
from shadow_architect.core.models import Severity, TestSuite, TestType
from shadow_architect.core.validator import (
    TestValidator,
    ValidationResult,
    _DEFAULT_CRITERIA,
)


@pytest.fixture()
def well_tested_suite(tmp_path: Path) -> TestSuite:
    """A suite with unit and integration tests, mocks, and fixtures."""
    unit = tmp_path / "test_unit_service.py"
    unit.write_text(
        textwrap.dedent(
            """\
            from unittest.mock import MagicMock
            import pytest

            @pytest.fixture()
            def svc():
                return MagicMock()

            @pytest.mark.parametrize("val", [1, 2, 3])
            def test_unit_process(val, svc):
                svc.process.return_value = val * 2
                assert svc.process(val) == val * 2
            """
        )
    )
    integration = tmp_path / "test_integration_api.py"
    integration.write_text(
        textwrap.dedent(
            """\
            def test_integration_health_check():
                assert True
            """
        )
    )
    return TestSuite(
        name="Well Tested",
        product="Generic Service",
        use_case="API",
        test_files=[str(unit), str(integration)],
    )


@pytest.fixture()
def empty_suite() -> TestSuite:
    return TestSuite(name="Empty Suite")


@pytest.fixture()
def analyzer() -> TestStrategyAnalyzer:
    return TestStrategyAnalyzer()


@pytest.fixture()
def validator() -> TestValidator:
    return TestValidator()


class TestValidationResult:
    def test_grade_a_for_high_score(self):
        result = ValidationResult(passed=True, score=95.0)
        assert result.grade == "A"

    def test_grade_b(self):
        result = ValidationResult(passed=True, score=85.0)
        assert result.grade == "B"

    def test_grade_f_for_low_score(self):
        result = ValidationResult(passed=False, score=40.0)
        assert result.grade == "F"


class TestTestValidator:
    def test_empty_suite_fails(self, analyzer, validator, empty_suite):
        analysis = analyzer.analyze(empty_suite)
        result = validator.validate(analysis)
        assert result.passed is False
        assert result.score < 60.0

    def test_well_tested_suite_passes(
        self, analyzer, validator, well_tested_suite
    ):
        analysis = analyzer.analyze(well_tested_suite)
        result = validator.validate(analysis)
        # A well-tested suite should pass (score ≥ 60)
        assert result.passed is True

    def test_criteria_results_populated(self, analyzer, validator, empty_suite):
        analysis = analyzer.analyze(empty_suite)
        result = validator.validate(analysis)
        assert len(result.criteria_results) == len(_DEFAULT_CRITERIA)

    def test_recommendations_generated_for_empty_suite(
        self, analyzer, validator, empty_suite
    ):
        analysis = analyzer.analyze(empty_suite)
        result = validator.validate(analysis)
        assert len(result.recommendations) > 0

    def test_adversarial_criterion_applicable_to_ai_product(
        self, analyzer, validator, tmp_path
    ):
        f = tmp_path / "test_basic.py"
        f.write_text("def test_x():\n    assert 1 == 1\n")
        suite = TestSuite(
            name="AI Product Suite",
            product="Azure OpenAI LLM",
            use_case="Chat AI",
            test_files=[str(f)],
        )
        analysis = analyzer.analyze(suite)
        result = validator.validate(analysis)
        adversarial_passed = result.criteria_results.get(
            "adversarial-tests-present", True
        )
        assert adversarial_passed is False

    def test_custom_criteria_respected(self, analyzer, empty_suite):
        from shadow_architect.core.validator import HasTestsCriterion

        custom_validator = TestValidator(criteria=[HasTestsCriterion()])
        analysis = analyzer.analyze(empty_suite)
        result = custom_validator.validate(analysis)
        assert result.criteria_results == {"has-tests": False}
