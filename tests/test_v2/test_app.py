# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for the v2 CLI app (typer-based)."""

import pytest
from typer.testing import CliRunner

from fabric_cli_v2.app import app, _ensure_commands

runner = CliRunner()


@pytest.fixture(autouse=True)
def _register():
    _ensure_commands()


class TestCLIApp:

    def test_version(self):
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "2.0.0" in result.output

    def test_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "ls" in result.output
        assert "auth" in result.output
        assert "config" in result.output

    def test_pwd(self):
        result = runner.invoke(app, ["pwd"])
        assert result.exit_code == 0
        assert "/" in result.output

    def test_ls_help(self):
        result = runner.invoke(app, ["ls", "--help"])
        assert result.exit_code == 0
        assert "Path to list" in result.output

    def test_cd_root(self):
        result = runner.invoke(app, ["cd", "/"])
        assert result.exit_code == 0

    def test_auth_help(self):
        result = runner.invoke(app, ["auth", "--help"])
        assert result.exit_code == 0
        assert "login" in result.output
        assert "logout" in result.output
        assert "status" in result.output

    def test_auth_status__not_authenticated(self):
        result = runner.invoke(app, ["auth", "status"])
        assert result.exit_code == 0
        assert "Not authenticated" in result.output

    def test_config_ls(self):
        result = runner.invoke(app, ["config", "ls"])
        assert result.exit_code == 0
        assert "output_format" in result.output

    def test_config_get(self):
        result = runner.invoke(app, ["config", "get", "output_format"])
        assert result.exit_code == 0

    def test_config_set_invalid_value(self):
        result = runner.invoke(app, ["config", "set", "output_format", "invalid"])
        assert result.exit_code != 0

    def test_config_set_valid_value(self):
        result = runner.invoke(app, ["config", "set", "output_format", "json"])
        assert result.exit_code == 0
        assert "json" in result.output
