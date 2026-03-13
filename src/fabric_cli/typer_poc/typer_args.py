# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
TyperArgs — Compatibility bridge between Typer and existing argparse-based handlers.

This module provides a `TyperArgs` class that mimics `argparse.Namespace` so that
existing command handlers (which expect `args.path`, `args.output_format`, etc.)
can be reused without modification during the migration from argparse to typer.

Usage in a typer command:

    @app.command()
    def ls(path: Optional[str] = None, long: bool = False):
        args = TyperArgs(command="ls", path=path, long=long)
        return existing_ls_handler(args)
"""

from __future__ import annotations

from typing import Any, Optional


class TyperArgs:
    """Bridge between typer function parameters and argparse.Namespace-style access.

    Accepts arbitrary keyword arguments and exposes them as attributes,
    matching the `argparse.Namespace` interface that existing command
    handlers rely on.

    Example::

        args = TyperArgs(
            command="ls",
            path="/ws.Workspace",
            long=True,
            output_format="json",
        )
        assert args.command == "ls"
        assert args.path == "/ws.Workspace"
    """

    # Default values that every command handler may expect
    _defaults: dict[str, Any] = {
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

    def __init__(self, **kwargs: Any) -> None:
        # Apply defaults first, then overwrite with provided kwargs
        for key, default in self._defaults.items():
            setattr(self, key, kwargs.pop(key, default))

        # Set any remaining kwargs as attributes
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __repr__(self) -> str:
        attrs = ", ".join(f"{k}={v!r}" for k, v in self.__dict__.items())
        return f"TyperArgs({attrs})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TyperArgs):
            return NotImplemented
        return self.__dict__ == other.__dict__

    def get(self, key: str, default: Any = None) -> Any:
        """Dict-like access for optional attributes."""
        return getattr(self, key, default)
