# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for fabric_cli_v2.auth module."""

import pytest

from fabric_cli_v2.auth import FabricAuth


@pytest.fixture(autouse=True)
def _reset_auth():
    """Reset auth singleton between tests."""
    FabricAuth._instance = None
    yield
    FabricAuth._instance = None


class TestFabricAuth:

    def test_initial_state__not_authenticated(self):
        auth = FabricAuth()
        assert auth.is_authenticated is False
        assert auth.mode is None
        assert auth.credential is None

    def test_get_token__raises_when_not_authenticated(self):
        auth = FabricAuth()
        with pytest.raises(RuntimeError, match="Not authenticated"):
            auth.get_token()

    def test_logout__clears_state(self):
        auth = FabricAuth()
        auth._mode = "user"
        auth._credential = object()  # fake credential
        auth.logout()
        assert auth.is_authenticated is False
        assert auth.mode is None

    def test_singleton__returns_same_instance(self):
        a = FabricAuth.get_instance()
        b = FabricAuth.get_instance()
        assert a is b

    def test_login_spn__requires_secret_or_cert(self):
        auth = FabricAuth()
        with pytest.raises(ValueError, match="client_secret or cert_path"):
            auth.login_spn(
                tenant_id="t",
                client_id="c",
            )

    def test_env_token_credential(self, monkeypatch):
        """When FAB_TOKEN is set, login_from_environment should use it."""
        monkeypatch.setenv("FAB_TOKEN", "test-token-value")
        auth = FabricAuth()
        auth.login_from_environment()
        assert auth.is_authenticated
        assert auth.mode == "env"
        token = auth.get_token()
        assert token.token == "test-token-value"
