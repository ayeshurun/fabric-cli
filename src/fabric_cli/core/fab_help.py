# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Static, versioned help metadata; never inspects a parsed command or user config."""

import argparse
import json
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Iterator, Sequence

from fabric_cli import __version__
from fabric_cli.core import fab_constant
from fabric_cli.parsers.fab_parser_validators import validate_positive_int

_help_context: ContextVar[tuple[argparse.ArgumentParser, str] | None] = ContextVar(
    "fab_help_context", default=None
)

_TYPE_METADATA: dict[Any, dict[str, Any]] = {
    None: {"type": "string"},
    str: {"type": "string"},
    int: {"type": "integer"},
    float: {"type": "number"},
    bool: {"type": "boolean"},
    validate_positive_int: {"type": "integer", "constraints": {"minimum": 1}},
}

_COMMON_ERRORS = [
    {
        "code": fab_constant.ERROR_INVALID_INPUT,
        "description": "A command input is invalid.",
        "recovery": "Check the command inputs, choices, and constraints.",
    },
    {
        "code": fab_constant.ERROR_INVALID_PATH,
        "description": "A Fabric path is invalid.",
        "recovery": "Check the workspace, item suffix, and current working directory.",
    },
    {
        "code": fab_constant.ERROR_AUTHENTICATION_FAILED,
        "description": "Authentication failed.",
        "recovery": "Check the authentication method and sign in with fab auth login.",
    },
    {
        "code": fab_constant.ERROR_FORBIDDEN,
        "description": "Access to the requested resource is denied.",
        "recovery": "Check the account's permissions on the requested resource.",
    },
    {
        "code": fab_constant.ERROR_NOT_FOUND,
        "description": "The requested resource was not found.",
        "recovery": "Verify that the resource exists and that its path is correct.",
    },
    {
        "code": fab_constant.ERROR_UNEXPECTED_ERROR,
        "description": "An unexpected error occurred.",
        "recovery": "Inspect the error message and diagnostic logs before retrying.",
    },
]


@contextmanager
def help_output_context(
    parser: argparse.ArgumentParser, arguments: Sequence[str]
) -> Iterator[None]:
    """Share an explicit help format across nested parsers, for one parse only."""
    if _help_context.get() is not None:
        yield
        return

    output_format = "text"
    # Look ahead because argparse's help action exits before later flags are parsed.
    # Stop at -- so positional data cannot change the help format.
    for index, argument in enumerate(arguments):
        if argument == "--":
            break
        if argument.startswith("--output_format="):
            output_format = argument.partition("=")[2]
        elif argument == "--output_format" and index + 1 < len(arguments):
            output_format = arguments[index + 1]
    token = _help_context.set((parser, output_format))
    try:
        yield
    finally:
        _help_context.reset(token)


def is_json_help() -> bool:
    """Return whether the current parse explicitly requests JSON help."""
    context = _help_context.get()
    return context is not None and context[1] == "json"


def _children(
    parser: argparse.ArgumentParser,
) -> Iterator[tuple[str, argparse.ArgumentParser, list[str], str | None]]:
    for action in parser._actions:
        if not isinstance(action, argparse._SubParsersAction):
            continue
        descriptions = {entry.dest: entry.help for entry in action._choices_actions}
        seen: set[int] = set()
        for name, child in action.choices.items():
            if id(child) in seen:
                continue
            seen.add(id(child))
            description = descriptions.get(name, child.description)
            if description == argparse.SUPPRESS:
                continue
            aliases = [
                alias
                for alias, candidate in action.choices.items()
                if candidate is child and alias != name
            ]
            yield name, child, aliases, description


def _find_command(
    root: argparse.ArgumentParser,
    target: argparse.ArgumentParser,
    path: list[str],
    aliases: list[str],
    description: str | None,
) -> tuple[list[str], list[str], str | None] | None:
    if root is target:
        return path, aliases, root.description or description
    for name, child, child_aliases, child_description in _children(root):
        found = _find_command(
            child, target, [*path, name], child_aliases, child_description
        )
        if found is not None:
            return found
    return None


def _input_metadata(action: argparse.Action) -> dict[str, Any]:
    flag = isinstance(
        action,
        (argparse._StoreTrueAction, argparse._StoreFalseAction, argparse._HelpAction),
    )
    metadata = (
        {"type": "boolean"}
        if flag
        else _TYPE_METADATA.get(action.type, {"type": "unknown"})
    )
    result = {
        "name": action.dest,
        "flags": action.option_strings,
        "kind": "option" if action.option_strings else "positional",
        "description": action.help,
        "required": action.required,
        "default": None if action.default == argparse.SUPPRESS else action.default,
        "default_suppressed": action.default == argparse.SUPPRESS,
        "choices": list(action.choices) if action.choices is not None else None,
        "nargs": action.nargs,
        "multiple": action.nargs in ("*", "+")
        or isinstance(action.nargs, int)
        and action.nargs > 0,
        "repeatable": isinstance(
            action, (argparse._AppendAction, argparse._CountAction)
        ),
        **metadata,
    }
    if action.type not in _TYPE_METADATA:
        result["validator"] = getattr(action.type, "__name__", "custom")
    return result


def format_json_help(parser: argparse.ArgumentParser) -> str:
    """Describe a parser using declarations only, without loading command handlers."""
    context = _help_context.get()
    root = context[0] if context else parser
    path, aliases, description = _find_command(
        root, parser, ["fab", *root.prog.split()[1:]], [], root.description
    ) or (["fab"], [], parser.description)
    subcommands = [
        {
            "name": name,
            "command": " ".join([*path, name]),
            "description": child.description or summary,
            "aliases": child_aliases,
        }
        for name, child, child_aliases, summary in _children(parser)
    ]
    document = {
        "schema_version": "1.0",
        "cli_version": __version__,
        "name": path[-1],
        "command": " ".join(path),
        "description": description,
        "aliases": aliases,
        "inputs": [
            _input_metadata(action)
            for action in parser._actions
            if not isinstance(action, argparse._SubParsersAction)
            and action.help != argparse.SUPPRESS
        ],
        "subcommands": subcommands,
        "outputs": {
            "formats": ["text", "json"],
            "schema_status": "unknown",
            "schema": None,
            "description": (
                "Command output is not yet described by a command-specific schema. "
                "The output_format flag does not guarantee all output is structured."
            ),
        },
        "common_errors": _COMMON_ERRORS,
        "errors_scope": (
            "Non-exhaustive CLI-wide examples, not guaranteed for every command. "
            "Service APIs can return additional error codes."
        ),
        "exit_codes": [
            {"code": fab_constant.EXIT_CODE_SUCCESS, "description": "Success or help."},
            {"code": fab_constant.EXIT_CODE_ERROR, "description": "Command failure."},
            {
                "code": fab_constant.EXIT_CODE_CANCELLED_OR_MISUSE_BUILTINS,
                "description": "Invalid command syntax or cancellation.",
            },
            {
                "code": fab_constant.EXIT_CODE_AUTHORIZATION_REQUIRED,
                "description": "Authorization required.",
            },
        ],
    }
    return json.dumps(document, indent=2, ensure_ascii=False) + "\n"
