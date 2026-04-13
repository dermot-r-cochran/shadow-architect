"""Chaos experiment runner and orchestrator."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

from shadow_architect.chaos.base import ChaosExperiment
from shadow_architect.chaos.models import ChaosReport, ChaosResult, ChaosStatus

_console = Console()


class ChaosRunner:
    """Orchestrates a collection of :class:`ChaosExperiment` instances.

    Args:
        experiments: List of experiments to run.
        dry_run: When ``True``, list experiments without executing them.

    Example::

        runner = ChaosRunner([exp1, exp2, exp3])
        report = runner.run()
        runner.print_report(report)
    """

    def __init__(
        self,
        experiments: list[ChaosExperiment],
        *,
        dry_run: bool = False,
    ) -> None:
        self._experiments = experiments
        self._dry_run = dry_run

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, *, names: list[str] | None = None) -> ChaosReport:
        """Run all (or a subset of) experiments and return a :class:`ChaosReport`.

        Args:
            names: If provided, only experiments whose :attr:`~ChaosExperiment.name`
                appears in this list are executed.
        """
        selected = self._select(names)
        report = ChaosReport()

        if self._dry_run:
            for exp in selected:
                result = ChaosResult(
                    name=exp.name,
                    description=exp.description,
                    status=ChaosStatus.SKIPPED,
                    observations=["dry-run: experiment not executed"],
                )
                report.results.append(result)
                report.skipped += 1
                report.experiments_run += 1
            return report

        for exp in selected:
            result = exp.run()
            report.results.append(result)
            report.experiments_run += 1
            report.total_duration_seconds += result.duration_seconds
            if result.status == ChaosStatus.PASSED:
                report.passed += 1
            elif result.status == ChaosStatus.FAILED:
                report.failed += 1
            elif result.status == ChaosStatus.ERROR:
                report.errors += 1
            else:
                report.skipped += 1

        return report

    def print_report(self, report: ChaosReport) -> None:
        """Pretty-print the report to the console using :mod:`rich`."""
        table = Table(
            title="Chaos Engineering Report",
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("Experiment", style="bold")
        table.add_column("Status")
        table.add_column("Duration (s)", justify="right")
        table.add_column("Details")

        status_styles = {
            ChaosStatus.PASSED: "green",
            ChaosStatus.FAILED: "red",
            ChaosStatus.ERROR: "bright_red",
            ChaosStatus.SKIPPED: "yellow",
        }

        for result in report.results:
            style = status_styles.get(result.status, "white")
            details = result.error_details or "; ".join(result.observations[:2])
            table.add_row(
                result.name,
                f"[{style}]{result.status.value.upper()}[/{style}]",
                f"{result.duration_seconds:.3f}",
                details[:80],
            )

        _console.print(table)
        _console.print(
            f"\n[bold]Summary:[/bold] "
            f"{report.passed} passed, "
            f"{report.failed} failed, "
            f"{report.errors} errors, "
            f"{report.skipped} skipped  "
            f"(pass rate: {report.pass_rate:.0%})"
        )

    def write_json(self, report: ChaosReport, path: Path) -> None:
        """Write the report to *path* as JSON."""
        data: dict[str, Any] = {
            **report.summary(),
            "results": [
                {
                    "name": r.name,
                    "description": r.description,
                    "status": r.status.value,
                    "duration_seconds": round(r.duration_seconds, 6),
                    "error_details": r.error_details,
                    "observations": r.observations,
                    "metadata": r.metadata,
                    "timestamp": r.timestamp.isoformat(),
                }
                for r in report.results
            ],
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _select(self, names: list[str] | None) -> list[ChaosExperiment]:
        if names is None:
            return list(self._experiments)
        return [e for e in self._experiments if e.name in names]
