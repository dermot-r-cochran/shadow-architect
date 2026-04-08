"""Tests for shadow_architect.core.reporter."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from shadow_architect.core.analyzer import TestStrategyAnalyzer
from shadow_architect.core.improver import TestImprover
from shadow_architect.core.models import TestSuite
from shadow_architect.core.reporter import TestReport, TestReporter
from shadow_architect.core.validator import TestValidator


@pytest.fixture()
def full_report(tmp_path: Path) -> TestReport:
    f = tmp_path / "test_x.py"
    f.write_text("def test_one():\n    assert 1 == 1\n")
    suite = TestSuite(
        name="Reporter Suite",
        product="Demo Product",
        use_case="Demo Use Case",
        test_files=[str(f)],
    )
    analyzer = TestStrategyAnalyzer()
    validator = TestValidator()
    improver = TestImprover()
    reporter = TestReporter()

    analysis = analyzer.analyze(suite)
    validation = validator.validate(analysis)
    plan = improver.build_plan(analysis, validation)
    return reporter.build_report(analysis, validation, plan)


class TestTestReport:
    def test_overall_score_delegates_to_validation(self, full_report):
        assert full_report.overall_score == full_report.validation.score  # type: ignore[union-attr]

    def test_grade_is_letter(self, full_report):
        assert full_report.grade in ("A", "B", "C", "D", "F")

    def test_to_dict_contains_required_keys(self, full_report):
        d = full_report.to_dict()
        for key in (
            "suite_name", "product", "use_case", "generated_at",
            "overall_score", "grade", "analysis", "validation", "improvement_plan",
        ):
            assert key in d

    def test_to_dict_is_json_serialisable(self, full_report):
        d = full_report.to_dict()
        json_str = json.dumps(d, default=str)
        parsed = json.loads(json_str)
        assert parsed["suite_name"] == "Reporter Suite"


class TestTestReporter:
    def test_write_json_creates_file(self, full_report, tmp_path):
        reporter = TestReporter()
        out = tmp_path / "report.json"
        reporter.write_json(full_report, out)
        assert out.exists()
        data = json.loads(out.read_text())
        assert data["product"] == "Demo Product"

    def test_write_json_creates_parent_dirs(self, full_report, tmp_path):
        reporter = TestReporter()
        out = tmp_path / "nested" / "deep" / "report.json"
        reporter.write_json(full_report, out)
        assert out.exists()

    def test_print_summary_does_not_raise(self, full_report, capsys):
        reporter = TestReporter()
        reporter.print_summary(full_report)
        # Either rich or plain output – should complete without exception

    def test_empty_report_grade_na(self):
        report = TestReport(suite_name="X", product="Y", use_case="Z")
        assert report.grade == "N/A"
        assert report.overall_score == 0.0
