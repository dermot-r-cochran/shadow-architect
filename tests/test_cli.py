"""Tests for shadow_architect CLI."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest
from typer.testing import CliRunner

from shadow_architect.cli import app


@pytest.fixture()
def runner():
    return CliRunner()


@pytest.fixture()
def test_file(tmp_path: Path) -> Path:
    f = tmp_path / "test_sample.py"
    f.write_text(
        textwrap.dedent(
            """\
            from unittest.mock import MagicMock

            def test_addition():
                assert 1 + 1 == 2

            def test_subtraction():
                assert 5 - 3 == 2
            """
        )
    )
    return f


class TestRunCommand:
    def test_run_with_no_test_files(self, runner):
        result = runner.invoke(app, ["run", "--suite", "Demo"])
        assert result.exit_code == 0

    def test_run_with_test_file_exits_zero(self, runner, test_file):
        result = runner.invoke(
            app,
            [
                "run",
                "--suite", "Demo",
                "--product", "Demo Product",
                "--use-case", "Testing",
                "--test-files", str(test_file),
            ],
        )
        assert result.exit_code == 0

    def test_run_writes_json_report(self, runner, test_file, tmp_path):
        out = tmp_path / "report.json"
        result = runner.invoke(
            app,
            [
                "run",
                "--suite", "JSON Test",
                "--test-files", str(test_file),
                "--output-json", str(out),
            ],
        )
        assert result.exit_code == 0
        assert out.exists()
        data = json.loads(out.read_text())
        assert data["suite_name"] == "JSON Test"

    def test_fail_below_exits_one_when_score_low(self, runner):
        result = runner.invoke(
            app,
            [
                "run",
                "--suite", "Empty",
                "--fail-below", "99",
            ],
        )
        assert result.exit_code == 1

    def test_fail_below_passes_when_above_threshold(self, runner, test_file):
        result = runner.invoke(
            app,
            [
                "run",
                "--suite", "Passing",
                "--test-files", str(test_file),
                "--fail-below", "0",
            ],
        )
        assert result.exit_code == 0


class TestDirectoryArguments:
    """A directory given to --test-files or --source-files stands for every
    .py file under it, which is how the README's gate commands pass a suite
    (``--test-files tests/``)."""

    @pytest.fixture()
    def suite_dir(self, tmp_path: Path) -> Path:
        suite = tmp_path / "suite"
        (suite / "nested").mkdir(parents=True)
        (suite / "test_top.py").write_text(
            "def test_one():\n    assert 1 == 1\n\n\ndef test_two():\n    assert 2 == 2\n"
        )
        (suite / "nested" / "test_deeper.py").write_text(
            "def test_three():\n    assert 3 == 3\n"
        )
        return suite

    def test_test_directory_is_read_at_any_depth(self, runner, suite_dir, tmp_path):
        out = tmp_path / "report.json"
        result = runner.invoke(
            app,
            [
                "run",
                "--suite", "Directory",
                "--test-files", str(suite_dir),
                "--output-json", str(out),
                "--fail-on", "high",
            ],
        )
        assert result.exit_code == 0
        assert json.loads(out.read_text())["analysis"]["test_count"] == 3

    def test_directory_without_python_tests_still_trips_the_gate(self, runner, tmp_path):
        # Only .py files are read from a directory, so the red line for a
        # suite with zero tests stays visible.
        empty = tmp_path / "suite"
        empty.mkdir()
        (empty / "notes.txt").write_text("def test_in_a_text_file():\n    assert 1 == 1\n")
        out = tmp_path / "report.json"
        result = runner.invoke(
            app,
            [
                "run",
                "--suite", "Empty directory",
                "--test-files", str(empty),
                "--output-json", str(out),
                "--fail-on", "critical",
            ],
        )
        assert result.exit_code == 1
        found = {f["id"] for f in json.loads(out.read_text())["validation"]["findings"]}
        assert "has-tests" in found

    def test_path_that_does_not_exist_is_still_reported(self, runner, test_file, tmp_path):
        out = tmp_path / "report.json"
        result = runner.invoke(
            app,
            [
                "run",
                "--suite", "Missing",
                "--test-files", str(test_file),
                "--test-files", str(tmp_path / "no_such_dir"),
                "--output-json", str(out),
                "--fail-on", "high",
            ],
        )
        assert result.exit_code == 1
        found = {f["id"] for f in json.loads(out.read_text())["analysis"]["findings"]}
        assert "missing-file-no_such_dir" in found

    def test_source_directory_is_read(self, runner, test_file, tmp_path):
        package = tmp_path / "src" / "pkg"
        package.mkdir(parents=True)
        (package / "calc.py").write_text(
            "def multiply(a, b):\n    return a * b\n\n\ndef divide(a, b):\n    return a / b\n"
        )
        out = tmp_path / "report.json"
        result = runner.invoke(
            app,
            [
                "run",
                "--suite", "Sources",
                "--test-files", str(test_file),
                "--source-files", str(tmp_path / "src"),
                "--output-json", str(out),
            ],
        )
        assert result.exit_code == 0
        # Neither symbol is referenced by the test file, so the sources were read.
        found = {f["id"] for f in json.loads(out.read_text())["analysis"]["findings"]}
        assert "low-symbol-coverage" in found

    def test_generate_adversarial_reads_a_test_directory(self, runner, tmp_path):
        suite = tmp_path / "suite"
        suite.mkdir()
        (suite / "test_fairness.py").write_text(
            "def test_reply_shows_no_demographic_bias():\n    assert 'reply' != ''\n"
        )
        result = runner.invoke(
            app,
            [
                "generate-adversarial",
                "--suite", "AI Service",
                "--product", "Azure OpenAI",
                "--test-files", str(suite),
            ],
        )
        assert result.exit_code == 0
        assert "def test_adversarial_jailbreak_" in result.output
        assert "def test_adversarial_bias_" not in result.output


class TestGenerateAdversarialCommand:
    def test_generates_stubs_to_stdout(self, runner):
        result = runner.invoke(
            app,
            [
                "generate-adversarial",
                "--suite", "AI Service",
                "--product", "Azure OpenAI GPT",
                "--use-case", "Chat AI",
            ],
        )
        assert result.exit_code == 0

    def test_generates_stubs_to_file(self, runner, tmp_path):
        out = tmp_path / "adversarial_tests.py"
        result = runner.invoke(
            app,
            [
                "generate-adversarial",
                "--suite", "AI Service",
                "--product", "Azure OpenAI",
                "--output", str(out),
            ],
        )
        assert result.exit_code == 0
        assert out.exists()
        content = out.read_text()
        assert "def test_adversarial_" in content


class TestUploadCommand:
    def test_upload_missing_file_exits_one(self, runner, tmp_path):
        result = runner.invoke(
            app,
            ["upload", str(tmp_path / "nonexistent.json")],
        )
        assert result.exit_code == 1

    def test_upload_json_report_mock(self, runner, tmp_path, monkeypatch):
        monkeypatch.setenv("SHADOW_ARCHITECT_MOCK_AZURE", "1")
        report_file = tmp_path / "report.json"
        report_file.write_text(
            json.dumps(
                {
                    "suite_name": "Upload Test",
                    "product": "P",
                    "use_case": "U",
                    "metadata": {},
                }
            )
        )
        result = runner.invoke(app, ["upload", str(report_file)])
        assert result.exit_code == 0
        assert "uploaded" in result.output.lower()

    @pytest.fixture()
    def stored(self, monkeypatch) -> dict[str, dict]:
        """Every blob the in-memory stub is handed, by blob name."""
        from shadow_architect.azure import storage

        monkeypatch.setenv("SHADOW_ARCHITECT_MOCK_AZURE", "1")
        blobs: dict[str, dict] = {}
        upload_blob = storage._MockBlobContainerClient.upload_blob

        def recording(self, name, data, overwrite=False):
            upload_blob(self, name, data, overwrite)
            blobs[name] = json.loads(self._store[name])

        monkeypatch.setattr(storage._MockBlobContainerClient, "upload_blob", recording)
        return blobs

    @pytest.fixture()
    def report_file(self, runner, test_file, tmp_path) -> Path:
        """A report as ``run --output-json`` writes it, findings included."""
        out = tmp_path / "report.json"
        result = runner.invoke(
            app,
            [
                "run",
                "--suite", "Upload Suite",
                "--product", "Azure OpenAI",
                "--test-files", str(test_file),
                "--output-json", str(out),
            ],
        )
        assert result.exit_code == 0
        return out

    def test_upload_stores_the_report_run_wrote(self, runner, report_file, stored):
        # The blob is the stored record of the run. It once held the suite
        # name, product, use case and metadata only: no findings, score 0.0.
        written = json.loads(report_file.read_text())
        assert written["validation"]["findings"]
        assert written["analysis"]["findings"]

        result = runner.invoke(app, ["upload", str(report_file)])

        assert result.exit_code == 0
        assert list(stored.values()) == [written]

    def test_suite_option_names_the_blob_only(self, runner, report_file, stored):
        result = runner.invoke(app, ["upload", str(report_file), "--suite", "Renamed"])

        assert result.exit_code == 0
        (blob_name, blob), = stored.items()
        assert blob_name.startswith("Renamed/")
        assert blob == json.loads(report_file.read_text())


class TestConsoleNamesWhatTrippedTheGate:
    """``--fail-on`` reads the analyzer's and the evaluators' findings as well
    as the validator's, so the console must list them too: a run that exits 1
    on ``--fail-on high`` names the HIGH finding on screen, not only in JSON."""

    @staticmethod
    def _screen(result) -> str:
        # Rich wraps long lines; compare on collapsed whitespace.
        return " ".join(result.output.split())

    def test_analyzer_high_finding_is_on_screen(self, runner, test_file, tmp_path):
        result = runner.invoke(
            app,
            [
                "run",
                "--suite", "Missing",
                "--test-files", str(test_file),
                "--test-files", str(tmp_path / "test_absent.py"),
                "--fail-on", "high",
            ],
        )
        assert result.exit_code == 1
        assert "[HIGH] Test file not found" in self._screen(result)

    def test_evaluator_high_finding_is_on_screen(self, runner, test_file):
        # An AI product with no adversarial tests: the adversarial evaluator
        # raises its own HIGH finding beside the validator's criterion.
        result = runner.invoke(
            app,
            [
                "run",
                "--suite", "AI",
                "--product", "Azure OpenAI",
                "--test-files", str(test_file),
                "--fail-on", "high",
            ],
        )
        assert result.exit_code == 1
        assert "[HIGH] Adversarial test coverage gaps" in self._screen(result)
