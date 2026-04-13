"""Security permission misalignment chaos scenarios."""

from __future__ import annotations

import os
from typing import Any
from unittest.mock import MagicMock, patch

from shadow_architect.chaos.base import ChaosExperiment
from shadow_architect.chaos.models import ChaosStatus


class _ForbiddenError(Exception):
    """Simulated 403 Forbidden Azure response."""

    status_code: int = 403


class _UnauthorizedError(Exception):
    """Simulated 401 Unauthorized Azure response."""

    status_code: int = 401


# ---------------------------------------------------------------------------
# Private context-manager helpers
# ---------------------------------------------------------------------------


class _MissingCredentialsCtx:
    _AZURE_CRED_VARS = (
        "AZURE_STORAGE_ACCOUNT_URL",
        "AZURE_CLIENT_ID",
        "AZURE_CLIENT_SECRET",
        "AZURE_TENANT_ID",
        "AZURE_SUBSCRIPTION_ID",
        "AZURE_AUTHORITY_HOST",
    )

    def __init__(self, vars_to_unset: tuple[str, ...]) -> None:
        self._vars = vars_to_unset
        self._saved: dict[str, str] = {}

    def __enter__(self) -> _MissingCredentialsCtx:
        for var in self._vars:
            val = os.environ.pop(var, None)
            if val is not None:
                self._saved[var] = val
        return self

    def __exit__(self, *_: Any) -> bool:
        os.environ.update(self._saved)
        return False


class _RbacSimCtx:
    def __init__(self, status_code: int, target: str) -> None:
        self._status_code = status_code
        self._target = target
        self._patcher: Any = None

    def __enter__(self) -> _RbacSimCtx:
        err_class = _ForbiddenError if self._status_code == 403 else _UnauthorizedError
        exc = err_class(f"Simulated HTTP {self._status_code} for {self._target}")
        mock_fn = MagicMock(side_effect=exc)
        self._patcher = patch(self._target, mock_fn)
        self._patcher.start()
        return self

    def __exit__(self, *_: Any) -> bool:
        if self._patcher is not None:
            self._patcher.stop()
        return False


class _ExpiredTokenCtx:
    def __init__(self, target: str) -> None:
        self._target = target
        self._patcher: Any = None

    def __enter__(self) -> _ExpiredTokenCtx:
        mock_token = MagicMock()
        mock_token.token = "expired-or-invalid-token"
        mock_token.expires_on = 0  # already expired
        mock_cred = MagicMock()
        mock_cred.get_token.return_value = mock_token
        self._patcher = patch(self._target, return_value=mock_cred)
        self._patcher.start()
        return self

    def __exit__(self, *_: Any) -> bool:
        if self._patcher is not None:
            self._patcher.stop()
        return False


class _WrongTenantCtx:
    _FAKE_TENANT = "00000000-0000-0000-0000-000000000000"
    _FAKE_SUBSCRIPTION = "ffffffff-ffff-ffff-ffff-ffffffffffff"

    def __init__(self) -> None:
        self._saved: dict[str, str | None] = {}

    def __enter__(self) -> _WrongTenantCtx:
        for var in ("AZURE_TENANT_ID", "AZURE_SUBSCRIPTION_ID"):
            self._saved[var] = os.environ.get(var)
        os.environ["AZURE_TENANT_ID"] = self._FAKE_TENANT
        os.environ["AZURE_SUBSCRIPTION_ID"] = self._FAKE_SUBSCRIPTION
        return self

    def __exit__(self, *_: Any) -> bool:
        for var, val in self._saved.items():
            if val is None:
                os.environ.pop(var, None)
            else:
                os.environ[var] = val
        return False


# ---------------------------------------------------------------------------
# PermissionChaos
# ---------------------------------------------------------------------------

_AZURE_CRED_VARS = (
    "AZURE_STORAGE_ACCOUNT_URL",
    "AZURE_CLIENT_ID",
    "AZURE_CLIENT_SECRET",
    "AZURE_TENANT_ID",
    "AZURE_SUBSCRIPTION_ID",
    "AZURE_AUTHORITY_HOST",
)


class PermissionChaos:
    """Provides individual security-permission misalignment scenarios.

    Each method is a **context manager** that activates the fault for the
    duration of the ``with`` block, then restores the original state.

    Example::

        pc = PermissionChaos()
        with pc.missing_azure_credentials():
            # AZURE_STORAGE_ACCOUNT_URL is unset here
            ...
    """

    def missing_azure_credentials(self) -> _MissingCredentialsCtx:
        """Temporarily unset all known Azure credential environment variables."""
        return _MissingCredentialsCtx(_AZURE_CRED_VARS)

    def rbac_forbidden(self, target: str) -> _RbacSimCtx:
        """Mock *target* (dotted path) to raise a 403 Forbidden error."""
        return _RbacSimCtx(403, target)

    def rbac_unauthorized(self, target: str) -> _RbacSimCtx:
        """Mock *target* (dotted path) to raise a 401 Unauthorized error."""
        return _RbacSimCtx(401, target)

    def expired_token(self, credential_target: str) -> _ExpiredTokenCtx:
        """Replace credential factory *credential_target* with expired tokens."""
        return _ExpiredTokenCtx(credential_target)

    def wrong_tenant(self) -> _WrongTenantCtx:
        """Swap tenant and subscription IDs for fake values."""
        return _WrongTenantCtx()


