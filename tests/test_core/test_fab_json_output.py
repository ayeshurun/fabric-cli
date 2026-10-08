# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Regression coverage for compact JSON and shared result queries."""

import argparse
import json
from typing import Any
from unittest.mock import Mock

import pytest

from fabric_cli.core import fab_constant
from fabric_cli.core.fab_decorators import handle_exceptions, set_command_context
from fabric_cli.core.fab_exceptions import FabricCLIError
from fabric_cli.core.fab_output import FabricCLIOutput
from fabric_cli.core.fab_parser_setup import create_parser_and_subparsers
from fabric_cli.utils import fab_jmespath, fab_ui


@pytest.fixture
def parser() -> argparse.ArgumentParser:
    return create_parser_and_subparsers()[0]


@pytest.mark.parametrize(
    "argv",
    [
        ["--json", "config", "ls"],
        ["config", "--json", "ls"],
        ["config", "ls", "--json"],
        ["dir", ".capacities", "--json"],
        ["get", "ws.Workspace/f.Folder/n.Notebook", "--json", "-q", "."],
        ["table", "schema", "ws.Workspace/l.Lakehouse/Tables/t", "--json"],
    ],
)
def test_json_flag_survives_nested_parsers(
    parser: argparse.ArgumentParser, argv: list[str]
) -> None:
    args = parser.parse_args(argv)
    assert args.output_format == "json"
    assert args.compact_json is True


@pytest.mark.parametrize(
    "argv,format_type,compact",
    [
        (["--json", "config", "ls", "--output_format", "text"], "text", False),
        (["--output_format", "text", "config", "ls", "--json"], "json", True),
        (["config", "ls", "--json", "--output_format", "json"], "json", False),
        (["--output_format", "json", "config", "ls"], "json", False),
    ],
)
def test_explicit_output_flags_have_deterministic_precedence(
    parser: argparse.ArgumentParser,
    argv: list[str],
    format_type: str,
    compact: bool,
) -> None:
    args = parser.parse_args(argv)
    assert args.output_format == format_type
    assert args.compact_json is compact


