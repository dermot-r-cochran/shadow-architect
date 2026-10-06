"""Guard tests for the architecture decision records in docs/adr/.

Each test here pins a decision so that a later change cannot quietly undo it.
Today only ADR 002 (gating authority for irreversible decisions) has a guard;
the other ADRs do not yet have one.
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest
from typer.testing import CliRunner

from shadow_architect.cli import app

# ADR 002's own failure mode for score-threshold gating: "An AI product is
# deployed to external users with no prompt injection checks because the
# overall score was 72/100." The fixture is that product: AI context, unit,
# integration and security tests present, no adversarial tests at all.
AI_PRODUCT = ["--product", "Azure OpenAI Chat", "--use-case", "Conversational AI"]


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture()
def ai_suite_without_adversarial_tests(tmp_path: Path) -> list[str]:
    body = textwrap.dedent(
        """\
        def test_reply_is_text():
            assert isinstance("hello", str)
        """
    )
    args: list[str] = []
    for name in ("test_chat_unit.py", "test_chat_integration.py", "test_chat_security.py"):
        path = tmp_path / name
        path.write_text(body)
        args += ["--test-files", str(path)]
    return args


def _run(runner: CliRunner, files: list[str], out: Path, *extra: str):
    return runner.invoke(
        app,
        ["run", "--suite", "ADR 002", *AI_PRODUCT, *files, "--output-json", str(out), *extra],
    )


class TestAdr002GatingOnFindingsNotScore:
    def test_fail_on_high_blocks_ai_product_without_adversarial_tests(
        self, runner, ai_suite_without_adversarial_tests, tmp_path
    ):
        out = tmp_path / "report.json"
        result = _run(runner, ai_suite_without_adversarial_tests, out, "--fail-on", "high")

        # The score alone would let this release through ...
        validation = json.loads(out.read_text())["validation"]
        assert validation["score"] >= 60
        assert validation["passed"] is True
        # ... and the finding-severity gate does not.
        assert result.exit_code == 1

    def test_without_fail_on_exit_code_is_unchanged(
        self, runner, ai_suite_without_adversarial_tests, tmp_path
    ):
        out = tmp_path / "report.json"
        result = _run(runner, ai_suite_without_adversarial_tests, out)
        assert result.exit_code == 0

    def test_fail_on_critical_ignores_high_only_findings(
        self, runner, ai_suite_without_adversarial_tests, tmp_path
    ):
        out = tmp_path / "report.json"
        result = _run(
            runner,
            ai_suite_without_adversarial_tests,
            out,
            "--no-adversarial",
            "--fail-on",
            "critical",
        )
        assert result.exit_code == 0

    def test_fail_on_critical_blocks_a_suite_with_no_tests(self, runner):
        result = runner.invoke(app, ["run", "--suite", "Empty", "--fail-on", "critical"])
        assert result.exit_code == 1