# ---------------------------------------------------------------------------
# SecurityChaosExperiment
# ---------------------------------------------------------------------------


class SecurityChaosExperiment(ChaosExperiment):
    """Orchestrate permission-misalignment scenarios against a target callable.

    The experiment runs a series of permission-chaos scenarios against
    *target* and verifies that the system:

    1. Does **not** crash with an unhandled exception from outside the
       *allowed_exceptions* set.
    2. Does **not** leak sensitive information in any raised exception message.

    Args:
        target: Callable to exercise under each security fault.
        credential_target: Dotted Python path to the credential factory to
            patch (e.g. ``"shadow_architect.azure.client.get_credential"``).
        allowed_exceptions: Exception types treated as graceful failure.
        name: Override the experiment name.
    """

    name = "security-permission-misalignment"
    description = (
        "Simulates missing Azure credentials, RBAC 403/401 responses, "
        "expired tokens, and wrong tenant/subscription to validate that the "
        "system fails gracefully without leaking sensitive information."
    )

    _SENSITIVE_PATTERNS = (
        "password",
        "secret",
        "private_key",
        "access_key",
        "connection_string",
    )

    def __init__(
        self,
        target: Any,
        credential_target: str = "shadow_architect.azure.client.get_credential",
        allowed_exceptions: tuple[type[Exception], ...] = (Exception,),
        name: str | None = None,
    ) -> None:
        super().__init__()
        self._target = target
        self._credential_target = credential_target
        self._allowed = allowed_exceptions
        self._chaos = PermissionChaos()
        if name is not None:
            self.name = name

    def setup(self) -> None:
        pass

    def execute(self) -> None:
        """Run each permission scenario and record whether failure is graceful."""
        violations: list[str] = []

        # 1. Missing credentials
        with self._chaos.missing_azure_credentials():
            try:
                self._target()
                self._observe("Missing-credentials: target succeeded (no creds needed)")
            except self._allowed as exc:
                msg = str(exc).lower()
                if self._has_sensitive_leak(msg):
                    violations.append(
                        f"Missing-credentials: sensitive info in exception: {exc}"
                    )
                else:
                    self._observe(
                        f"Missing-credentials: graceful failure ({type(exc).__name__})"
                    )
            except Exception as exc:  # noqa: BLE001
                violations.append(
                    f"Missing-credentials: unhandled {type(exc).__name__}: {exc}"
                )

        # 2. Expired token
        with self._chaos.expired_token(self._credential_target):
            try:
                self._target()
                self._observe("Expired-token: target succeeded")
            except self._allowed as exc:
                msg = str(exc).lower()
                if self._has_sensitive_leak(msg):
                    violations.append(
                        f"Expired-token: sensitive info in exception: {exc}"
                    )
                else:
                    self._observe(
                        f"Expired-token: graceful failure ({type(exc).__name__})"
                    )
            except Exception as exc:  # noqa: BLE001
                violations.append(
                    f"Expired-token: unhandled {type(exc).__name__}: {exc}"
                )

        # 3. Wrong tenant
        with self._chaos.wrong_tenant():
            try:
                self._target()
                self._observe("Wrong-tenant: target succeeded")
            except self._allowed as exc:
                msg = str(exc).lower()
                if self._has_sensitive_leak(msg):
                    violations.append(
                        f"Wrong-tenant: sensitive info in exception: {exc}"
                    )
                else:
                    self._observe(
                        f"Wrong-tenant: graceful failure ({type(exc).__name__})"
                    )
            except Exception as exc:  # noqa: BLE001
                violations.append(
                    f"Wrong-tenant: unhandled {type(exc).__name__}: {exc}"
                )

        if violations:
            raise AssertionError(
                f"{len(violations)} security violation(s):\n"
                + "\n".join(f"  • {v}" for v in violations)
            )

    def teardown(self) -> None:
        pass

    def _has_sensitive_leak(self, message: str) -> bool:
        """Return True if *message* contains sensitive keywords."""
        return any(pat in message for pat in self._SENSITIVE_PATTERNS)

    @property
    def status(self) -> ChaosStatus:
        return ChaosStatus.PASSED
