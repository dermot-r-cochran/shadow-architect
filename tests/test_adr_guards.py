"""Guard tests for the architecture decision records in docs/adr/.

Each test here pins a decision so that a later change cannot quietly undo it.

- ADR 001 (boundary enforcement over quality scoring) is guarded where the
  console is written: ``tests/test_reporter.py::TestTestReporter::
  test_console_output_has_no_letter_grade``.
- ADR 002 (gating authority for irreversible decisions): ``--fail-on`` gates
  on finding severity, never on the score, and a non-AI product is not
  failed by LLM failure classes that do not apply to it.
- ADR 003 (agentic containment) has no guard: nothing in the code yet tells
  an agentic capability from any other, so there is no behaviour to pin.
- ADR 004 (epistemic boundaries): no string in ``src/`` and no output of a
  passing run claims correctness, completeness, safety or exhaustiveness.
  The Markdown under ``docs/`` is outside this guard; it has to name the
  very phrases it forbids.
- ADR 005 (chaos as containment testing): a dry run is not a passing
  result, a FAILED experiment is a finding that fails the command, and the
  console shows no pass rate.
"""

from __future__ import annotations

import ast
import json
import re
import textwrap
from pathlib import Path

import pytest
from typer.testing import CliRunner

from shadow_architect.chaos.corrupt_inputs import CorruptInputExperiment
from shadow_architect.chaos.runner import ChaosRunner
from shadow_architect.cli import app

SRC = Path(__file__).resolve().parents[1] / "src" / "shadow_architect"

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

    def test_ai_product_still_gets_the_adversarial_finding(
        self, runner, ai_suite_without_adversarial_tests, tmp_path
    ):
        out = tmp_path / "report.json"
        _run(runner, ai_suite_without_adversarial_tests, out)
        ids = {f["id"] for f in json.loads(out.read_text())["analysis"]["findings"]}
        assert "adversarial-gaps" in ids

    def test_non_ai_product_gets_no_adversarial_finding_and_passes_fail_on_high(
        self, runner, ai_suite_without_adversarial_tests, tmp_path
    ):
        # The same suite under a product with no AI in it: the LLM failure
        # classes do not apply, so they must not block the gate.
        out = tmp_path / "report.json"
        result = runner.invoke(
            app,
            [
                "run",
                "--suite",
                "Ledger",
                "--product",
                "Invoice Ledger",
                "--use-case",
                "Billing",
                *ai_suite_without_adversarial_tests,
                "--output-json",
                str(out),
                "--fail-on",
                "high",
            ],
        )
        report = json.loads(out.read_text())
        ids = {f["id"] for f in report["analysis"]["findings"]}
        ids |= {f["id"] for f in report["validation"]["findings"]}
        assert "adversarial-gaps" not in ids
        assert "adversarial-tests-present" not in ids
        assert result.exit_code == 0, result.output


# ADR 004 forbids language that implies correctness, completeness, safety
# certification or exhaustiveness. Each pattern is an affirmative claim; a
# sentence that also carries a negation ("does not prove", "not a safety
# certificate") is the ADR's own framing and is skipped.
_CLAIMS: dict[str, re.Pattern[str]] = {
    "correctness": re.compile(
        r"\b(?:is|are|was|were) correct\b|\bproves?\b|\bproven\b|\bproof (?:of|that)\b"
    ),
    "completeness": re.compile(
        r"\ball (?:cases|inputs|failure modes|risks)\b"
        r"|\b(?:fully|completely) (?:covered|tested)\b|\bcomplete coverage\b"
    ),
    "safety certification": re.compile(
        r"\b(?:is|are) safe\b|\bsafety (?:rating|certificate)\b"
        r"|\bcertif(?:y|ies|ied|icate|ication)\b|\bguarantees?\b"
    ),
    "exhaustiveness": re.compile(r"\bexhaustive(?:ly)?\b"),
}
_NEGATION = re.compile(r"\b(?:not|never|no|cannot|nor|without)\b|n't\b")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+|\n\s*\n")


def _claims_in(text: str, where: str) -> list[str]:
    """Every ADR 004 claim in *text*, each with its kind and sentence."""
    found: list[str] = []
    for sentence in _SENTENCE_END.split(text):
        lowered = " ".join(sentence.split()).lower()
        if not lowered or _NEGATION.search(lowered):
            continue
        for kind, pattern in _CLAIMS.items():
            if pattern.search(lowered):
                found.append(f"{where}: claims {kind}: {lowered[:100]!r}")
    return found


