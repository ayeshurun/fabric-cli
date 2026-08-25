# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Assert that the black and isort pins agree across every file that declares one.

The formatter versions are declared in three places, each consumed by a different
tool:

* ``tox.toml``               -- what CI's ``tox -e lint`` and ``tox -e format`` install
* ``requirements-dev.txt``   -- what a developer gets from a plain ``pip install``
* ``.pre-commit-config.yaml`` -- what the local pre-commit hooks run

If these drift, "formatted" quietly means different things in different places,
which is the exact failure this repository's formatting setup exists to prevent.

Nothing else catches the drift reliably. CI runs both tox and pre-commit, but that
only fails once two versions actually disagree about *this* codebase -- adjacent
formatter releases usually do not, so a mismatch can sit dormant for months and
then surface in an unrelated pull request. This script compares the declared
versions directly, so drift fails immediately and in the change that introduced it.

Run it locally with::

    python scripts/check_formatter_pins.py

Exits 0 when every pin agrees, 1 otherwise.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

TOOLS = ("black", "isort")


class PinError(Exception):
    """Raised when a file cannot be parsed for the pins it is expected to declare."""


def _read(relative_path: str) -> str:
    path = REPO_ROOT / relative_path
    if not path.is_file():
        raise PinError(f"{relative_path}: expected file is missing")
    return path.read_text(encoding="utf-8")


def _unique(tool: str, source: str, versions: list[str]) -> str:
    """Collapse the versions found in one file, rejecting absence and disagreement."""
    if not versions:
        raise PinError(f"{source}: no pin found for {tool!r}")
    distinct = sorted(set(versions))
    if len(distinct) > 1:
        raise PinError(
            f"{source}: {tool!r} is pinned inconsistently within the same file: "
            + ", ".join(distinct)
        )
    return distinct[0]


def tox_pins() -> dict[str, str]:
    """Read the pins tox installs, across every environment that declares them."""
    content = _read("tox.toml")
    return {
        tool: _unique(
            tool,
            "tox.toml",
            re.findall(rf'"{tool}==([^"]+)"', content),
        )
        for tool in TOOLS
    }


def requirements_pins() -> dict[str, str]:
    """Read the pins a developer gets from requirements-dev.txt."""
    content = _read("requirements-dev.txt")
    return {
        tool: _unique(
            tool,
            "requirements-dev.txt",
            re.findall(rf"^{tool}==(.+)$", content, flags=re.MULTILINE),
        )
        for tool in TOOLS
    }


def pre_commit_pins() -> dict[str, str]:
    """Read the pins pre-commit runs, taken from its ``# frozen:`` annotations.

    ``rev`` holds an opaque commit SHA, so the human-readable version lives in the
    ``# frozen: <version>`` comment that ``pre-commit autoupdate --freeze`` writes.
    Requiring that annotation is deliberate: an unannotated SHA cannot be compared
    against the other files, and this check fails rather than skipping it.
    """
    content = _read(".pre-commit-config.yaml")
    pins: dict[str, str] = {}
    for tool, repo in (("isort", "PyCQA/isort"), ("black", "psf/black")):
        # Match the `rev:` line that follows this hook's `repo:` line, so a future
        # third hook cannot be mistaken for black or isort.
        match = re.search(
            rf"repo:\s*https://github\.com/{re.escape(repo)}\s*\n\s*rev:\s*"
            r"\S+\s*#\s*frozen:\s*(\S+)",
            content,
        )
        if match is None:
            raise PinError(
                f".pre-commit-config.yaml: no '# frozen: <version>' annotation found "
                f"for the {repo} hook"
            )
        pins[tool] = match.group(1)
    return pins


def main() -> int:
    sources = {
        "tox.toml": tox_pins,
        "requirements-dev.txt": requirements_pins,
        ".pre-commit-config.yaml": pre_commit_pins,
    }

    resolved: dict[str, dict[str, str]] = {}
    errors: list[str] = []
    for name, reader in sources.items():
        try:
            resolved[name] = reader()
        except PinError as exc:
            errors.append(str(exc))

    if errors:
        print("Could not read the formatter pins:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    mismatches: list[str] = []
    for tool in TOOLS:
        found = {name: pins[tool] for name, pins in resolved.items()}
        if len(set(found.values())) > 1:
            detail = "\n".join(
                f"    {name}: {version}" for name, version in found.items()
            )
            mismatches.append(f"  {tool} is pinned to different versions:\n{detail}")

    if mismatches:
        print("Formatter pins disagree:", file=sys.stderr)
        print("\n".join(mismatches), file=sys.stderr)
        print(
            "\nUpdate tox.toml, requirements-dev.txt and .pre-commit-config.yaml "
            "together so all three install the same formatter versions.\n"
            "For .pre-commit-config.yaml use `pre-commit autoupdate --freeze`, which "
            "writes both the SHA and the matching `# frozen:` version comment.",
            file=sys.stderr,
        )
        return 1

    for tool in TOOLS:
        print(f"{tool}=={resolved['tox.toml'][tool]} (consistent across all 3 files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
