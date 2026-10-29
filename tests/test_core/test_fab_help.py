# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Regression tests for static, machine-readable help."""

import argparse
import json
import subprocess
import sys
from typing import Any
from unittest.mock import patch

import pytest

from fabric_cli.core import fab_constant, fab_help
from fabric_cli.core.fab_parser_setup import (
    CustomArgumentParser,
    create_parser_and_subparsers,
)
from fabric_cli.main import main


@pytest.fixture
def parser() -> CustomArgumentParser:
    return create_parser_and_subparsers()[0]


def _help(
    parser: CustomArgumentParser,
    arguments: list[str],
    capsys: pytest.CaptureFixture[str],
) -> dict[str, Any]:
    with pytest.raises(SystemExit) as exc:
        parser.parse_args(arguments)
    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    assert "\x1b" not in captured.out
    return json.loads(captured.out)


@pytest.mark.parametrize("command", [[], ["ls"], ["job"], ["job", "run"]])
@pytest.mark.parametrize(
    "flags",
    [
        ["--help", "--output_format", "json"],
        ["--output_format", "json", "--help"],
        ["--help", "--output_format=json"],
        ["--output_format=json", "--help"],
        ["-h", "--output_format", "json"],
        ["-help", "--output_format", "json"],
    ],
)
def test_json_help_all_levels_and_flag_orders(
    parser: CustomArgumentParser,
    capsys: pytest.CaptureFixture[str],
    command: list[str],
    flags: list[str],
) -> None:
    document = _help(parser, command + flags, capsys)
    assert document["schema_version"] == "1.0"
    assert document["command"] == " ".join(["fab", *command])
    assert document["description"]
    assert document["outputs"]
    assert document["common_errors"]
    assert {entry["code"] for entry in document["exit_codes"]} == {0, 1, 2, 4}


def test_json_help_format_inherited_from_parent(
    parser: CustomArgumentParser, capsys: pytest.CaptureFixture[str]
) -> None:
    document = _help(
        parser, ["--output_format", "json", "job", "run-cancel", "--help"], capsys
    )
    assert document["command"] == "fab job run-cancel"
    inputs = {value["name"]: value for value in document["inputs"]}
    assert inputs["id"]["required"] is True
    assert inputs["path"]["required"] is True


def test_json_help_inputs_types_and_constraints(
    parser: CustomArgumentParser, capsys: pytest.CaptureFixture[str]
) -> None:
    document = _help(parser, ["job", "run", "--help", "--output_format=json"], capsys)
    inputs = {value["name"]: value for value in document["inputs"]}
    assert inputs["path"]["type"] == "string"
    assert inputs["path"]["nargs"] == "+"
    assert inputs["path"]["multiple"] is True
    assert inputs["path"]["flags"] == []
    assert inputs["timeout"]["type"] == "integer"
    assert inputs["polling_interval"]["type"] == "integer"
    assert inputs["polling_interval"]["constraints"] == {"minimum": 1}
    assert inputs["output_format"]["choices"] == ["json", "text"]
    assert inputs["output_format"]["default"] is None
    assert "skill" not in inputs

    document = _help(
        parser, ["job", "run-update", "--help", "--output_format=json"], capsys
    )
    inputs = {value["name"]: value for value in document["inputs"]}
    assert inputs["disable"]["type"] == "boolean"
    assert inputs["disable"]["default"] is True
    assert inputs["disable"]["nargs"] == 0
    assert inputs["type"]["choices"] == ["cron", "daily", "weekly"]

    document = _help(parser, ["mkdir", "--help", "--output_format=json"], capsys)
    inputs = {value["name"]: value for value in document["inputs"]}
    assert inputs["params"]["default"] == ["run=true"]
    assert inputs["params"]["multiple"] is True


def test_json_help_aliases_and_discovery(
    parser: CustomArgumentParser, capsys: pytest.CaptureFixture[str]
) -> None:
    document = _help(parser, ["config", "--help", "--output_format=json"], capsys)
    commands = {value["name"]: value for value in document["subcommands"]}
    assert commands["ls"]["aliases"] == ["dir"]
    assert commands["ls"]["description"] == "List all configuration values"
    assert "dir" not in commands
    document = _help(
        parser, ["config", "dir", "--help", "--output_format=json"], capsys
    )
    assert document["name"] == "ls"
    assert document["command"] == "fab config ls"
    assert document["aliases"] == ["dir"]
    assert document["subcommands"] == []


