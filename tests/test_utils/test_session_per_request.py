"""Regression tests — per-request session creation (no shared session pool)."""

import pytest
from unittest.mock import patch, MagicMock
from argparse import Namespace
from fabric_cli.client import fab_api_client


class TestSessionPerRequest:
    """Verify each do_request creates a fresh Session (no shared pool)."""

    def test_no_shared_session_attribute(self):
        assert not hasattr(fab_api_client, "_shared_session"), \
            "Shared session singleton should be removed"

    def test_no_get_session_function(self):
        assert not hasattr(fab_api_client, "_get_session"), \
            "_get_session helper should be removed"

    def test_do_request_creates_new_session_each_call(self):
        fake_args = Namespace(
            json_file=None,
            audience=None,
            method="GET",
            wait=False,
            raw_response=False,
            request_params=None,
            uri="workspaces/00000000-0000-0000-0000-000000000001/items",
            headers=None,
        )
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"x-ms-request-id": "test"}
        mock_response.json.return_value = {}

        sessions = []

        def track_session(*a, **kw):
            s = MagicMock()
            s.request.return_value = mock_response
            sessions.append(s)
            return s

        with patch("fabric_cli.client.fab_api_client.requests.Session", side_effect=track_session), \
             patch("fabric_cli.core.fab_auth.FabAuth") as mock_auth_cls, \
             patch("fabric_cli.core.fab_context.Context") as mock_ctx_cls, \
             patch("fabric_cli.core.fab_state_config.get_config", return_value=None):
            mock_auth_cls.return_value.get_access_token.return_value = "tok"
            mock_ctx_cls.return_value.command = "test"
            try:
                fab_api_client.do_request(fake_args)
            except Exception:
                pass
            try:
                fab_api_client.do_request(fake_args)
            except Exception:
                pass

        assert len(sessions) >= 2, "Each do_request should create its own Session"
        assert sessions[0] is not sessions[1]
