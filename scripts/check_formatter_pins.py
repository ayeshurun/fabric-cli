# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Assert that the black and isort pins agree across every file that declares one.

The formatter versions are declared in three places, each consumed by a different
tool:

* ``tox.toml``                -- what CI's ``tox -e lint`` and ``tox -e format`` install
* ``requirements-dev.txt``    -- what a developer gets from a plain ``pip install``
* ``.pre-commit-config.yaml`` -- what the local pre-commit hooks run

If these drift, "formatted" quietly means different things in different places,
which is the exact failure this repository's formatting setup exists to prevent.

Nothing else catches the drift reliably. CI runs both tox and pre-commit, but that
only fails once two versions actually disagree about *this* codebase -- adjacent
formatter releases usually do not, so a mismatch can sit dormant for months and
then surface in an unrelated pull request. This script compares the declared
versions directly, so drift fails immediately and in the change that introduced it.

It validates *structure*, not just the presence of a matching string: every
location that is expected to carry a pin must carry an exact ``==`` pin. Counting
occurrences is not enough, because loosening one of two declarations to ``>=`` or
deleting it leaves the remaining one self-consistent and would otherwise pass.

Known limitation: for pre-commit, ``rev`` is an opaque commit SHA and the version
is read from the ``# frozen: <version>`` annotation beside it. Whether that SHA
really is that release cannot be checked offline, so a hand-edited SHA with a
stale annotation is not detected. Bump those hooks with
``pre-commit autoupdate --freeze``, which rewrites both together.

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

# Every tox environment that installs the formatters. Both must pin them, and
# identically: `lint` decides whether CI passes, `format` decides what a
# contributor's files are rewritten to.
TOX_ENVS = ("lint", "format")

PRE_COMMIT_REPOS = {"isort": "PyCQA/isort", "black": "psf/black"}

FULL_SHA = re.compile(r"\A[0-9a-f]{40}\Z")

# name[extras] <operator> version, with an optional environment marker.
REQUIREMENT = re.compile(
    r"""\A\s*
    (?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)   # distribution name
    \s*(?:\[[^\]]*\])?                     # optional extras
    \s*(?P<operator>[=!<>~^]+)?            # optional version operator
    \s*(?P<version>[^;\s#]+)?              # optional version
    \s*(?:;.*)?                            # optional environment marker
    \Z""",
    re.VERBOSE,
)


class PinError(Exception):
    """Raised when a file cannot be parsed for the pins it is expected to declare."""


def _normalise(name: str) -> str:
    """Normalise a distribution name the way packaging tools do (PEP 503)."""
    return re.sub(r"[-_.]+", "-", name).lower()


def _read(relative_path: str) -> str:
    path = REPO_ROOT / relative_path
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise PinError(f"{relative_path}: expected file is missing") from None
    except UnicodeDecodeError as exc:
        raise PinError(f"{relative_path}: is not valid UTF-8 ({exc})") from None
    except OSError as exc:
        raise PinError(f"{relative_path}: could not be read ({exc})") from None
    # Normalise line endings so a CRLF checkout parses identically.
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _exact_version(spec: str, tool: str, source: str, where: str) -> str | None:
    """Return the pinned version if ``spec`` pins ``tool`` exactly, else None.

    Raises if ``spec`` names the tool but does not pin it to a single version,
    since a range makes the declaration unenforceable.
    """
    match = REQUIREMENT.match(spec)
    if match is None or _normalise(match.group("name")) != tool:
        return None
    operator, version = match.group("operator"), match.group("version")
    if operator != "==" or not version:
        raise PinError(
            f"{source}: {where} declares {tool!r} as {spec.strip()!r}; it must be "
            f"pinned exactly, as '{tool}==<version>'"
        )
    return version


def _collapse(tool: str, source: str, found: dict[str, str]) -> str:
    """Collapse per-location versions, rejecting disagreement within one file."""
    distinct = sorted(set(found.values()))
    if len(distinct) > 1:
        detail = ", ".join(
            f"{where}={version}" for where, version in sorted(found.items())
        )
        raise PinError(
            f"{source}: {tool!r} is pinned inconsistently within the same file: {detail}"
        )
    return distinct[0]


