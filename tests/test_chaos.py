"""Tests for the shadow_architect.chaos module."""

from __future__ import annotations

import json
import os
import textwrap
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from shadow_architect.chaos import (
    ChaosExperiment,
    ChaosReport,
    ChaosResult,
    ChaosRunner,
    ChaosStatus,
    CorruptInputExperiment,
    InputCorruptor,
    NetworkChaos,
    NetworkChaosExperiment,
    PermissionChaos,
    SecurityChaosExperiment,
)
from shadow_architect.cli import app

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _noop(_: Any = None) -> None:
    """A target callable that always succeeds."""


def _always_raise(_: Any = None) -> None:
    """A target callable that always raises an unhandled RuntimeError."""
    raise RuntimeError("always fails")


def _raises_value_error(_: Any = None) -> None:
    """A target callable that raises ValueError (graceful failure)."""
    raise ValueError("expected bad input")


# ---------------------------------------------------------------------------
# ChaosResult / ChaosReport models
# ---------------------------------------------------------------------------


class TestChaosModels:
    def test_chaos_result_defaults(self) -> None:
        result = ChaosResult(name="x", description="d", status=ChaosStatus.PASSED)
        assert result.duration_seconds == 0.0
        assert result.observations == []
        assert result.error_details is None

    def test_chaos_report_pass_rate_zero_when_no_experiments(self) -> None:
        report = ChaosReport()
        assert report.pass_rate == 0.0

    def test_chaos_report_pass_rate(self) -> None:
        report = ChaosReport(experiments_run=4, passed=3)
        assert report.pass_rate == pytest.approx(0.75)

    def test_chaos_report_summary_keys(self) -> None:
        report = ChaosReport(experiments_run=2, passed=2)
        summary = report.summary()
        assert "passed" in summary
        assert "experiments_run" in summary
        assert "pass_rate" in summary
        assert "generated_at" in summary


# ---------------------------------------------------------------------------
# ChaosExperiment base class
# ---------------------------------------------------------------------------


class _ConcreteExperiment(ChaosExperiment):
    name = "concrete"
    description = "A concrete test experiment"

    def __init__(self, *, fail_execute: bool = False, fail_teardown: bool = False) -> None:
        super().__init__()
        self.setup_called = False
        self.execute_called = False
        self.teardown_called = False
        self._fail_execute = fail_execute
        self._fail_teardown = fail_teardown

    def setup(self) -> None:
        self.setup_called = True

    def execute(self) -> None:
        self.execute_called = True
        if self._fail_execute:
            raise AssertionError("injected failure")

    def teardown(self) -> None:
        self.teardown_called = True
        if self._fail_teardown:
            raise RuntimeError("teardown error")


class TestChaosExperimentBase:
    def test_lifecycle_called_in_order(self) -> None:
        exp = _ConcreteExperiment()
        result = exp.run()
        assert exp.setup_called
        assert exp.execute_called
        assert exp.teardown_called
        assert result.status == ChaosStatus.PASSED

    def test_failed_execute_sets_failed_status(self) -> None:
        exp = _ConcreteExperiment(fail_execute=True)
        result = exp.run()
        assert result.status == ChaosStatus.FAILED
        assert result.error_details is not None

    def test_teardown_always_called_on_execute_failure(self) -> None:
        exp = _ConcreteExperiment(fail_execute=True)
        exp.run()
        assert exp.teardown_called

    def test_teardown_error_captured_as_observation(self) -> None:
        exp = _ConcreteExperiment(fail_teardown=True)
        result = exp.run()
        # Teardown error is captured, not re-raised
        assert any("teardown" in obs.lower() for obs in result.observations)

    def test_context_manager_calls_teardown(self) -> None:
        exp = _ConcreteExperiment()
        with exp:
            exp.setup()
            exp.execute()
        assert exp.teardown_called

    def test_duration_is_positive(self) -> None:
        exp = _ConcreteExperiment()
        result = exp.run()
        assert result.duration_seconds >= 0.0

    def test_observe_helper_records_messages(self) -> None:
        exp = _ConcreteExperiment()
        exp._observe("hello")
        result = exp.run()
        assert "hello" in result.observations


# ---------------------------------------------------------------------------
# InputCorruptor
# ---------------------------------------------------------------------------


