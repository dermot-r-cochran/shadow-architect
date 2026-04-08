"""Azure Blob Storage integration.

Uploads test reports to Azure Blob Storage and retrieves previous reports
for trend analysis.

When ``SHADOW_ARCHITECT_MOCK_AZURE=1`` the module operates against an
in-memory stub so the framework can be exercised without live Azure
credentials.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from io import BytesIO
from typing import Any

from shadow_architect.azure.client import AzureClientError, get_credential
from shadow_architect.core.reporter import TestReport


class StorageClient:
    """Manages report persistence in Azure Blob Storage.

    Args:
        account_url: Full Azure Storage account URL, e.g.
            ``https://<account>.blob.core.windows.net``.  When ``None`` the
            value of the ``AZURE_STORAGE_ACCOUNT_URL`` environment variable is
            used.
        container_name: Blob container name.  Defaults to
            ``shadow-architect-reports``.
        use_mock: When ``True`` (or ``SHADOW_ARCHITECT_MOCK_AZURE=1``) use the
            in-memory stub instead of the real Azure SDK.
    """

    _DEFAULT_CONTAINER = "shadow-architect-reports"

    def __init__(
        self,
        account_url: str | None = None,
        container_name: str = _DEFAULT_CONTAINER,
        use_mock: bool | None = None,
    ) -> None:
        self._account_url = account_url or os.environ.get(
            "AZURE_STORAGE_ACCOUNT_URL", ""
        )
        self._container_name = container_name
        _use_mock = use_mock if use_mock is not None else (
            os.environ.get("SHADOW_ARCHITECT_MOCK_AZURE", "0") == "1"
        )
        if _use_mock:
            self._client: Any = _MockBlobContainerClient()
        else:
            self._client = self._build_real_client()

    def upload_report(self, report: TestReport) -> str:
        """Upload *report* as a JSON blob and return the blob name.

        The blob is named ``<suite>/<timestamp>.json`` so that reports are
        naturally ordered by time within a suite prefix.
        """
        timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        safe_name = report.suite_name.replace(" ", "_").replace("/", "-")
        blob_name = f"{safe_name}/{timestamp}.json"

        data = json.dumps(report.to_dict(), indent=2, default=str).encode("utf-8")
        self._client.upload_blob(name=blob_name, data=BytesIO(data), overwrite=True)
        return blob_name

    def list_reports(self, suite_name: str | None = None) -> list[str]:
        """Return a list of blob names, optionally filtered by *suite_name*."""
        prefix = (
            suite_name.replace(" ", "_").replace("/", "-") + "/"
            if suite_name
            else None
        )
        blobs = self._client.list_blobs(name_starts_with=prefix)
        return [b["name"] if isinstance(b, dict) else b.name for b in blobs]

    def download_report(self, blob_name: str) -> dict[str, Any]:
        """Download and deserialise a report blob."""
        data = self._client.download_blob(blob_name).readall()
        return json.loads(data.decode("utf-8"))  # type: ignore[no-any-return]

    # ------------------------------------------------------------------

    def _build_real_client(self) -> Any:
        if not self._account_url:
            raise AzureClientError(
                "Azure Storage account URL not set. "
                "Provide account_url or set AZURE_STORAGE_ACCOUNT_URL."
            )
        try:
            from azure.storage.blob import ContainerClient

            credential = get_credential()
            return ContainerClient(
                account_url=self._account_url,
                container_name=self._container_name,
                credential=credential,
            )
        except ImportError as exc:
            raise AzureClientError(
                "azure-storage-blob is not installed. "
                "Run: pip install azure-storage-blob"
            ) from exc


class _MockBlobContainerClient:
    """In-memory stub for :class:`azure.storage.blob.ContainerClient`."""

    def __init__(self) -> None:
        self._store: dict[str, bytes] = {}

    def upload_blob(self, name: str, data: Any, overwrite: bool = False) -> None:  # noqa: ARG002
        self._store[name] = data.read() if hasattr(data, "read") else data

    def list_blobs(self, name_starts_with: str | None = None) -> list[dict[str, str]]:
        return [
            {"name": n}
            for n in self._store
            if name_starts_with is None or n.startswith(name_starts_with)
        ]

    def download_blob(self, blob_name: str) -> _MockDownloadStream:
        return _MockDownloadStream(self._store.get(blob_name, b"{}"))


class _MockDownloadStream:
    def __init__(self, data: bytes) -> None:
        self._data = data

    def readall(self) -> bytes:
        return self._data
