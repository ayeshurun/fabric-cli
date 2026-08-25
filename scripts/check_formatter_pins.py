# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Verify that the black and isort pins agree across the three files that declare them.

The versions live in three places, and nothing else checks that they match:

  * ``tox.toml``               -- ``[env.lint]`` and ``[env.format]`` deps
  * ``requirements-dev.txt``   -- what a contributor installs locally
  * ``.pre-commit-config.yaml`` -- the ``rev`` pin, whose version is carried in the
    ``# frozen:`` annotation written by ``pre-commit autoupdate --freeze``

Running black and isort in CI only catches a mismatch once two versions happen to
format *this* codebase differently, which can lag a release by months. Comparing the
declared pins catches it immediately.

The check is deliberately strict about *how* a pin is declared, because the failure
mode this guards against is enforcement being silently switched off:

  * every declaration must use ``==``; ``>=`` or a bare name is rejected
  * both tox environments must declare both tools
  * a tool must be declared exactly once per file, so a loose duplicate or a direct
    URL reference cannot sit alongside a good pin and be ignored
  * the pre-commit ``rev`` must be a 40-character SHA, since a tag can be repointed
  * the pre-commit repo must actually enable the hook, so renaming ``id: black``
    cannot leave the formatter disabled while the pins still agree

Structured files are parsed with real parsers (``tomllib``, ``yaml``) rather than
regular expressions. An earlier regex implementation accepted broken configurations
and rejected valid ones -- indented TOML keys, single-quoted strings, inline
comments and interleaved YAML comments are all legal and must not fail the check.

Known limitation: whether a ``rev`` SHA really is the commit tagged for the version
in its ``# frozen:`` annotation cannot be verified offline. Bump the pins with
``pre-commit autoupdate --freeze`` so the two are written together.

Exits 0 when the pins agree, 1 otherwise.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Iterable

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised only on Python 3.10
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ModuleNotFoundError:  # pragma: no cover
        sys.exit(
            "check_formatter_pins requires Python 3.11+ for tomllib, or the 'tomli' "
            "backport on 3.10. Install the dev requirements: "
            "pip install -r requirements-dev.txt"
        )

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent

TOX = "tox.toml"
REQUIREMENTS = "requirements-dev.txt"
PRE_COMMIT = ".pre-commit-config.yaml"

# Tool name -> the pre-commit repository that provides its hook. The hook id is
# assumed to equal the tool name, which is true for both hooks used here.
TOOLS = {
    "black": "https://github.com/psf/black",
    "isort": "https://github.com/PyCQA/isort",
}

# The tox environments that are required to pin the formatters. Hardcoded on
# purpose: these environments are the contract, so renaming one should force
# whoever renames it to update this check as well.
TOX_ENVS = ("lint", "format")

FULL_SHA = re.compile(r"\A[0-9a-f]{40}\Z")

# name[extras] <operator> version, with an optional environment marker. Inline
# comments are stripped before this is applied.
REQUIREMENT = re.compile(
    r"""
    \A\s*
    (?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)   # distribution name
    \s*(?:\[[^\]]*\])?                     # optional extras
    \s*(?P<operator>[=!<>~]=|[<>])?        # optional comparison operator
    \s*(?P<version>[^;\s]+)?               # optional version
    \s*(?:;.*)?                            # optional environment marker
    \Z
    """,
    re.VERBOSE,
)


class PinError(Exception):
    """A pin is missing, malformed, or inconsistent."""


def _normalise(name: str) -> str:
    """Normalise a distribution name per PEP 503."""
    return re.sub(r"[-_.]+", "-", name).lower()


def _read(relative: str) -> str:
    path = REPO_ROOT / relative
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise PinError(f"{relative}: not found (expected at {path})") from None
    except UnicodeDecodeError as exc:
        raise PinError(f"{relative}: is not valid UTF-8 ({exc.reason})") from None
    except OSError as exc:
        raise PinError(f"{relative}: could not be read ({exc.strerror})") from None
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _strip_comment(line: str) -> str:
    """Remove a trailing ``#`` comment from a requirements line."""
    return line.split("#", 1)[0].strip()


def _exact_version(spec: str, tool: str, where: str) -> str | None:
    """Return the pinned version if ``spec`` pins ``tool``, else None.

    Raises if the spec names the tool but does not pin it with ``==``.
    """
    spec = spec.strip()
    if not spec:
        return None

    # PEP 508 direct reference, e.g. "black @ https://...". Never a valid pin.
    if "@" in spec:
        name = spec.split("@", 1)[0].strip()
        if _normalise(name) == tool:
            raise PinError(
                f"{where}: {tool!r} is declared as a direct reference ({spec!r}); "
                f"pin it with '{tool}==<version>' instead"
            )
        return None

    match = REQUIREMENT.match(spec)
    if match is None:
        return None
    if _normalise(match.group("name")) != tool:
        return None

    operator = match.group("operator")
    version = match.group("version")
    if operator != "==" or not version:
        raise PinError(
            f"{where}: {tool!r} is not pinned exactly ({spec!r}); "
            f"use '{tool}==<version>'"
        )
    return version


