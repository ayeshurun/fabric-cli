# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for HTTP session handling in fab_api_client."""


class TestSessionPerRequestUpstream:
    """Verify per-request session creation (shared session pool removed)."""

    def test_no_shared_session_module_attribute(self):
        """_shared_session module attribute must not exist."""
        from fabric_cli.client import fab_api_client

        assert not hasattr(fab_api_client, "_shared_session"), \
            "Shared session singleton should be removed"

    def test_no_get_session_function(self):
        """_get_session helper must not exist."""
        from fabric_cli.client import fab_api_client

        assert not hasattr(fab_api_client, "_get_session"), \
            "_get_session helper should be removed"
