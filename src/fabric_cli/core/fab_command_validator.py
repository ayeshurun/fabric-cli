# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Command Validator — Early failure detection for Fabric CLI commands.

Validates that a command + element/item type combination is supported
*before* executing any API calls.  Uses the ``command_support.yaml``
matrix as the source of truth.

Usage::

    from fabric_cli.core.fab_command_validator import CommandValidator

    validator = CommandValidator()

    # Raises FabricCLIError if unsupported
    validator.validate("fs", "start", item_type="notebook")

    # Returns True / supported-items list for introspection
    validator.is_supported("fs", "ls", element_type="workspace")
"""

from __future__ import annotations

import os
from typing import Any, Optional

import yaml

from fabric_cli.core import fab_constant
from fabric_cli.core.fab_exceptions import FabricCLIError


class CommandValidator:
    """Validates command + element/item type against ``command_support.yaml``.

    The YAML file is loaded once and cached for the lifetime of the
    validator instance.  A module-level singleton is available via
    :func:`get_validator`.
    """

    def __init__(self, yaml_path: Optional[str] = None) -> None:
        if yaml_path is None:
            yaml_path = os.path.join(
                os.path.dirname(__file__),
                "fab_config",
                "command_support.yaml",
            )
        self._yaml_path = yaml_path
        self._config: dict[str, Any] | None = None

    # ------------------------------------------------------------------
    # YAML loading (lazy)
    # ------------------------------------------------------------------

    def _load(self) -> dict[str, Any]:
        if self._config is None:
            with open(self._yaml_path, "r", encoding="utf-8") as fh:
                raw = yaml.safe_load(fh)
            self._config = raw.get("commands", {})
        return self._config

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate(
        self,
        command: str,
        subcommand: Optional[str] = None,
        *,
        element_type: Optional[str] = None,
        item_type: Optional[str] = None,
    ) -> bool:
        """Validate a command invocation.

        Raises :class:`FabricCLIError` if the combination is explicitly
        unsupported.  Returns ``True`` if the combination is either
        explicitly supported or not mentioned (i.e. not blocked).

        Parameters
        ----------
        command : str
            Top-level command group (e.g., ``"fs"``, ``"job"``).
        subcommand : str, optional
            Subcommand (e.g., ``"ls"``, ``"start"``).
        element_type : str, optional
            Fabric element type (e.g., ``"workspace"``, ``"tenant"``).
        item_type : str, optional
            Fabric item type (e.g., ``"notebook"``, ``"capacity"``).

        Returns
        -------
        bool
            ``True`` if validated successfully.

        Raises
        ------
        FabricCLIError
            If the combination is explicitly unsupported.
        """
        config = self._load()

        cmd_config = config.get(command)
        if cmd_config is None:
            # Command not in YAML → no restrictions defined
            return True

        # Resolve the effective config for the subcommand
        effective = self._resolve_effective_config(cmd_config, subcommand)

        display_cmd = f"{command} {subcommand}" if subcommand else command

        # Check element type support
        if element_type is not None:
            self._check_element_support(effective, element_type, display_cmd)

        # Check item type support
        if item_type is not None:
            self._check_item_support(effective, item_type, display_cmd)

        return True

    def is_supported(
        self,
        command: str,
        subcommand: Optional[str] = None,
        *,
        element_type: Optional[str] = None,
        item_type: Optional[str] = None,
    ) -> bool:
        """Return ``True`` if the combination is supported, ``False`` otherwise.

        Unlike :meth:`validate`, this does *not* raise on failure.
        """
        try:
            return self.validate(
                command,
                subcommand,
                element_type=element_type,
                item_type=item_type,
            )
        except FabricCLIError:
            return False

    def get_supported_items(
        self, command: str, subcommand: Optional[str] = None
    ) -> list[str]:
        """Return the list of explicitly supported item types for a command."""
        config = self._load()
        cmd_config = config.get(command, {})
        effective = self._resolve_effective_config(cmd_config, subcommand)
        return list(effective.get("supported_items", []))

    def get_supported_elements(
        self, command: str, subcommand: Optional[str] = None
    ) -> list[str]:
        """Return the list of explicitly supported element types for a command."""
        config = self._load()
        cmd_config = config.get(command, {})
        effective = self._resolve_effective_config(cmd_config, subcommand)
        return list(effective.get("supported_elements", []))

    def get_unsupported_items(
        self, command: str, subcommand: Optional[str] = None
    ) -> list[str]:
        """Return the list of explicitly unsupported item types for a command."""
        config = self._load()
        cmd_config = config.get(command, {})
        effective = self._resolve_effective_config(cmd_config, subcommand)
        return list(effective.get("unsupported_items", []))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_effective_config(
        cmd_config: dict[str, Any], subcommand: Optional[str]
    ) -> dict[str, Any]:
        """Merge command-level and subcommand-level config."""
        if not cmd_config:
            return {}

        # Start with command-level settings
        effective: dict[str, Any] = {}
        for key in ("supported_elements", "supported_items", "unsupported_items"):
            if key in cmd_config:
                effective[key] = list(cmd_config[key])

        # Overlay subcommand-specific settings
        if subcommand is not None:
            subcommands = cmd_config.get("subcommands", {})
            sub_config = subcommands.get(subcommand, {})
            if sub_config:
                for key in ("supported_elements", "supported_items", "unsupported_items"):
                    if key in sub_config:
                        effective[key] = list(sub_config[key])

        return effective

    def _check_element_support(
        self,
        effective: dict[str, Any],
        element_type: str,
        display_cmd: str,
    ) -> None:
        """Raise if element_type is not in the supported list (when list exists)."""
        supported = effective.get("supported_elements")
        if supported is not None and element_type not in supported:
            supported_str = ", ".join(sorted(supported))
            raise FabricCLIError(
                f"The '{display_cmd}' command does not support the element type "
                f"'{element_type}'. Supported element types: {supported_str}",
                fab_constant.ERROR_UNSUPPORTED_COMMAND,
            )

    def _check_item_support(
        self,
        effective: dict[str, Any],
        item_type: str,
        display_cmd: str,
    ) -> None:
        """Raise if item_type is explicitly unsupported or missing from supported list."""
        unsupported = effective.get("unsupported_items", [])
        if item_type in unsupported:
            supported = effective.get("supported_items", [])
            hint = ""
            if supported:
                hint = f" Supported item types: {', '.join(sorted(supported))}"
            raise FabricCLIError(
                f"The '{display_cmd}' command does not support '{item_type}' items.{hint}",
                fab_constant.ERROR_UNSUPPORTED_ITEM_TYPE,
            )

        supported = effective.get("supported_items")
        if supported is not None and item_type not in supported:
            supported_str = ", ".join(sorted(supported))
            raise FabricCLIError(
                f"The '{display_cmd}' command does not support '{item_type}' items. "
                f"Supported item types: {supported_str}",
                fab_constant.ERROR_UNSUPPORTED_ITEM_TYPE,
            )


# ------------------------------------------------------------------
# Module-level singleton
# ------------------------------------------------------------------

_validator: CommandValidator | None = None


def get_validator() -> CommandValidator:
    """Return a cached singleton :class:`CommandValidator`."""
    global _validator
    if _validator is None:
        _validator = CommandValidator()
    return _validator