def test_output_defaults_and_repl_subparser(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args(["config", "ls"])
    assert args.output_format is None
    subparsers = next(
        action
        for action in parser._actions
        if isinstance(action, argparse._SubParsersAction)
    )
    args = subparsers.choices["config"].parse_args(["ls", "--json", "-q", "[0]"])
    assert args.output_format == "json"
    assert args.output_query == "[0]"


def test_all_leaf_parsers_offer_query(parser: argparse.ArgumentParser) -> None:
    def check(current: argparse.ArgumentParser) -> None:
        children = [
            action
            for action in current._actions
            if isinstance(action, argparse._SubParsersAction)
        ]
        if children:
            for action in children:
                for child in set(action.choices.values()):
                    check(child)
        else:
            assert "-q" in current._option_string_actions
            assert "--json" in current._option_string_actions

    check(parser)


def test_existing_set_query_is_not_an_output_query(
    parser: argparse.ArgumentParser,
) -> None:
    args = parser.parse_args(["set", "ws.Workspace", "-q", "description", "-i", "new"])
    assert args.query == "description"
    assert getattr(args, "output_query", None) is None
    with pytest.raises(SystemExit):
        parser.parse_args(["set", "ws.Workspace", "-i", "new"])


@pytest.mark.parametrize("value", [False, 0, "", [], {}, None, 2.5, "name"])
def test_query_preserves_json_types(
    value: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    args = argparse.Namespace(
        output_format="json", compact_json=True, output_query="value"
    )
    fab_ui.print_output_format(args, data={"value": value})
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert result["result"]["data"] == (value if isinstance(value, list) else [value])
    assert captured.out.count("\n") == 1
    assert captured.err == ""
    assert type(fab_jmespath.search({"value": value}, "value")) is type(value)


def test_omitted_data_differs_from_explicit_null() -> None:
    assert "data" not in json.loads(FabricCLIOutput(message="done").to_json())["result"]
    assert json.loads(FabricCLIOutput(data=None).to_json())["result"]["data"] == [None]


def test_projection_preserves_diagnostics(capsys: pytest.CaptureFixture[str]) -> None:
    args = argparse.Namespace(
        command="ls",
        output_format="json",
        compact_json=True,
        output_query="[?name == 'absent']",
    )
    fab_ui.print_warning("Some resources could not be retrieved")
    fab_ui.print_output_format(
        args,
        data=[{"name": "visible"}],
        hidden_data=[".capacities"],
        message="Skipped unsupported resources",
    )
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert result["status"] == "Success"
    assert result["result"] == {
        "data": [],
        "hidden_data": [".capacities"],
        "message": "Skipped unsupported resources",
    }
    assert "could not be retrieved" in captured.err
    assert "omitted_count" not in captured.out


def test_legacy_query_is_not_applied_twice(capsys: pytest.CaptureFixture[str]) -> None:
    args = argparse.Namespace(output_format="json", query="length(@)")
    fab_ui.print_output_format(args, data=3)
    assert json.loads(capsys.readouterr().out)["result"]["data"] == [3]


def test_json_legacy_pretty_format_unchanged(
    capsys: pytest.CaptureFixture[str],
) -> None:
    fab_ui.print_output_format(
        argparse.Namespace(output_format="json"), data={"id": "a"}
    )
    captured = capsys.readouterr()
    assert '\n    "status": "Success"' in captured.out
    assert json.loads(captured.out)["result"]["data"] == [{"id": "a"}]


@pytest.mark.parametrize(
    "error_code,exit_code",
    [
        (fab_constant.ERROR_INVALID_INPUT, fab_constant.EXIT_CODE_ERROR),
        (
            fab_constant.ERROR_UNAUTHORIZED,
            fab_constant.EXIT_CODE_AUTHORIZATION_REQUIRED,
        ),
    ],
)
def test_query_cannot_hide_failure(
    error_code: str, exit_code: int, capsys: pytest.CaptureFixture[str]
) -> None:
    @handle_exceptions()
    def command(args: argparse.Namespace) -> None:
        raise FabricCLIError("Failure details", error_code)

    args = argparse.Namespace(
        command_path="test",
        output_format="json",
        compact_json=True,
        output_query="`null`",
    )
    assert command(args) == exit_code
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert result["status"] == "Failure"
    assert result["result"]["error_code"] == error_code
    assert result["result"]["message"] == "Failure details"
    assert captured.out.count("\n") == 1


@pytest.mark.parametrize("query", ["[", "", "a..b"])
def test_invalid_output_query_prevents_command_execution(
    query: str, capsys: pytest.CaptureFixture[str]
) -> None:
    action = Mock()

    @handle_exceptions()
    @set_command_context()
    def command(args: argparse.Namespace) -> None:
        action()

    args = argparse.Namespace(
        command_path="test", output_format="json", compact_json=True, output_query=query
    )
    assert command(args) == fab_constant.EXIT_CODE_ERROR
    action.assert_not_called()
    result = json.loads(capsys.readouterr().out)
    assert result["result"]["error_code"] == fab_constant.ERROR_INVALID_INPUT


def test_query_runtime_error_is_structured() -> None:
    with pytest.raises(FabricCLIError) as error:
        fab_jmespath.search({"id": 1}, "length(id)")
    assert error.value.status_code == fab_constant.ERROR_INVALID_INPUT


def test_scalar_query_works_with_key_value_text_output(
    capsys: pytest.CaptureFixture[str],
) -> None:
    fab_ui.print_output_format(
        argparse.Namespace(output_format="text", output_query="enabled"),
        data={"enabled": False},
        show_key_value_list=True,
    )
    assert capsys.readouterr().out.strip() == "False"


def test_main_rejects_query_before_dispatch(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from fabric_cli import main

    action = Mock()
    monkeypatch.setattr("sys.argv", ["fab", "config", "ls", "--json", "-q", "["])
    monkeypatch.setattr(main.fab_state_config, "init_defaults", lambda: None)
    monkeypatch.setattr(main, "_execute_command", action)
    with pytest.raises(SystemExit) as error:
        main.main()
    assert error.value.code == fab_constant.EXIT_CODE_ERROR
    action.assert_not_called()
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "Failure"
    assert result["result"]["error_code"] == fab_constant.ERROR_INVALID_INPUT


def test_legacy_query_preflight_and_set_target() -> None:
    with pytest.raises(FabricCLIError):
        fab_jmespath.validate_query_args(argparse.Namespace(command="api", query=["["]))
    fab_jmespath.validate_query_args(
        argparse.Namespace(command="set", query="mutation target")
    )
