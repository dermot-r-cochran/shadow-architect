"""Tests for shadow_architect.azure modules."""

from __future__ import annotations

import json
import os
import textwrap

import pytest

from shadow_architect.azure.client import _MockCredential, get_credential
from shadow_architect.azure.storage import StorageClient
from shadow_architect.azure.devops import DevOpsClient
from shadow_architect.core.models import Severity, TestSuite
from shadow_architect.core.reporter import TestReport


# ---------------------------------------------------------------------------
# AzureClient
# ---------------------------------------------------------------------------


class TestGetCredential:
    def test_returns_mock_when_env_set(self, monkeypatch):
        monkeypatch.setenv("SHADOW_ARCHITECT_MOCK_AZURE", "1")
        cred = get_credential()
        assert isinstance(cred, _MockCredential)

    def test_mock_credential_has_get_token(self):
        cred = _MockCredential()
        token = cred.get_token("https://storage.azure.com/.default")
        assert token.token == "mock-token"

    def test_use_mock_override(self):
        cred = get_credential(use_mock=True)
        assert isinstance(cred, _MockCredential)


# ---------------------------------------------------------------------------
# StorageClient
# ---------------------------------------------------------------------------


@pytest.fixture()
def storage_client():
    return StorageClient(use_mock=True)


@pytest.fixture()
def sample_report():
    return TestReport(
        suite_name="Azure Test Suite",
        product="Demo",
        use_case="Testing",
    )


class TestStorageClient:
    def test_upload_report_returns_blob_name(self, storage_client, sample_report):
        blob_name = storage_client.upload_report(sample_report)
        assert blob_name.startswith("Azure_Test_Suite/")
        assert blob_name.endswith(".json")

    def test_list_reports_returns_uploaded(self, storage_client, sample_report):
        storage_client.upload_report(sample_report)
        blobs = storage_client.list_reports()
        assert len(blobs) >= 1

    def test_list_reports_filtered_by_suite(self, storage_client, sample_report):
        storage_client.upload_report(sample_report)
        other = TestReport(suite_name="Other Suite", product="X", use_case="Y")
        storage_client.upload_report(other)

        azure_blobs = storage_client.list_reports(suite_name="Azure Test Suite")
        other_blobs = storage_client.list_reports(suite_name="Other Suite")
        assert all("Azure_Test_Suite" in b for b in azure_blobs)
        assert all("Other_Suite" in b for b in other_blobs)

    def test_download_report_roundtrip(self, storage_client, sample_report):
        blob_name = storage_client.upload_report(sample_report)
        data = storage_client.download_report(blob_name)
        assert data["suite_name"] == "Azure Test Suite"


# ---------------------------------------------------------------------------
# DevOpsClient
# ---------------------------------------------------------------------------


@pytest.fixture()
def devops_client():
    return DevOpsClient(use_mock=True)


@pytest.fixture()
def report_with_findings(tmp_path):
    from shadow_architect.core.analyzer import TestStrategyAnalyzer
    from shadow_architect.core.improver import TestImprover
    from shadow_architect.core.reporter import TestReporter
    from shadow_architect.core.validator import TestValidator

    f = tmp_path / "test_service.py"
    f.write_text("def test_placeholder():\n    assert True\n")
    suite = TestSuite(
        name="DevOps Suite",
        product="Demo Service",
        use_case="API",
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


class TestDevOpsClient:
    def test_publish_test_run_returns_dict(
        self, devops_client, report_with_findings
    ):
        run = devops_client.publish_test_run(report_with_findings)
        assert isinstance(run, dict)
        assert "id" in run

    def test_create_work_items_for_high_findings(
        self, devops_client, report_with_findings
    ):
        items = devops_client.create_work_items_for_findings(report_with_findings)
        # There should be at least some HIGH findings from missing test types
        assert isinstance(items, list)

    def test_no_work_items_when_no_validation(self, devops_client):
        report = TestReport(suite_name="X", product="Y", use_case="Z")
        items = devops_client.create_work_items_for_findings(report)
        assert items == []
