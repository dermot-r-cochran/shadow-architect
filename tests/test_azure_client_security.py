"""Credential-boundary tests for shadow_architect.azure.client.

The security boundary of ``get_credential``: secrets are never passed through
shadow-architect's own arguments (the Azure SDK reads them from its own
environment), nothing the module raises, prints or logs repeats one, a
missing or invalid credential surfaces as an error rather than a silent
fallback to the stub, and only the exact opt-in ``SHADOW_ARCHITECT_MOCK_AZURE=1``
selects the stub.

No test needs real credentials or the network: ``azure.identity`` is replaced
in ``sys.modules`` by a fake whose ``DefaultAzureCredential`` records how it
was built.
"""

from __future__ import annotations

import logging
import sys
import types
from typing import Any

import pytest

from shadow_architect.azure.client import (
    AzureClientError,
    _MockCredential,
    get_credential,
)

SECRET = "s3cr3t-client-secret-value"


class _AuthError(Exception):
    """Stands in for azure.core.exceptions.ClientAuthenticationError."""


class _FakeDefaultAzureCredential:
    """Records its keyword arguments; ``get_token`` fails as Azure does when
    no credential in the chain is available."""

    instances: list[_FakeDefaultAzureCredential] = []

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs
        _FakeDefaultAzureCredential.instances.append(self)

    def get_token(self, *scopes: str, **kwargs: Any) -> Any:  # noqa: ARG002
        raise _AuthError("DefaultAzureCredential failed to retrieve a token")


@pytest.fixture()
def fake_identity(monkeypatch: pytest.MonkeyPatch) -> type[_FakeDefaultAzureCredential]:
    _FakeDefaultAzureCredential.instances = []
    module = types.ModuleType("azure.identity")
    module.DefaultAzureCredential = _FakeDefaultAzureCredential  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "azure.identity", module)
    monkeypatch.delenv("SHADOW_ARCHITECT_MOCK_AZURE", raising=False)
    return _FakeDefaultAzureCredential


@pytest.fixture()
def secret_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """The environment a service principal leaves for the Azure SDK."""
    monkeypatch.setenv("AZURE_CLIENT_ID", "00000000-0000-0000-0000-000000000000")
    monkeypatch.setenv("AZURE_TENANT_ID", "11111111-1111-1111-1111-111111111111")
    monkeypatch.setenv("AZURE_CLIENT_SECRET", SECRET)


class TestSecretsAreNotTaken:
    def test_no_secret_is_passed_to_the_sdk(self, fake_identity, secret_env):
        cred = get_credential()
        assert isinstance(cred, fake_identity)
        # The SDK reads AZURE_CLIENT_SECRET itself; shadow-architect hands on nothing.
        assert cred.kwargs == {}

    def test_only_the_tenant_id_is_passed(self, fake_identity, secret_env):
        cred = get_credential(tenant_id="22222222-2222-2222-2222-222222222222")
        assert cred.kwargs == {"tenant_id": "22222222-2222-2222-2222-222222222222"}

    def test_empty_tenant_id_is_not_passed(self, fake_identity):
        assert get_credential(tenant_id="").kwargs == {}


class TestSecretsAreNotEchoed:
    def test_nothing_printed_or_logged_on_the_real_path(
        self, fake_identity, secret_env, capsys, caplog
    ):
        caplog.set_level(logging.DEBUG)
        cred = get_credential(tenant_id="t")
        with pytest.raises(_AuthError) as exc_info:
            cred.get_token("https://storage.azure.com/.default")
        captured = capsys.readouterr()
        assert SECRET not in captured.out + captured.err
        assert SECRET not in caplog.text
        assert SECRET not in str(exc_info.value)

    def test_missing_sdk_error_does_not_echo_the_secret(
        self, monkeypatch, secret_env, capsys, caplog
    ):
        caplog.set_level(logging.DEBUG)
        monkeypatch.delenv("SHADOW_ARCHITECT_MOCK_AZURE", raising=False)
        # None in sys.modules makes the import raise ImportError.
        monkeypatch.setitem(sys.modules, "azure.identity", None)
        with pytest.raises(AzureClientError) as exc_info:
            get_credential()
        assert "pip install azure-identity" in str(exc_info.value)
        assert isinstance(exc_info.value.__cause__, ImportError)
        captured = capsys.readouterr()
        for text in (str(exc_info.value), captured.out, captured.err, caplog.text):
            assert SECRET not in text

    def test_stub_token_is_not_taken_from_the_environment(self, secret_env):
        token = get_credential(use_mock=True).get_token("scope")
        assert token.token == "mock-token"
        assert SECRET not in token.token


class TestMissingOrInvalidCredentialsSurface:
    def test_missing_credentials_fail_at_token_time_not_silently(self, fake_identity):
        # With no mock opt-in, a chain with no credential is not swapped for
        # the stub: the failure reaches the caller.
        cred = get_credential()
        assert not isinstance(cred, _MockCredential)
        with pytest.raises(_AuthError):
            cred.get_token("https://storage.azure.com/.default")

    def test_invalid_credential_configuration_propagates(self, monkeypatch, fake_identity):
        def _reject(**kwargs: Any) -> Any:
            raise ValueError("Invalid tenant ID provided")

        monkeypatch.setattr(sys.modules["azure.identity"], "DefaultAzureCredential", _reject)
        # Raised as itself: not swallowed, and not relabelled as a missing package.
        with pytest.raises(ValueError, match="Invalid tenant ID"):
            get_credential(tenant_id="not a tenant")


class TestStubNeedsTheExactOptIn:
    @pytest.mark.parametrize("flag", ["", "0", "true", "yes", "on", " 1", "1 "])
    def test_anything_but_one_uses_the_real_credential(self, monkeypatch, fake_identity, flag):
        monkeypatch.setenv("SHADOW_ARCHITECT_MOCK_AZURE", flag)
        assert isinstance(get_credential(), fake_identity)

    def test_explicit_use_mock_false_overrides_the_environment(
        self, monkeypatch, fake_identity
    ):
        monkeypatch.setenv("SHADOW_ARCHITECT_MOCK_AZURE", "1")
        assert isinstance(get_credential(use_mock=False), fake_identity)
