"""Tests for shadow_architect.core.analyzer."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from shadow_architect.core.analyzer import StrategyAnalysis, TestStrategyAnalyzer
from shadow_architect.core.models import Severity, TestSuite, TestType


@pytest.fixture()
def analyzer() -> TestStrategyAnalyzer:
    return TestStrategyAnalyzer()


@pytest.fixture()
def simple_test_file(tmp_path: Path) -> Path:
    """Write a minimal pytest file and return its path."""
    content = textwrap.dedent(
        """\
        def test_addition():
            assert 1 + 1 == 2

        def test_subtraction():
            assert 5 - 3 == 2
        """
    )
    p = tmp_path / "test_math.py"
    p.write_text(content)
    return p


@pytest.fixture()
def unit_test_file(tmp_path: Path) -> Path:
    content = textwrap.dedent(
        """\
        from unittest.mock import MagicMock
        import pytest

        @pytest.fixture()
        def client():
            return MagicMock()

        @pytest.mark.parametrize("x,y", [(1, 2), (3, 4)])
        def test_unit_sum(x, y):
            mock = MagicMock()
            mock.add.return_value = x + y
            assert mock.add(x, y) == x + y
        """
    )
    p = tmp_path / "test_unit_example.py"
    p.write_text(content)
    return p


class TestStrategyAnalyzerBasic:
    def test_empty_suite_produces_no_tests_finding(self, analyzer, tmp_path):
        suite = TestSuite(name="Empty", test_files=[])
        result = analyzer.analyze(suite)
        assert result.test_count == 0
        ids = [f.id for f in result.findings]
        assert "no-tests" in ids

    def test_simple_file_counts_tests(self, analyzer, simple_test_file):
        suite = TestSuite(name="Math", test_files=[str(simple_test_file)])
        result = analyzer.analyze(suite)
        assert result.test_count == 2
        assert result.assertion_count == 2

    def test_assertion_density_calculated(self, analyzer, simple_test_file):
        suite = TestSuite(name="Math", test_files=[str(simple_test_file)])
        result = analyzer.analyze(suite)
        assert result.assertion_density == pytest.approx(1.0)

    def test_unit_test_type_detected(self, analyzer, unit_test_file):
        suite = TestSuite(name="Units", test_files=[str(unit_test_file)])
        result = analyzer.analyze(suite)
        assert TestType.UNIT in result.test_types_found

    def test_mock_count_detected(self, analyzer, unit_test_file):
        suite = TestSuite(name="Mocked", test_files=[str(unit_test_file)])
        result = analyzer.analyze(suite)
        assert result.mock_count > 0

    def test_fixture_count_detected(self, analyzer, unit_test_file):
        suite = TestSuite(name="Fixtures", test_files=[str(unit_test_file)])
        result = analyzer.analyze(suite)
        assert result.fixture_count >= 1

    def test_parametrized_count_detected(self, analyzer, unit_test_file):
        suite = TestSuite(name="Params", test_files=[str(unit_test_file)])
        result = analyzer.analyze(suite)
        assert result.parametrized_count >= 1

    def test_missing_file_produces_high_finding(self, analyzer):
        suite = TestSuite(name="Ghost", test_files=["/nonexistent/path/test_x.py"])
        result = analyzer.analyze(suite)
        assert any(
            f.severity == Severity.HIGH and "not found" in f.title.lower()
            for f in result.findings
        )

    def test_ai_product_recommends_adversarial_tests(self, analyzer, simple_test_file):
        suite = TestSuite(
            name="AI Suite",
            product="Azure OpenAI GPT",
            use_case="Conversational AI model",
            test_files=[str(simple_test_file)],
        )
        result = analyzer.analyze(suite)
        assert TestType.ADVERSARIAL in result.missing_test_types

    def test_has_adequate_coverage_false_when_critical_findings(
        self, analyzer
    ):
        suite = TestSuite(name="Empty")
        result = analyzer.analyze(suite)
        assert result.has_adequate_coverage is False

    def test_syntax_error_in_file_produces_finding(self, analyzer, tmp_path):
        bad_file = tmp_path / "test_bad.py"
        bad_file.write_text("def test_oops(:\n    pass\n")
        suite = TestSuite(name="Bad", test_files=[str(bad_file)])
        result = analyzer.analyze(suite)
        assert any("syntax" in f.id.lower() for f in result.findings)
