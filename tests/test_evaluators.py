"""Tests for shadow_architect.evaluators."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from shadow_architect.core.models import TestSuite
from shadow_architect.evaluators.adversarial import (
    AdversarialCategory,
    AdversarialEvaluator,
)
from shadow_architect.evaluators.coverage import CoverageEvaluator
from shadow_architect.evaluators.quality import QualityEvaluator


# ---------------------------------------------------------------------------
# CoverageEvaluator
# ---------------------------------------------------------------------------


class TestCoverageEvaluator:
    def test_no_source_files_returns_100_percent(self, tmp_path):
        f = tmp_path / "test_demo.py"
        f.write_text("def test_x():\n    assert True\n")
        suite = TestSuite(name="demo", test_files=[str(f)], source_files=[])
        result = CoverageEvaluator().evaluate(suite)
        assert result.coverage_percent == 100.0
        assert result.total_symbols == 0

    def test_covered_symbol_detected(self, tmp_path):
        src = tmp_path / "mymodule.py"
        src.write_text(
            textwrap.dedent(
                """\
                def compute_total(items):
                    return sum(items)
                """
            )
        )
        test_f = tmp_path / "test_mymodule.py"
        test_f.write_text(
            textwrap.dedent(
                """\
                from mymodule import compute_total

                def test_compute_total():
                    assert compute_total([1, 2, 3]) == 6
                """
            )
        )
        suite = TestSuite(
            name="demo",
            test_files=[str(test_f)],
            source_files=[str(src)],
        )
        result = CoverageEvaluator().evaluate(suite)
        assert result.covered_symbols >= 1
        assert "compute_total" not in result.uncovered_symbols

    def test_uncovered_symbol_flagged(self, tmp_path):
        src = tmp_path / "math_utils.py"
        src.write_text("def add(a, b):\n    return a + b\n\ndef subtract(a, b):\n    return a - b\n")
        test_f = tmp_path / "test_only_add.py"
        test_f.write_text("from math_utils import add\ndef test_add():\n    assert add(1, 2) == 3\n")
        suite = TestSuite(
            name="partial",
            test_files=[str(test_f)],
            source_files=[str(src)],
        )
        result = CoverageEvaluator().evaluate(suite)
        assert "subtract" in result.uncovered_symbols


# ---------------------------------------------------------------------------
# QualityEvaluator
# ---------------------------------------------------------------------------


class TestQualityEvaluator:
    def test_empty_list_returns_perfect_score(self):
        result = QualityEvaluator().evaluate([])
        assert result.quality_score == 100.0

    def test_trivial_assert_true_detected(self, tmp_path):
        f = tmp_path / "test_bad.py"
        f.write_text("def test_trivial():\n    assert True\n")
        result = QualityEvaluator().evaluate([str(f)])
        assert result.anti_patterns_found >= 1
        assert any("trivial" in finding.id for finding in result.findings)

    def test_bare_except_detected(self, tmp_path):
        content = textwrap.dedent(
            """\
            def test_swallows_error():
                try:
                    1 / 0
                except:
                    pass
                assert True
            """
        )
        f = tmp_path / "test_bare.py"
        f.write_text(content)
        result = QualityEvaluator().evaluate([str(f)])
        assert any("bare-except" in finding.id for finding in result.findings)

    def test_broad_except_detected(self, tmp_path):
        content = textwrap.dedent(
            """\
            def test_broad():
                try:
                    1 / 0
                except Exception:
                    pass
                assert 1 == 1
            """
        )
        f = tmp_path / "test_broad.py"
        f.write_text(content)
        result = QualityEvaluator().evaluate([str(f)])
        assert any("broad-except" in finding.id for finding in result.findings)

    def test_good_test_file_has_full_score(self, tmp_path):
        content = textwrap.dedent(
            """\
            def test_addition():
                result = 1 + 1
                assert result == 2

            def test_subtraction():
                result = 5 - 3
                assert result == 2
            """
        )
        f = tmp_path / "test_good.py"
        f.write_text(content)
        result = QualityEvaluator().evaluate([str(f)])
        assert result.anti_patterns_found == 0
        assert result.quality_score == 100.0


# ---------------------------------------------------------------------------
# AdversarialEvaluator
# ---------------------------------------------------------------------------


class TestAdversarialEvaluator:
    def test_empty_suite_flags_all_categories(self, tmp_path):
        suite = TestSuite(name="Empty", test_files=[])
        result = AdversarialEvaluator().evaluate(suite)
        assert set(result.categories_missing) == set(AdversarialCategory)
        assert len(result.generated_cases) > 0

    def test_prompt_injection_detected_in_file(self, tmp_path):
        f = tmp_path / "test_adversarial_injection.py"
        f.write_text("def test_adversarial_injection():\n    assert True\n")
        suite = TestSuite(name="AI", test_files=[str(f)])
        result = AdversarialEvaluator().evaluate(suite)
        assert AdversarialCategory.PROMPT_INJECTION in result.categories_covered

    def test_coverage_percent_zero_for_empty(self):
        suite = TestSuite(name="Empty", test_files=[])
        result = AdversarialEvaluator().evaluate(suite)
        assert result.coverage_percent == 0.0

    def test_finding_generated_for_missing_categories(self):
        suite = TestSuite(name="Empty", test_files=[])
        result = AdversarialEvaluator().evaluate(suite)
        assert len(result.findings) >= 1
        assert any("adversarial" in f.id for f in result.findings)

    @pytest.mark.parametrize("category", list(AdversarialCategory))
    def test_category_has_example_prompts(self, category):
        from shadow_architect.evaluators.adversarial import _EXAMPLE_PROMPTS

        assert category in _EXAMPLE_PROMPTS
        assert len(_EXAMPLE_PROMPTS[category]) > 0
