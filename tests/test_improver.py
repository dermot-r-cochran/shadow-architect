"""Tests for shadow_architect.core.improver."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from shadow_architect.core.analyzer import TestStrategyAnalyzer
from shadow_architect.core.improver import ImprovementPlan, TestImprover
from shadow_architect.core.models import Severity, TestSuite
from shadow_architect.core.validator import TestValidator


@pytest.fixture()
def analyzer():
    return TestStrategyAnalyzer()


@pytest.fixture()
def validator():
    return TestValidator()


@pytest.fixture()
def improver():
    return TestImprover()


def _make_suite(tmp_path: Path, product: str = "", use_case: str = "") -> TestSuite:
    f = tmp_path / "test_sample.py"
    f.write_text("def test_x():\n    assert 1 == 1\n")
    return TestSuite(
        name="Sample",
        product=product,
        use_case=use_case,
        test_files=[str(f)],
    )


class TestImprovementPlan:
    def test_critical_count_property(self):
        from shadow_architect.core.models import Recommendation

        plan = ImprovementPlan(
            recommendations=[
                Recommendation(
                    id="r1",
                    title="A",
                    description="b",
                    priority=Severity.CRITICAL,
                    category="x",
                ),
                Recommendation(
                    id="r2",
                    title="C",
                    description="d",
                    priority=Severity.HIGH,
                    category="x",
                ),
            ]
        )
        assert plan.critical_count == 1
        assert plan.high_count == 1


class TestTestImprover:
    def test_plan_is_returned(self, analyzer, validator, improver, tmp_path):
        suite = _make_suite(tmp_path)
        analysis = analyzer.analyze(suite)
        validation = validator.validate(analysis)
        plan = improver.build_plan(analysis, validation)
        assert isinstance(plan, ImprovementPlan)

    def test_no_duplicate_recommendations(
        self, analyzer, validator, improver, tmp_path
    ):
        suite = _make_suite(tmp_path)
        analysis = analyzer.analyze(suite)
        validation = validator.validate(analysis)
        plan = improver.build_plan(analysis, validation)
        ids = [r.id for r in plan.recommendations]
        assert len(ids) == len(set(ids))

    def test_recommendations_sorted_by_priority(
        self, analyzer, validator, improver, tmp_path
    ):
        """Higher-severity recommendations should appear first."""
        from shadow_architect.core.improver import _SEVERITY_ORDER

        suite = _make_suite(tmp_path)
        analysis = analyzer.analyze(suite)
        validation = validator.validate(analysis)
        plan = improver.build_plan(analysis, validation)
        orders = [
            _SEVERITY_ORDER.get(r.priority, 99) for r in plan.recommendations
        ]
        assert orders == sorted(orders)

    def test_azure_ai_recommendations_added_for_ai_product(
        self, analyzer, validator, improver, tmp_path
    ):
        suite = _make_suite(tmp_path, product="Azure OpenAI GPT", use_case="AI chat")
        analysis = analyzer.analyze(suite)
        validation = validator.validate(analysis)
        plan = improver.build_plan(analysis, validation)
        ids = [r.id for r in plan.recommendations]
        assert "rec-azure-ai-eval" in ids

    def test_quick_wins_are_low_effort(
        self, analyzer, validator, improver, tmp_path
    ):
        suite = _make_suite(tmp_path)
        analysis = analyzer.analyze(suite)
        validation = validator.validate(analysis)
        plan = improver.build_plan(analysis, validation)
        for rec in plan.quick_wins:
            assert rec.effort == "low"

    def test_long_term_are_high_effort(
        self, analyzer, validator, improver, tmp_path
    ):
        suite = _make_suite(tmp_path)
        analysis = analyzer.analyze(suite)
        validation = validator.validate(analysis)
        plan = improver.build_plan(analysis, validation)
        for rec in plan.long_term:
            assert rec.effort == "high"
