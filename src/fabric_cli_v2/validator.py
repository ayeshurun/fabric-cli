# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Command validation for Fabric CLI v2.

Loads ``command_support.yaml`` to check whether a command + item-type
combination is supported *before* making any API call.
"""

from __future__ import annotations

import os
from typing import Any, Optional

import yaml


class CommandValidator:
    """Validates commands against the support matrix."""

    _instance: Optional[CommandValidator] = None

    def __init__(self, yaml_path: Optional[str] = None) -> None:
        if yaml_path is None:
            # Default: look for the v1 YAML (reuse it)
            yaml_path = os.path.join(
                os.path.dirname(__file__),
                "..",
                "fabric_cli",
                "core",
                "fab_config",
                "command_support.yaml",
            )
        self._path = yaml_path
        self._config: Optional[dict[str, Any]] = None

    def _load(self) -> dict[str, Any]:
        if self._config is None:
            with open(self._path, encoding="utf-8") as fh:
                self._config = yaml.safe_load(fh).get("commands", {})
        return self._config

    # ------------------------------------------------------------------

    def validate(
        self,
        command: str,
        subcommand: Optional[str] = None,
        *,
        element_type: Optional[str] = None,
        item_type: Optional[str] = None,
    ) -> bool:
        """Raise ``ValueError`` if unsupported, else return ``True``."""
        cfg = self._load()
        cmd_cfg = cfg.get(command)
        if cmd_cfg is None:
            return True  # not tracked → allow

        eff = self._effective(cmd_cfg, subcommand)
        display = f"{command} {subcommand}" if subcommand else command

        if element_type:
            sup = eff.get("supported_elements")
            if sup is not None and element_type not in sup:
                raise ValueError(
                    f"'{display}' does not support element type '{element_type}'. "
                    f"Supported: {', '.join(sorted(sup))}"
                )

        if item_type:
            unsup = eff.get("unsupported_items", [])
            if item_type in unsup:
                sup = eff.get("supported_items", [])
                hint = f" Supported: {', '.join(sorted(sup))}" if sup else ""
                raise ValueError(
                    f"'{display}' does not support '{item_type}'.{hint}"
                )
            sup = eff.get("supported_items")
            if sup is not None and item_type not in sup:
                raise ValueError(
                    f"'{display}' does not support '{item_type}'. "
                    f"Supported: {', '.join(sorted(sup))}"
                )

        return True

    def is_supported(self, command: str, subcommand: Optional[str] = None,
                     *, element_type: Optional[str] = None,
                     item_type: Optional[str] = None) -> bool:
        try:
            return self.validate(command, subcommand,
                                element_type=element_type, item_type=item_type)
        except ValueError:
            return False

    def get_supported_items(self, command: str, subcommand: Optional[str] = None) -> list[str]:
        cfg = self._load()
        eff = self._effective(cfg.get(command, {}), subcommand)
        return list(eff.get("supported_items", []))

    # ------------------------------------------------------------------

    @staticmethod
    def _effective(cmd_cfg: dict[str, Any], subcommand: Optional[str]) -> dict[str, Any]:
        eff: dict[str, Any] = {}
        for k in ("supported_elements", "supported_items", "unsupported_items"):
            if k in cmd_cfg:
                eff[k] = list(cmd_cfg[k])
        if subcommand:
            sub = cmd_cfg.get("subcommands", {}).get(subcommand, {})
            if sub:
                for k in ("supported_elements", "supported_items", "unsupported_items"):
                    if k in sub:
                        eff[k] = list(sub[k])
        return eff

    @classmethod
    def get_instance(cls) -> CommandValidator:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