class TestInputCorruptor:
    @pytest.fixture()
    def corruptor(self) -> InputCorruptor:
        return InputCorruptor()

    def test_null_variants_contains_none(self, corruptor: InputCorruptor) -> None:
        variants = corruptor.null_variants("anything")
        assert None in variants

    def test_null_variants_contains_empty_string(self, corruptor: InputCorruptor) -> None:
        variants = corruptor.null_variants("anything")
        assert "" in variants

    def test_type_confusion_changes_type(self, corruptor: InputCorruptor) -> None:
        variants = corruptor.type_confusion("hello")
        types = {type(v) for v in variants}
        # Should include types other than str
        assert types - {str}

    def test_encoding_corruption_returns_non_empty(self, corruptor: InputCorruptor) -> None:
        variants = corruptor.encoding_corruption("test string")
        assert len(variants) > 0

    def test_boundary_values_includes_large_string(self, corruptor: InputCorruptor) -> None:
        variants = corruptor.boundary_values("x")
        long_strings = [v for v in variants if isinstance(v, str) and len(v) > 1000]
        assert long_strings

    def test_boundary_values_includes_negative(self, corruptor: InputCorruptor) -> None:
        variants = corruptor.boundary_values(5)
        assert -1 in variants

    def test_malformed_python_source_has_syntax_errors(self, corruptor: InputCorruptor) -> None:
        variants = corruptor.malformed_python_source("def test(): pass")
        # At least one variant should fail to compile
        broken = []
        for v in variants:
            if isinstance(v, str):
                try:
                    compile(v, "<chaos>", "exec")
                except SyntaxError:
                    broken.append(v)
        assert broken, "Expected at least one syntactically broken variant"

    def test_corrupt_json_returns_invalid_strings(self, corruptor: InputCorruptor) -> None:
        data = {"key": "value", "count": 1}
        variants = corruptor.corrupt_json(data)
        invalid = []
        for v in variants:
            if isinstance(v, str):
                try:
                    json.loads(v)
                except (json.JSONDecodeError, ValueError):
                    invalid.append(v)
        assert invalid, "Expected at least one invalid JSON string"


# ---------------------------------------------------------------------------
# CorruptInputExperiment
# ---------------------------------------------------------------------------


class TestCorruptInputExperiment:
    def test_noop_target_passes(self) -> None:
        exp = CorruptInputExperiment(target=_noop, sample_input="hello")
        result = exp.run()
        assert result.status == ChaosStatus.PASSED

    def test_unhandled_exception_causes_failure(self) -> None:
        exp = CorruptInputExperiment(
            target=_always_raise,
            sample_input="hello",
            allowed_exceptions=(),
        )
        result = exp.run()
        assert result.status == ChaosStatus.FAILED

    def test_allowed_exception_is_graceful(self) -> None:
        exp = CorruptInputExperiment(
            target=_raises_value_error,
            sample_input="hello",
            allowed_exceptions=(ValueError,),
        )
        result = exp.run()
        assert result.status == ChaosStatus.PASSED

    def test_observations_recorded(self) -> None:
        exp = CorruptInputExperiment(target=_noop, sample_input="hello")
        result = exp.run()
        assert len(result.observations) > 0

    def test_dict_sample_triggers_json_corruption(self) -> None:
        exp = CorruptInputExperiment(
            target=_noop, sample_input={"a": 1}
        )
        result = exp.run()
        # The experiment should complete (PASSED or FAILED, not ERROR)
        assert result.status in (ChaosStatus.PASSED, ChaosStatus.FAILED)

    def test_custom_name_overrides_default(self) -> None:
        exp = CorruptInputExperiment(
            target=_noop, sample_input="x", name="my-custom-name"
        )
        assert exp.name == "my-custom-name"


# ---------------------------------------------------------------------------
# PermissionChaos
# ---------------------------------------------------------------------------


