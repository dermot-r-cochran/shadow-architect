"""Report generation module.

Produces human-readable and machine-readable reports summarising the
meta-testing analysis, validation, and improvement plan.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jinja2 import Environment, PackageLoader, select_autoescape

from shadow_architect.core.analyzer import StrategyAnalysis
from shadow_architect.core.improver import ImprovementPlan
from shadow_architect.core.models import Severity
from shadow_architect.core.validator import ValidationResult


@dataclass
class TestReport:
    """Aggregated report from a full meta-testing run."""

    suite_name: str
    product: str
    use_case: str
    generated_at: datetime = field(
        default_factory=lambda: datetime.now(tz=timezone.utc)
    )
    analysis: StrategyAnalysis | None = None
    validation: ValidationResult | None = None
    improvement_plan: ImprovementPlan | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def overall_score(self) -> float:
        if self.validation is not None:
            return self.validation.score
        return 0.0

    @property
    def grade(self) -> str:
        if self.validation is not None:
            return self.validation.grade
        return "N/A"

    def to_dict(self) -> dict[str, Any]:
        """Serialise report to a plain dictionary (JSON-compatible)."""
        analysis_data: dict[str, Any] = {}
        if self.analysis is not None:
            analysis_data = {
                "test_count": self.analysis.test_count,
                "assertion_count": self.analysis.assertion_count,
                "assertion_density": self.analysis.assertion_density,
                "mock_count": self.analysis.mock_count,
                "fixture_count": self.analysis.fixture_count,
                "parametrized_count": self.analysis.parametrized_count,
                "test_types_found": [t.value for t in self.analysis.test_types_found],
                "missing_test_types": [t.value for t in self.analysis.missing_test_types],
                "findings": [
                    {
                        "id": f.id,
                        "title": f.title,
                        "severity": f.severity.value,
                        "category": f.category,
                        "description": f.description,
                    }
                    for f in self.analysis.findings
                ],
            }

        validation_data: dict[str, Any] = {}
        if self.validation is not None:
            validation_data = {
                "passed": self.validation.passed,
                "score": self.validation.score,
                "grade": self.validation.grade,
                "criteria_results": self.validation.criteria_results,
                "findings": [
                    {
                        "id": f.id,
                        "title": f.title,
                        "severity": f.severity.value,
                        "category": f.category,
                        "description": f.description,
                    }
                    for f in self.validation.findings
                ],
            }

        plan_data: dict[str, Any] = {}
        if self.improvement_plan is not None:
            plan_data = {
                "recommendations": [
                    {
                        "id": r.id,
                        "title": r.title,
                        "priority": r.priority.value,
                        "category": r.category,
                        "effort": r.effort,
                        "description": r.description,
                    }
                    for r in self.improvement_plan.recommendations
                ],
                "quick_wins": [r.id for r in self.improvement_plan.quick_wins],
                "long_term": [r.id for r in self.improvement_plan.long_term],
            }

        return {
            "suite_name": self.suite_name,
            "product": self.product,
            "use_case": self.use_case,
            "generated_at": self.generated_at.isoformat(),
            "overall_score": self.overall_score,
            "grade": self.grade,
            "analysis": analysis_data,
            "validation": validation_data,
            "improvement_plan": plan_data,
            "metadata": self.metadata,
        }


class TestReporter:
    """Generates reports from a completed meta-testing run.

    Usage::

        reporter = TestReporter()
        report = reporter.build_report(suite, analysis, validation, plan)
        reporter.write_json(report, Path("report.json"))
        reporter.print_summary(report)
    """

    def build_report(
        self,
        analysis: StrategyAnalysis,
        validation: ValidationResult,
        plan: ImprovementPlan,
    ) -> TestReport:
        """Assemble a :class:`TestReport` from component results."""
        return TestReport(
            suite_name=analysis.suite.name,
            product=analysis.suite.product,
            use_case=analysis.suite.use_case,
            analysis=analysis,
            validation=validation,
            improvement_plan=plan,
        )

    def write_json(self, report: TestReport, path: Path) -> None:
        """Write the report as a JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(report.to_dict(), indent=2, default=str),
            encoding="utf-8",
        )

    def print_summary(self, report: TestReport) -> None:
        """Print a rich summary to the console."""
        try:
            from rich.console import Console
            from rich.panel import Panel
            from rich.table import Table

            console = Console()
            self._rich_summary(console, report)
        except ImportError:
            self._plain_summary(report)

    # ------------------------------------------------------------------
    def _rich_summary(self, console: Any, report: TestReport) -> None:
        from rich.panel import Panel
        from rich.table import Table

        score_color = (
            "green"
            if report.overall_score >= 80
            else "yellow"
            if report.overall_score >= 60
            else "red"
        )

        console.print(
            Panel(
                f"[bold]Meta-Testing Report[/bold]\n"
                f"Suite: [cyan]{report.suite_name}[/cyan]  "
                f"Product: [cyan]{report.product}[/cyan]  "
                f"Use Case: [cyan]{report.use_case}[/cyan]\n"
                f"Score: [{score_color}]{report.overall_score:.1f}/100 ({report.grade})[/{score_color}]",
                title="shadow-architect",
            )
        )

        if report.analysis:
            tbl = Table(title="Analysis Summary", show_header=True)
            tbl.add_column("Metric", style="bold")
            tbl.add_column("Value")
            tbl.add_row("Tests found", str(report.analysis.test_count))
            tbl.add_row("Assertions", str(report.analysis.assertion_count))
            tbl.add_row("Assertion density", f"{report.analysis.assertion_density:.2f}")
            tbl.add_row(
                "Test types", ", ".join(t.value for t in report.analysis.test_types_found)
            )
            console.print(tbl)

        if report.validation and report.validation.findings:
            console.print("\n[bold red]Findings[/bold red]")
            for f in report.validation.findings:
                sev_color = {
                    Severity.CRITICAL: "red",
                    Severity.HIGH: "orange3",
                    Severity.MEDIUM: "yellow",
                    Severity.LOW: "blue",
                    Severity.INFO: "dim",
                }.get(f.severity, "white")
                console.print(
                    f"  [{sev_color}][{f.severity.value.upper()}][/{sev_color}] "
                    f"{f.title}: {f.description}"
                )

        if report.improvement_plan and report.improvement_plan.recommendations:
            console.print("\n[bold green]Recommendations[/bold green]")
            for rec in report.improvement_plan.recommendations[:10]:
                console.print(f"  • ({rec.effort}) {rec.title}")

    def _plain_summary(self, report: TestReport) -> None:
        print(f"\n=== shadow-architect: Meta-Testing Report ===")
        print(f"Suite   : {report.suite_name}")
        print(f"Product : {report.product}")
        print(f"Use Case: {report.use_case}")
        print(f"Score   : {report.overall_score:.1f}/100  Grade: {report.grade}")

        if report.analysis:
            print(f"\nTests: {report.analysis.test_count}  "
                  f"Assertions: {report.analysis.assertion_count}  "
                  f"Density: {report.analysis.assertion_density:.2f}")

        if report.validation and report.validation.findings:
            print("\nFindings:")
            for f in report.validation.findings:
                print(f"  [{f.severity.value.upper()}] {f.title}")

        if report.improvement_plan and report.improvement_plan.recommendations:
            print("\nTop Recommendations:")
            for rec in report.improvement_plan.recommendations[:5]:
                print(f"  • [{rec.priority.value.upper()}] {rec.title}")
