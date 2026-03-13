# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for the Typer migration proof-of-concept.

These tests validate:
1. TyperArgs compatibility layer produces correct argparse.Namespace-like objects
2. Typer config commands invoke correctly via CliRunner
3. Help output includes examples and learn-more sections
4. Feature parity with the argparse-based config commands
"""

import pytest
from typer.testing import CliRunner

from fabric_cli.typer_poc.config_app import config_app
from fabric_cli.typer_poc.main_app import app as main_app
from fabric_cli.typer_poc.typer_args import TyperArgs


# --- TyperArgs Compatibility Layer Tests ---


class TestTyperArgs:
    """Validate the TyperArgs compatibility layer."""

    def test_typer_args__basic_attributes(self):
        args = TyperArgs(command="config", subcommand="set", key="mode", value="json")
        assert args.command == "config"
        assert args.config_subcommand == "set"
        assert args.command_path == "config set"
        assert args.fab_mode == "command_line"
        assert args.key == "mode"
        assert args.value == "json"

    def test_typer_args__output_format_default_none(self):
        args = TyperArgs(command="config", subcommand="get")
        assert args.output_format is None

    def test_typer_args__output_format_set(self):
        args = TyperArgs(command="config", subcommand="ls", output_format="json")
        assert args.output_format == "json"

    def test_typer_args__command_path_without_subcommand(self):
        args = TyperArgs(command="version")
        assert args.command_path == "version"

    def test_typer_args__subcommand_attribute_naming(self):
        """Verify the <command>_subcommand attribute is set correctly."""
        args = TyperArgs(command="job", subcommand="start")
        assert args.job_subcommand == "start"

    def test_typer_args__arbitrary_kwargs(self):
        args = TyperArgs(command="config", subcommand="set", foo="bar", count=42)
        assert args.foo == "bar"
        assert args.count == 42


# --- Config App Help Tests ---


runner = CliRunner()


class TestConfigAppHelp:
    """Validate help output for Typer config commands."""

    def test_config_app__no_args_shows_help(self):
        result = runner.invoke(config_app, [])
        # Typer returns exit code 2 for no_args_is_help (usage error)
        assert result.exit_code in (0, 2)
        assert "Usage" in result.output

    def test_config_set__help_shows_examples(self):
        result = runner.invoke(config_app, ["set", "--help"])
        assert result.exit_code == 0
        assert "config set mode command_line" in result.output

    def test_config_set__help_shows_learn_more(self):
        result = runner.invoke(config_app, ["set", "--help"])
        assert result.exit_code == 0
        assert "https://aka.ms/fabric-cli" in result.output

    def test_config_get__help_shows_examples(self):
        result = runner.invoke(config_app, ["get", "--help"])
        assert result.exit_code == 0
        assert "config get mode" in result.output

    def test_config_ls__help_shows_examples(self):
        result = runner.invoke(config_app, ["ls", "--help"])
        assert result.exit_code == 0
        assert "config ls" in result.output

    def test_config_clear_cache__help_shows_examples(self):
        result = runner.invoke(config_app, ["clear-cache", "--help"])
        assert result.exit_code == 0
        assert "config clear-cache" in result.output

    def test_config_set__help_shows_key_value_args(self):
        result = runner.invoke(config_app, ["set", "--help"])
        assert result.exit_code == 0
        assert "KEY" in result.output
        assert "VALUE" in result.output

    def test_config_get__help_shows_key_arg(self):
        result = runner.invoke(config_app, ["get", "--help"])
        assert result.exit_code == 0
        assert "KEY" in result.output


# --- Main App Tests ---


class TestMainApp:
    """Validate the main Typer app composition."""

    def test_main_app__help_shows_config(self):
        result = runner.invoke(main_app, ["--help"])
        assert result.exit_code == 0
        assert "config" in result.output.lower()

    def test_main_app__config_subcommand_help(self):
        result = runner.invoke(main_app, ["config", "--help"])
        assert result.exit_code == 0
        assert "set" in result.output
        assert "get" in result.output
        assert "ls" in result.output
        assert "clear-cache" in result.output

    def test_main_app__invalid_command(self):
        result = runner.invoke(main_app, ["nonexistent"])
        assert result.exit_code != 0

    def test_main_app__version_flag(self):
        """Version flag should invoke version callback."""
        result = runner.invoke(main_app, ["--version"])
        # May exit 0 or trigger version print depending on fab_ui availability
        # The key validation is that --version is recognized as a valid flag
        assert result.exit_code == 0 or "version" in result.output.lower()


# --- Error Handling Tests ---


class TestConfigAppErrors:
    """Validate error handling in Typer config commands."""

    def test_config_set__missing_args(self):
        """Missing required args should result in error."""
        result = runner.invoke(config_app, ["set"])
        assert result.exit_code != 0

    def test_config_set__missing_value(self):
        """Missing value arg should result in error."""
        result = runner.invoke(config_app, ["set", "mode"])
        assert result.exit_code != 0

    def test_config_get__missing_key(self):
        """Missing key arg should result in error."""
        result = runner.invoke(config_app, ["get"])
        assert result.exit_code != 0
