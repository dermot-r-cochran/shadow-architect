"""Azure DevOps integration.

Publishes meta-testing results as test runs and work items to an Azure
DevOps project, enabling traceability between the meta-testing analysis
and the project's test plans.

When ``SHADOW_ARCHITECT_MOCK_AZURE=1`` the module uses in-memory stubs.
"""

from __future__ import annotations

import os
from typing import Any

from shadow_architect.azure.client import AzureClientError
from shadow_architect.core.models import Severity
from shadow_architect.core.reporter import TestReport


class DevOpsClient:
    """Thin client for Azure DevOps test plan and work item operations.

    Args:
        organization_url: Azure DevOps organisation URL, e.g.
            ``https://dev.azure.com/myorg``.  Falls back to the
            ``AZURE_DEVOPS_ORG_URL`` environment variable.
        project: Azure DevOps project name.  Falls back to
            ``AZURE_DEVOPS_PROJECT``.
        personal_access_token: PAT for authentication.  Falls back to
            ``AZURE_DEVOPS_PAT``.
        use_mock: Force mock mode without setting environment variables.
    """

    def __init__(
        self,
        organization_url: str | None = None,
        project: str | None = None,
        personal_access_token: str | None = None,
        use_mock: bool | None = None,
    ) -> None:
        self._org_url = organization_url or os.environ.get(
            "AZURE_DEVOPS_ORG_URL", ""
        )
        self._project = project or os.environ.get("AZURE_DEVOPS_PROJECT", "")
        self._pat = personal_access_token or os.environ.get(
            "AZURE_DEVOPS_PAT", ""
        )
        _use_mock = use_mock if use_mock is not None else (
            os.environ.get("SHADOW_ARCHITECT_MOCK_AZURE", "0") == "1"
        )
        if _use_mock:
            self._client: Any = _MockDevOpsConnection()
        else:
            self._client = self._build_real_client()

    def publish_test_run(self, report: TestReport) -> dict[str, Any]:
        """Create a test run entry in Azure DevOps Test Plans.

        Returns the created test run's metadata.
        """
        test_client = self._client.get_client(
            "azure.devops.v7_1.test.test_client.TestClient"
        )
        run_model = {
            "name": f"shadow-architect: {report.suite_name}",
            "build": None,
            "is_automated": True,
            "plan": None,
            "point_ids": None,
        }
        run = test_client.create_test_run(run_model, project=self._project)
        return dict(run) if isinstance(run, dict) else {"id": run.id, "name": run.name}

    def create_work_items_for_findings(
        self, report: TestReport
    ) -> list[dict[str, Any]]:
        """Create Azure DevOps work items (Bugs) for HIGH/CRITICAL findings.

        Returns a list of created work item metadata dicts.
        """
        if report.validation is None:
            return []

        work_item_client = self._client.get_client(
            "azure.devops.v7_1.work_item_tracking."
            "work_item_tracking_client.WorkItemTrackingClient"
        )
        created: list[dict[str, Any]] = []
        for finding in report.validation.findings:
            if finding.severity not in (Severity.CRITICAL, Severity.HIGH):
                continue
            patch = [
                {
                    "op": "add",
                    "path": "/fields/System.Title",
                    "value": f"[shadow-architect] {finding.title}",
                },
                {
                    "op": "add",
                    "path": "/fields/System.Description",
                    "value": finding.description,
                },
                {
                    "op": "add",
                    "path": "/fields/Microsoft.VSTS.Common.Priority",
                    "value": 1 if finding.severity == Severity.CRITICAL else 2,
                },
            ]
            item = work_item_client.create_work_item(
                document=patch, project=self._project, type="Bug"
            )
            created.append(
                dict(item)
                if isinstance(item, dict)
                else {"id": item.id, "title": item.fields.get("System.Title", "")}
            )
        return created

    # ------------------------------------------------------------------

    def _build_real_client(self) -> Any:
        if not self._org_url or not self._pat:
            raise AzureClientError(
                "Azure DevOps organisation URL and PAT must be set. "
                "Provide them directly or via AZURE_DEVOPS_ORG_URL and "
                "AZURE_DEVOPS_PAT environment variables."
            )
        try:
            from azure.devops.connection import Connection
            from msrest.authentication import BasicAuthentication

            credentials = BasicAuthentication("", self._pat)
            return Connection(base_url=self._org_url, creds=credentials)
        except ImportError as exc:
            raise AzureClientError(
                "azure-devops is not installed. "
                "Run: pip install azure-devops"
            ) from exc


class _MockDevOpsConnection:
    """Minimal stub for :class:`azure.devops.connection.Connection`."""

    def __init__(self) -> None:
        self._test_runs: list[dict[str, Any]] = []
        self._work_items: list[dict[str, Any]] = []

    def get_client(self, client_path: str) -> _MockDevOpsServiceClient:  # noqa: ARG002
        return _MockDevOpsServiceClient(self._test_runs, self._work_items)


class _MockDevOpsServiceClient:
    def __init__(
        self,
        test_runs: list[dict[str, Any]],
        work_items: list[dict[str, Any]],
    ) -> None:
        self._test_runs = test_runs
        self._work_items = work_items

    def create_test_run(
        self, run_model: dict[str, Any], project: str = ""  # noqa: ARG002
    ) -> dict[str, Any]:
        run = {**run_model, "id": len(self._test_runs) + 1}
        self._test_runs.append(run)
        return run

    def create_work_item(
        self,
        document: list[dict[str, Any]],
        project: str = "",  # noqa: ARG002
        type: str = "Bug",  # noqa: ARG002
    ) -> dict[str, Any]:
        fields = {
            entry["path"].split("/")[-1]: entry["value"]
            for entry in document
            if entry.get("op") == "add"
        }
        item = {"id": len(self._work_items) + 1, "fields": fields}
        self._work_items.append(item)
        return item
