# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Output formatting for Fabric CLI v2.

All user-visible output goes through this module so we have a single
place to control format (text vs JSON), colours, and error rendering.
"""

from __future__ import annotations

import json
import sys
from typing import Any, Optional, Sequence


# ---------------------------------------------------------------------------
# Colour helpers (ANSI escape codes — disabled when not a TTY)
# ---------------------------------------------------------------------------

_USE_COLOUR = sys.stdout.isatty()


def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _USE_COLOUR else text


def grey(text: str) -> str:
    return _c("38;5;243", text)


def green(text: str) -> str:
    return _c("32", text)


def red(text: str) -> str:
    return _c("31", text)


def yellow(text: str) -> str:
    return _c("33", text)


def bold(text: str) -> str:
    return _c("1", text)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def print_json(data: Any) -> None:
    """Pretty-print a JSON-serialisable object."""
    print(json.dumps(data, indent=2, default=str))


def print_table(
    rows: Sequence[dict[str, Any]],
    columns: Optional[list[str]] = None,
) -> None:
    """Print a list of dicts as an aligned table."""
    if not rows:
        return

    cols = columns or list(rows[0].keys())

    # Calculate column widths
    widths = {c: len(c) for c in cols}
    for row in rows:
        for c in cols:
            val = str(row.get(c, ""))
            widths[c] = max(widths[c], len(val))

    # Header
    header = "  ".join(bold(c.ljust(widths[c])) for c in cols)
    print(header)
    print("  ".join("-" * widths[c] for c in cols))

    # Rows
    for row in rows:
        line = "  ".join(str(row.get(c, "")).ljust(widths[c]) for c in cols)
        print(line)


def print_items(
    items: list[dict[str, Any]],
    *,
    long: bool = False,
    output_format: str = "text",
    columns: Optional[list[str]] = None,
) -> None:
    """Print a list of Fabric items in the requested format."""
    if output_format == "json":
        print_json({"value": items})
        return

    if not items:
        return

    if long and columns:
        print_table(items, columns=columns)
    elif long:
        # Auto-detect interesting columns
        cols = [k for k in items[0] if k not in ("description",)]
        print_table(items, columns=cols)
    else:
        # Compact: name + type
        for item in items:
            name = item.get("displayName") or item.get("name", "?")
            itype = item.get("type", "")
            suffix = f".{itype}" if itype else ""
            print(f"  {name}{grey(suffix)}")


def print_error(message: str) -> None:
    """Print an error message to stderr."""
    print(red(f"Error: {message}"), file=sys.stderr)


def print_warning(message: str) -> None:
    """Print a warning to stderr."""
    print(yellow(f"Warning: {message}"), file=sys.stderr)


def print_success(message: str) -> None:
    """Print a success message."""
    print(green(f"✓ {message}"))


def print_info(message: str) -> None:
    """Print an informational message."""
    print(grey(message))