def _tox_deps(content: str, env: str) -> list[str] | None:
    """Return the quoted entries of ``[env.<env>]``'s ``deps`` array, or None."""
    section = re.search(
        rf"^\[env\.{re.escape(env)}\]\s*$(.*?)(?=^\[|\Z)",
        content,
        flags=re.MULTILINE | re.DOTALL,
    )
    if section is None:
        return None
    body = section.group(1)
    start = re.search(r"^deps\s*=\s*\[", body, re.MULTILINE)
    if start is None:
        return None
    # Scan to the bracket that closes the array rather than to the first ']', so
    # an entry containing brackets -- `black[jupyter]==26.5.1` -- still parses.
    depth, in_string, end = 0, False, None
    for index in range(start.end() - 1, len(body)):
        char = body[index]
        if in_string:
            if char == "\\":
                continue
            if char == '"':
                in_string = False
        elif char == '"':
            in_string = True
        elif char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                end = index
                break
    if end is None:
        raise PinError(f"tox.toml: [env.{env}]'s 'deps' array is not closed")
    return re.findall(r'"([^"]*)"', body[start.end() : end])


def tox_pins() -> dict[str, str]:
    """Read the pins tox installs, requiring every formatter env to declare them."""
    content = _read("tox.toml")
    pins: dict[str, str] = {}
    for tool in TOOLS:
        found: dict[str, str] = {}
        for env in TOX_ENVS:
            deps = _tox_deps(content, env)
            if deps is None:
                raise PinError(
                    f"tox.toml: no '[env.{env}]' section with a 'deps' array was found; "
                    f"it is expected to pin {' and '.join(TOOLS)}"
                )
            versions = [
                version
                for spec in deps
                if (version := _exact_version(spec, tool, "tox.toml", f"[env.{env}]"))
            ]
            if not versions:
                raise PinError(f"tox.toml: [env.{env}] does not pin {tool!r}")
            found[f"[env.{env}]"] = _collapse(
                tool,
                "tox.toml",
                {f"[env.{env}]#{i}": v for i, v in enumerate(versions)},
            )
        pins[tool] = _collapse(tool, "tox.toml", found)
    return pins


def requirements_pins() -> dict[str, str]:
    """Read the pins a developer gets from requirements-dev.txt."""
    content = _read("requirements-dev.txt")
    lines = [
        line
        for line in content.splitlines()
        if line.strip() and not line.lstrip().startswith(("#", "-"))
    ]
    pins: dict[str, str] = {}
    for tool in TOOLS:
        found = {
            line.strip(): version
            for line in lines
            if (version := _exact_version(line, tool, "requirements-dev.txt", "entry"))
        }
        if not found:
            raise PinError(f"requirements-dev.txt: no exact pin found for {tool!r}")
        pins[tool] = _collapse(tool, "requirements-dev.txt", found)
    return pins


def pre_commit_pins() -> dict[str, str]:
    """Read the pins pre-commit runs, taken from its ``# frozen:`` annotations.

    ``rev`` holds an opaque commit SHA, so the human-readable version lives in the
    ``# frozen: <version>`` comment that ``pre-commit autoupdate --freeze`` writes.
    Requiring that annotation is deliberate: an unannotated SHA cannot be compared
    against the other files, and this check fails rather than skipping it.
    """
    source = ".pre-commit-config.yaml"
    content = _read(source)
    pins: dict[str, str] = {}
    for tool, repo in PRE_COMMIT_REPOS.items():
        # Anchor to this hook's `repo:` line so a future third hook cannot be
        # mistaken for black or isort, and collect *every* match so a duplicated
        # repo block at a second revision is rejected rather than ignored.
        matches = re.findall(
            rf"repo:\s*https://github\.com/{re.escape(repo)}/?\s*\n\s*rev:\s*"
            r"(\S+)[^\S\n]*(?:#[^\S\n]*frozen:[^\S\n]*(\S+))?",
            content,
        )
        if not matches:
            raise PinError(f"{source}: no hook found for {repo}")
        if len(matches) > 1:
            raise PinError(
                f"{source}: {repo} is declared {len(matches)} times; "
                f"expected exactly one so its pin is unambiguous"
            )
        rev, frozen = matches[0]
        if not frozen:
            raise PinError(
                f"{source}: the {repo} hook has no '# frozen: <version>' annotation. "
                f"Bump it with `pre-commit autoupdate --freeze`."
            )
        if not FULL_SHA.match(rev):
            raise PinError(
                f"{source}: the {repo} hook is pinned to {rev!r}, which is not a "
                f"full-length commit SHA. A tag can be repointed by its maintainer, "
                f"so it is not a reproducible pin."
            )
        pins[tool] = frozen
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
