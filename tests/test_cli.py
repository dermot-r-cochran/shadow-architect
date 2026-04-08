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
