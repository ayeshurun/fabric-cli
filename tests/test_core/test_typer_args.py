# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for the TyperArgs compatibility bridge."""

import pytest

from fabric_cli.typer_poc.typer_args import TyperArgs


class TestTyperArgs:
    """Test suite for the TyperArgs compatibility layer."""

    def test_default_values__populated(self):
        """Default values should be set even without explicit kwargs."""
        args = TyperArgs()
        assert args.command is None
        assert args.output_format is None
        assert args.all is False
        assert args.long is False
        assert args.force is False
        assert args.fab_mode == "commandline"

    def test_explicit_values__override_defaults(self):
        args = TyperArgs(command="ls", all=True, output_format="json")
        assert args.command == "ls"
        assert args.all is True
        assert args.output_format == "json"

    def test_extra_kwargs__set_as_attributes(self):
        args = TyperArgs(path="/ws.Workspace", custom_flag=42)
        assert args.path == "/ws.Workspace"
        assert args.custom_flag == 42

    def test_get__returns_existing_attr(self):
        args = TyperArgs(command="ls")
        assert args.get("command") == "ls"

    def test_get__returns_default_for_missing(self):
        args = TyperArgs()
        assert args.get("nonexistent", "fallback") == "fallback"

    def test_get__returns_none_for_missing_without_default(self):
        args = TyperArgs()
        assert args.get("nonexistent") is None

    def test_repr__contains_attrs(self):
        args = TyperArgs(command="ls", path="/ws")
        r = repr(args)
        assert "TyperArgs(" in r
        assert "command='ls'" in r
        assert "path='/ws'" in r

    def test_eq__same_values(self):
        a = TyperArgs(command="ls", path="/ws")
        b = TyperArgs(command="ls", path="/ws")
        assert a == b

    def test_eq__different_values(self):
        a = TyperArgs(command="ls")
        b = TyperArgs(command="cd")
        assert a != b

    def test_eq__not_typer_args(self):
        a = TyperArgs(command="ls")
        assert a != "not a TyperArgs"

    def test_all_defaults_present(self):
        """Verify all documented defaults exist."""
        args = TyperArgs()
        expected_defaults = {
            "command": None,
            "output_format": None,
            "json_file": None,
            "query": None,
            "all": False,
            "long": False,
            "force": False,
            "recursive": False,
            "fab_mode": "commandline",
            "command_path": None,
        }
        for key, expected in expected_defaults.items():
            assert getattr(args, key) == expected, f"Default mismatch for {key}"
