"""Tests for shadow_architect.azure modules."""

from __future__ import annotations

import pytest

from shadow_architect.azure.client import _MockCredential, get_credential
from shadow_architect.azure.devops import DevOpsClient
from shadow_architect.azure.storage import StorageClient
from shadow_architect.core.models import Finding, Severity, TestSuite
from shadow_architect.core.reporter import TestReport
from shadow_architect.core.validator import ValidationResult

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

    def test_upload_report_keeps_the_findings(self, storage_client, report_with_findings):
        blob_name = storage_client.upload_report(report_with_findings)
        data = storage_client.download_report(blob_name)
        assert data == report_with_findings.to_dict()
        assert data["validation"]["findings"]

    def test_upload_report_data_stores_the_dictionary_as_given(self, storage_client):
        report = {
            "suite_name": "As Written",
            "overall_score": 41.5,
            "validation": {"findings": [{"id": "has-tests", "severity": "critical"}]},
        }
        blob_name = storage_client.upload_report_data("Blob Name", report)
        assert blob_name.startswith("Blob_Name/")
        assert storage_client.download_report(blob_name) == report


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


def _finding(title: str, severity: Severity) -> Finding:
    return Finding(
        id=title.lower().replace(" ", "-"),
        title=title,
        description=f"{title}, described.",
        severity=severity,
        category="coverage",
    )


def _report_with(findings: list[Finding]) -> TestReport:
    """A report whose validator raised exactly *findings*.

    It carries no analysis, so the tests that use it say nothing on whether a
    finding raised by the analyzer or an evaluator alone should become a work
    item too: today it does not, and that is not yet decided.
    """
    return TestReport(
        suite_name="DevOps Suite",
        product="Demo Service",
        use_case="API",
        validation=ValidationResult(passed=False, score=0.0, findings=findings),
    )


@pytest.fixture()
def work_item_calls(monkeypatch) -> list[dict]:
    """Every ``create_work_item`` call the in-memory stub is handed.

    The stub ignores the work item type and the project, so what the client
    asked for is read here. The recorder has no defaults of its own: an
    argument the client leaves out is recorded as ``None``.
    """
    from shadow_architect.azure import devops

    calls: list[dict] = []
    create_work_item = devops._MockDevOpsServiceClient.create_work_item

    def recording(self, document, project=None, type=None):
        calls.append({"document": document, "project": project, "type": type})
        return create_work_item(self, document)

    monkeypatch.setattr(devops._MockDevOpsServiceClient, "create_work_item", recording)
    return calls


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
        # A real run: one test, an API product and no security test, so the
        # validator raises one HIGH finding beside a MEDIUM one. This test
        # once asserted only that a list came back, which an empty list met.
        findings = report_with_findings.validation.findings
        assert {f.id: f.severity for f in findings} == {
            "integration-tests-present": Severity.MEDIUM,
            "security-tests-present": Severity.HIGH,
        }
        (security,) = [f for f in findings if f.severity is Severity.HIGH]

        items = devops_client.create_work_items_for_findings(report_with_findings)

        assert [item["fields"] for item in items] == [
            {
                "System.Title": f"[shadow-architect] {security.title}",
                "System.Description": security.description,
                "Microsoft.VSTS.Common.Priority": 2,
            }
        ]

    def test_one_bug_per_high_or_critical_finding(self, devops_client):
        report = _report_with(
            [
                _finding("Medium gap", Severity.MEDIUM),
                _finding("High gap", Severity.HIGH),
                _finding("Info note", Severity.INFO),
                _finding("Critical gap", Severity.CRITICAL),
                _finding("Low gap", Severity.LOW),
            ]
        )

        items = devops_client.create_work_items_for_findings(report)

        # One per HIGH or CRITICAL finding, in the report's order, none for
        # the rest; CRITICAL is priority 1 and HIGH priority 2.
        assert [item["fields"] for item in items] == [
            {
                "System.Title": "[shadow-architect] High gap",
                "System.Description": "High gap, described.",
                "Microsoft.VSTS.Common.Priority": 2,
            },
            {
                "System.Title": "[shadow-architect] Critical gap",
                "System.Description": "Critical gap, described.",
                "Microsoft.VSTS.Common.Priority": 1,
            },
        ]

    def test_work_items_are_bugs_in_the_configured_project(self, work_item_calls):
        client = DevOpsClient(project="Guardrails", use_mock=True)

        client.create_work_items_for_findings(
            _report_with([_finding("High gap", Severity.HIGH)])
        )

        assert [(call["type"], call["project"]) for call in work_item_calls] == [
            ("Bug", "Guardrails")
        ]

    def test_no_work_items_when_no_validation(self, devops_client):
        report = TestReport(suite_name="X", product="Y", use_case="Z")
        items = devops_client.create_work_items_for_findings(report)
        assert items == []