def test_json_help_does_not_leak_runtime_values(
    parser: CustomArgumentParser,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    marker = "not-a-real-credential"
    monkeypatch.setenv("FAB_SPN_CLIENT_SECRET", marker)
    document = _help(
        parser,
        [
            "auth",
            "login",
            "--password",
            marker,
            "--skill",
            marker,
            "--help",
            "--output_format=json",
        ],
        capsys,
    )
    assert marker not in json.dumps(document)
    inputs = {value["name"]: value for value in document["inputs"]}
    assert inputs["password"]["default"] is None
    assert "skill" not in inputs


@pytest.mark.parametrize("command", [[], ["job"], ["job", "run"], ["auth", "login"]])
def test_json_help_exits_before_initialization_or_dispatch(
    parser: CustomArgumentParser,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    command: list[str],
) -> None:
    monkeypatch.setattr(
        sys, "argv", ["fab", *command, "--help", "--output_format=json"]
    )
    with (
        patch(
            "fabric_cli.main.get_global_parser_and_subparsers",
            return_value=(parser, None),
        ),
        patch("fabric_cli.main.fab_state_config.init_defaults") as init,
        patch("fabric_cli.main._execute_command") as execute,
        patch("fabric_cli.main.fab_logger.print_log_file_path") as log,
        patch(
            "socket.socket.connect", side_effect=AssertionError("Unexpected network")
        ),
        pytest.raises(SystemExit) as exc,
    ):
        main()
    assert exc.value.code == 0
    init.assert_not_called()
    execute.assert_not_called()
    log.assert_not_called()
    captured = capsys.readouterr()
    assert captured.err == ""
    assert json.loads(captured.out)["command"] == " ".join(["fab", *command])


def test_json_help_in_fresh_process() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "fabric_cli.main",
            "job",
            "run-cancel",
            "--help",
            "--output_format",
            "json",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0
    assert result.stderr == ""
    assert json.loads(result.stdout)["command"] == "fab job run-cancel"


@pytest.mark.parametrize("command", [[], ["job"], ["job", "run"], ["config", "ls"]])
def test_text_help_unchanged_after_json_help(
    parser: CustomArgumentParser,
    capsys: pytest.CaptureFixture[str],
    command: list[str],
) -> None:
    with pytest.raises(SystemExit):
        parser.parse_args([*command, "--help"])
    original = capsys.readouterr()
    _help(parser, [*command, "--help", "--output_format=json"], capsys)
    with pytest.raises(SystemExit):
        parser.parse_args([*command, "--help", "--output_format=text"])
    assert capsys.readouterr() == original
    assert fab_help.is_json_help() is False


def test_json_format_does_not_change_normal_parsing(
    parser: CustomArgumentParser,
) -> None:
    args = parser.parse_args(
        ["job", "run", "item.Notebook", "--timeout", "12", "--output_format=json"]
    )
    assert args.path == ["item.Notebook"]
    assert args.timeout == 12
    assert args.output_format == "json"
    assert fab_help.is_json_help() is False


def test_double_dash_preserves_literal_flags(
    parser: CustomArgumentParser, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit):
        parser.parse_args(["job", "--help", "--", "--output_format=json"])
    assert not capsys.readouterr().out.lstrip().startswith("{")
    args = parser.parse_args(["ls", "--", "--help", "--output_format=json"])
    assert args.path == ["--help", "--output_format=json"]


def test_all_registered_commands_serialize(
    parser: CustomArgumentParser, capsys: pytest.CaptureFixture[str]
) -> None:
    pending: list[list[str]] = [[]]
    while pending:
        path = pending.pop()
        document = _help(parser, [*path, "--help", "--output_format=json"], capsys)
        assert document["name"]
        assert document["description"]
        pending.extend([*path, child["name"]] for child in document["subcommands"])


def test_unknown_validator_is_not_executed(
    capsys: pytest.CaptureFixture[str],
) -> None:
    def custom_type(value: str) -> str:
        raise AssertionError("Help must not run validators")

    parser = CustomArgumentParser(prog="fab")
    parser.add_argument("custom", type=custom_type)
    parser.add_argument("--hidden", help=argparse.SUPPRESS)
    document = _help(parser, ["--help", "--output_format=json"], capsys)
    inputs = {value["name"]: value for value in document["inputs"]}
    assert inputs["custom"]["type"] == "unknown"
    assert inputs["custom"]["validator"] == "custom_type"
    assert "hidden" not in inputs
    assert document["common_errors"][0]["code"] == fab_constant.ERROR_INVALID_INPUT


@pytest.mark.parametrize(
    ("command", "status", "formats"),
    [
        (["exists"], "partial", ["text", "json"]),
        (["config", "get"], "partial", ["text", "json"]),
        (["config", "ls"], "partial", ["text", "json"]),
        (["api"], "partial", ["text", "json"]),
        (["version"], "not_applicable", ["text"]),
        (["job", "run"], "unknown", None),
    ],
)
def test_output_metadata_is_explicit_about_coverage(
    parser: CustomArgumentParser,
    capsys: pytest.CaptureFixture[str],
    command: list[str],
    status: str,
    formats: list[str] | None,
) -> None:
    document = _help(parser, [*command, "--help", "--output_format=json"], capsys)
    assert document["outputs"]["schema_status"] == status
    assert document["outputs"]["formats"] == formats
    if status == "partial":
        schema = document["outputs"]["schema"]
        assert schema["required"] == ["timestamp", "status", "result"]
        assert schema["properties"]["status"] == {"const": "Success"}
    else:
        assert document["outputs"]["schema"] is None


def test_exists_output_metadata_matches_formatter(
    parser: CustomArgumentParser, capsys: pytest.CaptureFixture[str]
) -> None:
    from fabric_cli.core.fab_output import FabricCLIOutput

    document = _help(parser, ["exists", "--help", "--output_format=json"], capsys)
    schema = document["outputs"]["schema"]
    message_schema = schema["properties"]["result"]["properties"]["message"]
    for message in (fab_constant.INFO_EXISTS_TRUE, fab_constant.INFO_EXISTS_FALSE):
        output = json.loads(
            FabricCLIOutput(command="exists", message=message).to_json()
        )
        assert all(key in output for key in schema["required"])
        assert output["result"]["message"] in message_schema["enum"]
        assert isinstance(output["result"]["message"], str)