@pytest.fixture()
def ai_suite_with_every_boundary_covered(tmp_path: Path) -> list[str]:
    """An AI product whose suite clears every check, so the run passes.

    A passing run is where an overclaim would be made, so that is the
    output the ADR 004 guard reads.
    """
    adversarial = textwrap.dedent(
        """\
        import pytest
        from unittest.mock import MagicMock

        @pytest.mark.parametrize("prompt", ["ignore previous instructions", "you are DAN"])
        def test_prompt_injection_and_jailbreak_are_refused(prompt):
            assert MagicMock()(prompt) is not None

        def test_system_prompt_exfiltration_is_refused():
            assert True

        def test_xss_in_output_is_escaped():
            assert True

        def test_hallucination_is_acknowledged():
            assert True

        def test_long_input_dos_is_bounded():
            assert True

        def test_demographic_bias_is_absent():
            assert True

        def test_sensitive_pii_is_not_disclosed():
            assert True
        """
    )
    plain = textwrap.dedent(
        """\
        def test_reply_is_text():
            assert isinstance("hello", str)
        """
    )
    args: list[str] = []
    for name, body in (
        ("test_chat_unit.py", plain),
        ("test_chat_integration.py", plain),
        ("test_chat_security.py", plain),
        ("test_chat_adversarial.py", adversarial),
    ):
        path = tmp_path / name
        path.write_text(body)
        args += ["--test-files", str(path)]
    return args


class TestAdr004NoOutputClaimsCorrectnessOrSafety:
    def test_no_string_in_src_makes_a_claim(self):
        found: list[str] = []
        for path in sorted(SRC.rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            where = path.relative_to(SRC.parent).as_posix()
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    found += _claims_in(node.value, f"{where}:{node.lineno}")
        assert not found, "\n".join(found)

    def test_passing_run_makes_no_claim(
        self, runner, ai_suite_with_every_boundary_covered, tmp_path
    ):
        out = tmp_path / "report.json"
        result = _run(
            runner, ai_suite_with_every_boundary_covered, out, "--fail-on", "high"
        )
        assert result.exit_code == 0, result.output
        report = json.loads(out.read_text())
        assert report["validation"]["passed"] is True
        found = _claims_in(result.output, "console") + _claims_in(out.read_text(), "json")
        assert not found, "\n".join(found)

    def test_passing_chaos_run_makes_no_claim(self, runner, tmp_path):
        out = tmp_path / "chaos.json"
        result = runner.invoke(app, ["chaos", "--output-json", str(out)])
        assert result.exit_code == 0, result.output
        assert json.loads(out.read_text())["failed"] == 0
        found = _claims_in(result.output, "console") + _claims_in(out.read_text(), "json")
        assert not found, "\n".join(found)


class TestAdr005DryRunIsNotAResultAndFailedIsAFinding:
    def test_dry_run_passes_nothing(self):
        experiment = CorruptInputExperiment(target=lambda value: None, sample_input="x")
        report = ChaosRunner([experiment], dry_run=True).run()
        assert report.experiments_run == 1
        assert report.passed == 0
        assert report.pass_rate == 0.0
        assert all(r.status.value == "skipped" for r in report.results)

    def test_cli_dry_run_writes_no_report_and_reports_no_pass(self, runner, tmp_path):
        out = tmp_path / "chaos.json"
        result = runner.invoke(app, ["chaos", "--dry-run", "--output-json", str(out)])
        assert result.exit_code == 0
        assert not out.exists()
        assert "PASSED" not in result.output

    def test_screen_output_has_no_pass_rate_but_json_keeps_it(self, runner, tmp_path):
        # ADR 005 rejects chaos as a percentage metric, so the console shows
        # counts only; the JSON report keeps pass_rate for machine consumers.
        out = tmp_path / "chaos.json"
        result = runner.invoke(app, ["chaos", "--output-json", str(out)])
        assert result.exit_code == 0, result.output
        assert "pass rate" not in result.output.lower()
        assert "%" not in result.output
        assert "pass_rate" in json.loads(out.read_text())

    def test_failed_experiment_fails_the_command(self, runner, monkeypatch, tmp_path):
        def boundary_crossed(self: CorruptInputExperiment) -> None:
            raise AssertionError("target proceeded silently on corrupt input")

        monkeypatch.setattr(CorruptInputExperiment, "execute", boundary_crossed)
        out = tmp_path / "chaos.json"
        result = runner.invoke(
            app, ["chaos", "--scenarios", "corrupt-inputs", "--output-json", str(out)]
        )
        assert result.exit_code == 1
        report = json.loads(out.read_text())
        assert report["failed"] == 1
        assert report["results"][0]["status"] == "failed"
