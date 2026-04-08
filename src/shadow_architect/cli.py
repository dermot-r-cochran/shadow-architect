"""Command-line interface for shadow-architect.

Usage examples::

    # Analyse a Python test suite
    shadow-architect run \\
        --suite "My AI Service" \\
        --product "Azure OpenAI Chat" \\
        --use-case "Conversational AI" \\
        --test-files tests/test_chat.py tests/test_integration.py \\
        --source-files src/chat.py src/utils.py \\
        --output-json report.json

    # Only print a summary without writing a file
    shadow-architect run --suite "Demo" --test-files tests/test_demo.py

    # Upload the report to Azure Blob Storage
    shadow-architect upload report.json --suite "My AI Service"
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Annotated

import typer

from shadow_architect.core.analyzer import TestStrategyAnalyzer
from shadow_architect.core.improver import TestImprover
from shadow_architect.core.models import TestSuite
from shadow_architect.core.reporter import TestReporter
from shadow_architect.core.validator import TestValidator
from shadow_architect.evaluators.adversarial import AdversarialEvaluator
from shadow_architect.evaluators.coverage import CoverageEvaluator
from shadow_architect.evaluators.quality import QualityEvaluator

app = typer.Typer(
    name="shadow-architect",
    help="Meta-testing framework for AI capabilities on Azure Cloud.",
    add_completion=False,
)


@app.command()
def run(
    suite: Annotated[str, typer.Option("--suite", "-s", help="Name of the test suite")],
    product: Annotated[
        str, typer.Option("--product", "-p", help="Product name (e.g. Azure OpenAI)")
    ] = "",
    use_case: Annotated[
        str,
        typer.Option("--use-case", "-u", help="Use case description (e.g. Conversational AI)"),
    ] = "",
    test_files: Annotated[
        list[Path],
        typer.Option(
            "--test-files",
            "-t",
            help="Paths to test files to analyse",
            exists=False,
        ),
    ] = [],
    source_files: Annotated[
        list[Path],
        typer.Option(
            "--source-files",
            "-f",
            help="Paths to source files (used for coverage estimation)",
            exists=False,
        ),
    ] = [],
    output_json: Annotated[
        Path | None,
        typer.Option("--output-json", "-o", help="Write JSON report to this path"),
    ] = None,
    fail_below: Annotated[
        float,
        typer.Option(
            "--fail-below",
            help="Exit with code 1 if validation score falls below this threshold",
        ),
    ] = 0.0,
    adversarial: Annotated[
        bool,
        typer.Option(
            "--adversarial/--no-adversarial",
            help="Run adversarial coverage evaluation (AI products)",
        ),
    ] = True,
) -> None:
    """Analyse, validate, and improve a test suite."""
    test_suite = TestSuite(
        name=suite,
        product=product,
        use_case=use_case,
        test_files=[str(f) for f in test_files],
        source_files=[str(f) for f in source_files],
    )

    typer.echo(f"Analysing test suite: {suite}")

    # 1. Analyse
    analyzer = TestStrategyAnalyzer()
    analysis = analyzer.analyze(test_suite)

    # 2. Coverage evaluation
    coverage_eval = CoverageEvaluator()
    coverage_result = coverage_eval.evaluate(test_suite)

    # 3. Quality evaluation
    quality_eval = QualityEvaluator()
    quality_result = quality_eval.evaluate(test_suite.test_files)

    # 4. Adversarial evaluation (optional)
    if adversarial:
        adv_eval = AdversarialEvaluator()
        adv_result = adv_eval.evaluate(test_suite)
        # Merge adversarial findings into analysis
        analysis.findings.extend(adv_result.findings)
        analysis.metadata["adversarial_coverage_percent"] = adv_result.coverage_percent
        analysis.metadata["adversarial_cases_generated"] = len(adv_result.generated_cases)

    # Merge quality findings
    analysis.findings.extend(quality_result.findings)

    # 5. Validate
    validator = TestValidator()
    validation = validator.validate(analysis)

    # 6. Build improvement plan
    improver = TestImprover()
    plan = improver.build_plan(analysis, validation)

    # 7. Report
    reporter = TestReporter()
    report = reporter.build_report(analysis, validation, plan)

    reporter.print_summary(report)

    if output_json is not None:
        reporter.write_json(report, output_json)
        typer.echo(f"\nReport written to: {output_json}")

    if fail_below > 0.0 and validation.score < fail_below:
        typer.echo(
            f"\nValidation score {validation.score:.1f} is below "
            f"threshold {fail_below:.1f}. Exiting with code 1.",
            err=True,
        )
        raise typer.Exit(code=1)


@app.command()
def upload(
    report_path: Annotated[
        Path, typer.Argument(help="Path to a JSON report file produced by 'run'")
    ],
    suite: Annotated[
        str | None,
        typer.Option("--suite", "-s", help="Suite name override for blob naming"),
    ] = None,
    account_url: Annotated[
        str | None,
        typer.Option(
            "--account-url",
            help="Azure Storage account URL (or set AZURE_STORAGE_ACCOUNT_URL)",
        ),
    ] = None,
) -> None:
    """Upload a JSON report to Azure Blob Storage."""
    from shadow_architect.azure.storage import StorageClient
    from shadow_architect.core.reporter import TestReport

    if not report_path.exists():
        typer.echo(f"Error: report file not found: {report_path}", err=True)
        raise typer.Exit(code=1)

    data = json.loads(report_path.read_text(encoding="utf-8"))
    report = TestReport(
        suite_name=suite or data.get("suite_name", "unknown"),
        product=data.get("product", ""),
        use_case=data.get("use_case", ""),
        metadata=data.get("metadata", {}),
    )

    client = StorageClient(account_url=account_url)
    blob_name = client.upload_report(report)
    typer.echo(f"Report uploaded: {blob_name}")


@app.command()
def generate_adversarial(
    suite: Annotated[str, typer.Option("--suite", "-s", help="Suite name")],
    product: Annotated[str, typer.Option("--product", "-p", help="Product name")] = "",
    use_case: Annotated[str, typer.Option("--use-case", "-u", help="Use case")] = "",
    test_files: Annotated[
        list[Path],
        typer.Option("--test-files", "-t", help="Existing test files"),
    ] = [],
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Output Python test stub file"),
    ] = None,
) -> None:
    """Generate adversarial test stubs for an AI capability."""
    test_suite = TestSuite(
        name=suite,
        product=product,
        use_case=use_case,
        test_files=[str(f) for f in test_files],
    )

    evaluator = AdversarialEvaluator()
    result = evaluator.evaluate(test_suite)

    if not result.generated_cases:
        typer.echo("All adversarial categories appear to be covered. No stubs generated.")
        return

    stub_lines: list[str] = [
        '"""Auto-generated adversarial test stubs by shadow-architect."""',
        "import pytest",
        "",
        "",
    ]
    for case in result.generated_cases:
        func_name = (
            f"test_adversarial_{case.category.value}_"
            + case.prompt[:20].lower()
        )
        # Replace all non-identifier characters with underscores
        func_name = re.sub(r"[^\w]", "_", func_name).strip("_")

        stub_lines += [
            f"def {func_name}():",
            f'    """',
            f"    Category: {case.category.value}",
            f"    Severity: {case.severity.value}",
            f"    Prompt: {case.prompt!r}",
            f"    Expected: {case.expected_behaviour}",
            f'    """',
            f"    # TODO: Call your AI system under test with the prompt above",
            f"    # and assert that the response matches the expected behaviour.",
            f"    response = None  # replace with actual call",
            f"    assert response is not None, 'Test not yet implemented'",
            "",
            "",
        ]

    stub_content = "\n".join(stub_lines)

    if output is not None:
        output.write_text(stub_content, encoding="utf-8")
        typer.echo(f"Adversarial test stubs written to: {output}")
    else:
        typer.echo(stub_content)


if __name__ == "__main__":
    app()