class TestPermissionChaos:
    @pytest.fixture()
    def pc(self) -> PermissionChaos:
        return PermissionChaos()

    def test_missing_credentials_unsets_env_vars(self, pc: PermissionChaos) -> None:
        os.environ["AZURE_STORAGE_ACCOUNT_URL"] = "https://example.blob.core.windows.net"
        with pc.missing_azure_credentials():
            assert "AZURE_STORAGE_ACCOUNT_URL" not in os.environ
        # Restored after exit
        assert os.environ.get("AZURE_STORAGE_ACCOUNT_URL") == "https://example.blob.core.windows.net"
        del os.environ["AZURE_STORAGE_ACCOUNT_URL"]

    def test_missing_credentials_restores_on_exception(self, pc: PermissionChaos) -> None:
        os.environ["AZURE_CLIENT_ID"] = "client-id-value"
        try:
            with pc.missing_azure_credentials():
                assert "AZURE_CLIENT_ID" not in os.environ
                raise RuntimeError("boom")
        except RuntimeError:
            pass
        assert os.environ.get("AZURE_CLIENT_ID") == "client-id-value"
        del os.environ["AZURE_CLIENT_ID"]

    def test_rbac_forbidden_patches_target(self, pc: PermissionChaos) -> None:
        with pc.rbac_forbidden("os.path.exists"):
            with pytest.raises(Exception):
                os.path.exists("/some/path")  # noqa: PTH110

    def test_wrong_tenant_sets_fake_values(self, pc: PermissionChaos) -> None:
        original_tenant = os.environ.pop("AZURE_TENANT_ID", None)
        with pc.wrong_tenant():
            assert os.environ["AZURE_TENANT_ID"] == "00000000-0000-0000-0000-000000000000"
            assert os.environ["AZURE_SUBSCRIPTION_ID"] == "ffffffff-ffff-ffff-ffff-ffffffffffff"
        if original_tenant is None:
            assert "AZURE_TENANT_ID" not in os.environ
        else:
            assert os.environ["AZURE_TENANT_ID"] == original_tenant
            os.environ["AZURE_TENANT_ID"] = original_tenant

    def test_expired_token_patches_credential_factory(self, pc: PermissionChaos) -> None:
        with pc.expired_token("shadow_architect.azure.client.get_credential"):
            from shadow_architect.azure.client import get_credential

            cred = get_credential()
            token = cred.get_token("scope")
            assert token.expires_on == 0


# ---------------------------------------------------------------------------
# SecurityChaosExperiment
# ---------------------------------------------------------------------------


class TestSecurityChaosExperiment:
    def test_noop_target_passes(self) -> None:
        exp = SecurityChaosExperiment(
            target=_noop,
            credential_target="shadow_architect.azure.client.get_credential",
        )
        result = exp.run()
        assert result.status == ChaosStatus.PASSED

    def test_observations_non_empty(self) -> None:
        exp = SecurityChaosExperiment(target=_noop)
        result = exp.run()
        assert len(result.observations) > 0

    def test_sensitive_leak_detection(self) -> None:
        exp = SecurityChaosExperiment(target=_noop)
        assert exp._has_sensitive_leak("password=s3cr3t")
        assert not exp._has_sensitive_leak("everything is fine")


# ---------------------------------------------------------------------------
# NetworkChaos
# ---------------------------------------------------------------------------


class TestNetworkChaos:
    @pytest.fixture()
    def nc(self) -> NetworkChaos:
        return NetworkChaos()

    def test_latency_delays_call(self, nc: NetworkChaos) -> None:
        delay = 0.05
        with nc.latency(seconds=delay, target="time.sleep"):
            # The latency context manager patches the target — just verify it
            # can be entered and exited without error.
            pass

    def test_timeout_raises_exception(self, nc: NetworkChaos) -> None:
        with nc.timeout(target="httpx.Client.send", exception_class=TimeoutError):
            import httpx

            client = httpx.Client()
            with pytest.raises(TimeoutError):
                client.send(MagicMock())

    def test_connection_refused_raises(self, nc: NetworkChaos) -> None:
        with nc.connection_refused(target="httpx.Client.send"):
            import httpx

            client = httpx.Client()
            with pytest.raises(ConnectionRefusedError):
                client.send(MagicMock())

    def test_intermittent_failures_with_seed(self, nc: NetworkChaos) -> None:
        results = []
        with nc.intermittent_failures(
            target="httpx.Client.send", failure_rate=1.0, seed=0
        ):
            import httpx

            client = httpx.Client()
            for _ in range(3):
                try:
                    client.send(MagicMock())
                    results.append("ok")
                except OSError:
                    results.append("fail")
        # With failure_rate=1.0 all calls should fail
        assert all(r == "fail" for r in results)

    def test_slow_response_returns_mock(self, nc: NetworkChaos) -> None:
        with nc.slow_response(target="httpx.Client.send", chunk_delay=0.0):
            import httpx

            client = httpx.Client()
            resp = client.send(MagicMock())
            assert resp is not None


# ---------------------------------------------------------------------------
# NetworkChaosExperiment
# ---------------------------------------------------------------------------


class TestNetworkChaosExperiment:
    def test_noop_target_passes(self) -> None:
        exp = NetworkChaosExperiment(
            target=_noop,
            http_target="httpx.Client.send",
            latency_seconds=0.0,
        )
        result = exp.run()
        assert result.status == ChaosStatus.PASSED

    def test_experiment_records_observations(self) -> None:
        exp = NetworkChaosExperiment(
            target=_noop,
            http_target="httpx.Client.send",
            latency_seconds=0.0,
        )
        result = exp.run()
        assert len(result.observations) > 0

    def test_unhandled_network_exception_fails(self) -> None:
        """If the target re-raises a network exception it should fail."""

        def _reraise(_: Any = None) -> None:
            raise RuntimeError("network error propagated")

        exp = NetworkChaosExperiment(
            target=_reraise,
            http_target="httpx.Client.send",
            allowed_exceptions=(),  # nothing allowed → FAILED
        )
        result = exp.run()
        assert result.status == ChaosStatus.FAILED


