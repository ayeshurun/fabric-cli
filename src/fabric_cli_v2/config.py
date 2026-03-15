# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Configuration management for Fabric CLI v2.

Stores settings in ``~/.config/fab/config.json`` (same location as v1
so users migrating from v1 keep their settings).

Design goals:
 - Single file, JSON format, human-readable
 - Typed access with defaults
 - No heavy dependencies (stdlib only)
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_CONFIG_DIR = Path(os.environ.get("FAB_CONFIG_DIR", "~/.config/fab")).expanduser()
CONFIG_PATH = _CONFIG_DIR / "config.json"


# ---------------------------------------------------------------------------
# Default settings
# ---------------------------------------------------------------------------

DEFAULTS: dict[str, Any] = {
    # Output
    "output_format": "text",
    # Auth
    "auth_mode": None,  # "user" | "spn" | "managed_identity"
    "tenant_id": None,
    "client_id": None,
    # Behaviour
    "cache_enabled": "true",
    "context_persistence_enabled": "true",
    "debug_enabled": "false",
    "show_hidden": "false",
    "check_updates": "true",
    # Capacity
    "default_capacity": None,
    "default_az_subscription_id": None,
    # Misc
    "default_open_experience": "fabric",
    "folder_listing_enabled": "true",
    "item_sort_criteria": "name",
}


# ---------------------------------------------------------------------------
# Read / write
# ---------------------------------------------------------------------------

_cache: dict[str, Any] | None = None


def _ensure_dir() -> None:
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def read_all() -> dict[str, Any]:
    """Return the full config dict, merged with defaults."""
    global _cache
    if _cache is not None:
        return _cache

    data: dict[str, Any] = {}
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {}

    # Merge defaults for missing keys
    merged = {**DEFAULTS, **data}
    _cache = merged
    return merged


def write_all(data: dict[str, Any]) -> None:
    """Write full config to disk and update cache."""
    global _cache
    _ensure_dir()
    CONFIG_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    _cache = data


def get(key: str) -> Any:
    """Get a single config value (returns default if unset)."""
    return read_all().get(key, DEFAULTS.get(key))


def set_value(key: str, value: Any) -> None:
    """Set a single config value and persist."""
    data = read_all().copy()
    data[key] = value
    write_all(data)


def reset() -> None:
    """Reset config to defaults."""
    write_all(dict(DEFAULTS))


def invalidate_cache() -> None:
    """Force re-read from disk on next access."""
    global _cache
    _cache = None


def init_defaults() -> None:
    """Ensure config file exists with at least the default values."""
    if not CONFIG_PATH.exists():
        _ensure_dir()
        write_all(dict(DEFAULTS))
    else:
        # Backfill any new keys
        data = read_all()
        changed = False
        for k, v in DEFAULTS.items():
            if k not in data:
                data[k] = v
                changed = True
        if changed:
            write_all(data)


# ---------------------------------------------------------------------------
# Valid values (for ``config set`` validation)
# ---------------------------------------------------------------------------

VALID_VALUES: dict[str, list[str]] = {
    "output_format": ["text", "json"],
    "cache_enabled": ["true", "false"],
    "context_persistence_enabled": ["true", "false"],
    "debug_enabled": ["true", "false"],
    "show_hidden": ["true", "false"],
    "check_updates": ["true", "false"],
    "default_open_experience": ["fabric", "powerbi"],
    "folder_listing_enabled": ["true", "false"],
    "item_sort_criteria": ["name", "type"],
}