def _single(versions: list[str], tool: str, where: str) -> str:
    """Require exactly one declaration of ``tool`` in ``where``."""
    if not versions:
        raise PinError(f"{where}: no exact pin found for {tool!r}")
    if len(versions) > 1:
        raise PinError(
            f"{where}: {tool!r} is declared {len(versions)} times "
            f"({', '.join(sorted(set(versions)))}); declare it exactly once"
        )
    return versions[0]


def _scan(specs: Iterable[str], tool: str, where: str) -> str:
    found = [v for v in (_exact_version(s, tool, where) for s in specs) if v]
    return _single(found, tool, where)


def tox_pins(tool: str) -> str:
    """Return the version ``tool`` is pinned to in every required tox environment."""
    try:
        data = tomllib.loads(_read(TOX))
    except tomllib.TOMLDecodeError as exc:
        raise PinError(f"{TOX}: is not valid TOML ({exc})") from None

    envs = data.get("env")
    if not isinstance(envs, dict):
        raise PinError(f"{TOX}: has no [env.*] sections")

    versions: dict[str, str] = {}
    for env_name in TOX_ENVS:
        env = envs.get(env_name)
        if not isinstance(env, dict):
            raise PinError(f"{TOX}: has no [env.{env_name}] section")
        deps = env.get("deps")
        if not isinstance(deps, list):
            raise PinError(
                f"{TOX}: [env.{env_name}] has no 'deps' array; it is expected to "
                f"pin {tool!r}"
            )
        where = f"{TOX} [env.{env_name}]"
        versions[where] = _scan([d for d in deps if isinstance(d, str)], tool, where)

    return _collapse(versions, tool)


def requirements_pins(tool: str) -> str:
    specs = []
    for raw in _read(REQUIREMENTS).splitlines():
        line = _strip_comment(raw)
        # Skip blank lines and pip options such as "-r base.txt" or "--index-url".
        if not line or line.startswith("-"):
            continue
        specs.append(line)
    return _scan(specs, tool, REQUIREMENTS)


def pre_commit_pins(tool: str) -> str:
    text = _read(PRE_COMMIT)
    try:
        config = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise PinError(f"{PRE_COMMIT}: is not valid YAML ({exc})") from None

    if not isinstance(config, dict) or not isinstance(config.get("repos"), list):
        raise PinError(f"{PRE_COMMIT}: has no 'repos' list")

    url = TOOLS[tool]
    matches = [
        r
        for r in config["repos"]
        if isinstance(r, dict) and str(r.get("repo", "")).rstrip("/") == url
    ]
    if not matches:
        raise PinError(f"{PRE_COMMIT}: no repo entry for {url}")
    if len(matches) > 1:
        raise PinError(
            f"{PRE_COMMIT}: {len(matches)} repo entries for {url}; "
            "declare it exactly once"
        )
    repo = matches[0]

    hooks = repo.get("hooks")
    if not isinstance(hooks, list):
        raise PinError(f"{PRE_COMMIT}: the {url} entry has no 'hooks' list")
    ids = {h.get("id") for h in hooks if isinstance(h, dict)}
    if tool not in ids:
        raise PinError(
            f"{PRE_COMMIT}: the {url} entry does not enable the {tool!r} hook "
            f"(found {sorted(i for i in ids if i)}); the pins would agree while "
            f"{tool} never runs"
        )

    rev = str(repo.get("rev", "")).strip()
    if not FULL_SHA.match(rev):
        raise PinError(
            f"{PRE_COMMIT}: rev for {url} is {rev!r}, not a 40-character commit "
            "SHA; a tag can be repointed and is not a reproducible pin"
        )

    # The version itself only exists in the "# frozen:" comment, which the YAML
    # parser discards, so read it from the line carrying this exact rev.
    annotation = re.search(
        rf"^\s*rev:\s*{rev}\s*#\s*frozen:\s*(\S+)\s*$", text, re.MULTILINE
    )
    if annotation is None:
        raise PinError(
            f"{PRE_COMMIT}: rev for {url} has no '# frozen: <version>' annotation; "
            "bump it with 'pre-commit autoupdate --freeze' so the version is "
            "recorded alongside the SHA"
        )
    return annotation.group(1)


def _collapse(versions: dict[str, str], tool: str) -> str:
    distinct = sorted(set(versions.values()))
    if len(distinct) > 1:
        detail = ", ".join(f"{where} -> {v}" for where, v in sorted(versions.items()))
        raise PinError(f"{tool}: pins disagree ({detail})")
    return distinct[0]


def main() -> int:
    errors: list[str] = []
    for tool in sorted(TOOLS):
        found: dict[str, str] = {}
        for label, reader in (
            (TOX, tox_pins),
            (REQUIREMENTS, requirements_pins),
            (PRE_COMMIT, pre_commit_pins),
        ):
            try:
                found[label] = reader(tool)
            except PinError as exc:
                errors.append(str(exc))

        if len(found) == 3:
            try:
                version = _collapse(found, tool)
            except PinError as exc:
                errors.append(str(exc))
            else:
                print(f"{tool}=={version} (consistent across all 3 files)")

    if errors:
        print("\nFormatter pins are inconsistent:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        print(
            "\nThe black and isort versions in tox.toml, requirements-dev.txt and "
            ".pre-commit-config.yaml must match, or CI, pre-commit and local runs "
            "will disagree about what 'formatted' means.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