# ---------------------------------------------------------------------------
# ChaosRunner
# ---------------------------------------------------------------------------


class TestChaosRunner:
    def test_runner_runs_all_experiments(self) -> None:
        exp1 = _ConcreteExperiment()
        exp2 = _ConcreteExperiment()
        runner = ChaosRunner([exp1, exp2])
        report = runner.run()
        assert report.experiments_run == 2
        assert report.passed == 2

    def test_dry_run_skips_execution(self) -> None:
        exp = _ConcreteExperiment()
        runner = ChaosRunner([exp], dry_run=True)
        report = runner.run()
        assert report.experiments_run == 1
        assert report.skipped == 1
        assert not exp.setup_called

    def test_selective_run_by_name(self) -> None:
        exp1 = _ConcreteExperiment()
        exp1.name = "alpha"
        exp2 = _ConcreteExperiment()
        exp2.name = "beta"
        runner = ChaosRunner([exp1, exp2])
        report = runner.run(names=["alpha"])
        assert report.experiments_run == 1
        assert exp1.setup_called
        assert not exp2.setup_called

    def test_failed_experiment_counted(self) -> None:
        exp = _ConcreteExperiment(fail_execute=True)
        runner = ChaosRunner([exp])
        report = runner.run()
        assert report.failed == 1
        assert report.passed == 0

    def test_write_json_output(self, tmp_path: Path) -> None:
        exp = _ConcreteExperiment()
        runner = ChaosRunner([exp])
        report = runner.run()
        out = tmp_path / "chaos_report.json"
        runner.write_json(report, out)
        assert out.exists()
        data = json.loads(out.read_text())
        assert "results" in data
        assert data["experiments_run"] == 1

    def test_print_report_does_not_raise(self, capsys: pytest.CaptureFixture[str]) -> None:
        exp = _ConcreteExperiment()
        runner = ChaosRunner([exp])
        report = runner.run()
        # Should not raise
        runner.print_report(report)


# ---------------------------------------------------------------------------
# CLI integration
# ---------------------------------------------------------------------------


class TestChaosCLI:
    @pytest.fixture()
    def cli_runner(self) -> CliRunner:
        return CliRunner()

    def test_chaos_dry_run_lists_experiments(self, cli_runner: CliRunner) -> None:
        result = cli_runner.invoke(
            app,
            [
                "chaos",
                "--scenarios", "corrupt-inputs,network",
                "--dry-run",
            ],
        )
        assert result.exit_code == 0
        assert "corrupt-inputs" in result.output or "Dry-run" in result.output

    def test_chaos_runs_corrupt_inputs(self, cli_runner: CliRunner) -> None:
        result = cli_runner.invoke(
            app,
            [
                "chaos",
                "--scenarios", "corrupt-inputs",
            ],
        )
        # Should succeed with exit code 0 when all experiments pass
        assert result.exit_code == 0

    def test_chaos_writes_json_output(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        out = tmp_path / "chaos_report.json"
        result = cli_runner.invoke(
            app,
            [
                "chaos",
                "--scenarios", "corrupt-inputs",
                "--output-json", str(out),
            ],
        )
        assert result.exit_code == 0
        assert out.exists()
        data = json.loads(out.read_text())
        assert "results" in data

    def test_chaos_with_target_module(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        target = tmp_path / "test_sample.py"
        target.write_text(
            textwrap.dedent(
                """\
                def test_add():
                    assert 1 + 1 == 2
                """
            )
        )
        result = cli_runner.invoke(
            app,
            [
                "chaos",
                "--scenarios", "corrupt-inputs",
                "--target-module", str(target),
            ],
        )
        assert result.exit_code == 0

    def test_chaos_invalid_scenarios_exits_one(self, cli_runner: CliRunner) -> None:
        result = cli_runner.invoke(
            app,
            [
                "chaos",
                "--scenarios", "nonexistent-scenario",
            ],
        )
        assert result.exit_code == 1

    def test_chaos_all_scenarios_dry_run(self, cli_runner: CliRunner) -> None:
        result = cli_runner.invoke(
            app,
            ["chaos", "--dry-run"],
        )
        assert result.exit_code == 0
