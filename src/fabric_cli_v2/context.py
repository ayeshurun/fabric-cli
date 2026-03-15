# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Context persistence for Fabric CLI v2.

Tracks the user's current "working directory" in the Fabric hierarchy
(tenant → workspace → item → OneLake path) and persists it across
shell invocations so that ``fab ls`` in a new terminal resumes where
the user left off.

Persistence file: ``~/.config/fab/context-{ppid}.json``
Controlled by config key ``context_persistence_enabled``.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

from fabric_cli_v2.config import _CONFIG_DIR
from fabric_cli_v2.types import ElementType, FabricElement


class Context:
    """Singleton that holds the current navigation context."""

    _instance: Optional[Context] = None

    def __init__(self) -> None:
        self._current: Optional[FabricElement] = None
        self._loading: bool = False

    # ------------------------------------------------------------------
    # Singleton accessor
    # ------------------------------------------------------------------

    @classmethod
    def get(cls) -> Context:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_singleton(cls) -> None:
        """Reset for testing."""
        cls._instance = None

    # ------------------------------------------------------------------
    # Current context
    # ------------------------------------------------------------------

    @property
    def current(self) -> Optional[FabricElement]:
        return self._current

    @current.setter
    def current(self, value: Optional[FabricElement]) -> None:
        self._current = value

    @property
    def path(self) -> str:
        """Human-readable path string for prompt display."""
        if self._current is None:
            return "/"
        return self._current.path

    def reset(self) -> None:
        self._current = None

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    @staticmethod
    def _context_file() -> Path:
        """Per-process context file keyed by parent PID."""
        ppid = os.getppid()
        return _CONFIG_DIR / f"context-{ppid}.json"

    def save(self) -> None:
        """Persist current context to disk (if enabled)."""
        from fabric_cli_v2 import config as cfg

        if cfg.get("context_persistence_enabled") != "true":
            return

        path = self._context_file()
        if self._current is None:
            # Remove stale file
            path.unlink(missing_ok=True)
            return

        data = self._serialise(self._current)
        _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def load(self) -> None:
        """Restore context from disk (if available and enabled)."""
        from fabric_cli_v2 import config as cfg

        if cfg.get("context_persistence_enabled") != "true":
            return

        path = self._context_file()
        if not path.exists():
            return

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            self._current = self._deserialise(data)
        except (json.JSONDecodeError, KeyError, OSError):
            # Corrupted file — silently ignore
            pass

    def cleanup_stale_files(self) -> None:
        """Remove context files for processes that no longer exist."""
        try:
            import psutil  # optional dep; skip if unavailable
        except ImportError:
            return

        active_pids = {p.pid for p in psutil.process_iter(attrs=[])}
        for f in _CONFIG_DIR.glob("context-*.json"):
            try:
                pid = int(f.stem.split("-", 1)[1])
                if pid not in active_pids:
                    f.unlink(missing_ok=True)
            except (ValueError, IndexError):
                pass

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    @staticmethod
    def _serialise(elem: FabricElement) -> dict[str, Any]:
        """Convert element chain to a JSON-safe dict."""
        chain: list[dict[str, Any]] = []
        node: Optional[FabricElement] = elem
        while node is not None:
            chain.append(
                {
                    "name": node.name,
                    "id": node.id,
                    "element_type": node.element_type.value,
                    "item_type": node.item_type.value if node.item_type else None,
                }
            )
            node = node.parent
        chain.reverse()
        return {"chain": chain}

    @staticmethod
    def _deserialise(data: dict[str, Any]) -> FabricElement:
        """Reconstruct element chain from serialised dict."""
        from fabric_cli_v2.types import ItemType  # lazy to avoid circular import

        chain = data["chain"]
        parent: Optional[FabricElement] = None
        elem: Optional[FabricElement] = None
        for entry in chain:
            it = entry.get("item_type")
            elem = FabricElement(
                name=entry["name"],
                element_type=ElementType(entry["element_type"]),
                id=entry.get("id"),
                item_type=ItemType(it) if it else None,
                parent=parent,
            )
            parent = elem
        if elem is None:
            raise KeyError("Empty context chain")
        return elem
