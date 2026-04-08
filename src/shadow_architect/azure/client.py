"""Azure client base module.

Provides a thin wrapper around Azure Identity for obtaining credentials.
All Azure service clients in this package use this module to acquire
:class:`azure.identity.DefaultAzureCredential` or token credentials.

The module is designed to be testable without live Azure credentials – when
``SHADOW_ARCHITECT_MOCK_AZURE`` environment variable is set to ``1`` it
returns a stub credential object.
"""

from __future__ import annotations

import os
from typing import Any


class AzureClientError(Exception):
    """Raised when an Azure client operation fails."""


def get_credential(
    *, tenant_id: str | None = None, use_mock: bool | None = None
) -> Any:
    """Return an Azure credential object.

    In a real deployment this returns
    :class:`azure.identity.DefaultAzureCredential`.  When
    ``SHADOW_ARCHITECT_MOCK_AZURE=1`` (or *use_mock* is ``True``) it returns a
    lightweight stub so that the rest of the framework can be exercised without
    live Azure access.

    Args:
        tenant_id: Optional Azure tenant ID to pass to
            :class:`~azure.identity.DefaultAzureCredential`.
        use_mock: Override environment variable detection.  When ``None`` the
            value of ``SHADOW_ARCHITECT_MOCK_AZURE`` is used.

    Returns:
        An Azure credential compatible object.

    Raises:
        AzureClientError: When the ``azure-identity`` package is not installed
            and mock mode is not requested.
    """
    _use_mock = use_mock if use_mock is not None else (
        os.environ.get("SHADOW_ARCHITECT_MOCK_AZURE", "0") == "1"
    )
    if _use_mock:
        return _MockCredential()

    try:
        from azure.identity import DefaultAzureCredential

        kwargs: dict[str, Any] = {}
        if tenant_id:
            kwargs["tenant_id"] = tenant_id
        return DefaultAzureCredential(**kwargs)
    except ImportError as exc:
        raise AzureClientError(
            "azure-identity is not installed. "
            "Run: pip install azure-identity"
        ) from exc


class _MockCredential:
    """Stub credential used in tests and CI environments without Azure access."""

    def get_token(self, *scopes: str, **kwargs: Any) -> Any:  # noqa: ARG002
        return _MockAccessToken()


class _MockAccessToken:
    token: str = "mock-token"
    expires_on: int = 9_999_999_999
