# RFC-001: Migration from argparse to Typer

**Status**: Proposal  
**Authors**: Fabric CLI Contributors  
**Created**: 2026-03-13  
**Target**: Fabric CLI v2.0 (Major Version)

---

## Summary

This RFC evaluates migrating the Fabric CLI (`fab`) from Python's built-in `argparse` to [Typer](https://typer.tiangolo.com/) for command-line argument parsing. The analysis covers technical feasibility, value proposition, risks, and a recommended phased migration approach.

---

## Table of Contents

1. [Current Architecture](#1-current-architecture)
2. [Why Consider Typer?](#2-why-consider-typer)
3. [Detailed Comparison](#3-detailed-comparison)
4. [Impact Analysis](#4-impact-analysis)
5. [Risk Assessment](#5-risk-assessment)
6. [Recommended Approach](#6-recommended-approach)
7. [Migration Plan](#7-migration-plan)
8. [Proof of Concept](#8-proof-of-concept)
9. [Decision Matrix](#9-decision-matrix)
10. [Conclusion](#10-conclusion)

---

## 1. Current Architecture

### Scale

| Component | Count | Lines of Code |
|-----------|-------|---------------|
| Parser modules | 13 | ~2,000 |
| Command files | 136 | ~10,000+ |
| Test files | ~50+ | ~17,000 |
| Custom parser classes | 2 | ~140 |
| Registered commands | 61 | - |

### Key Components

- **`CustomArgumentParser`** (`fab_parser_setup.py`): Extended argparse with mode-aware error handling, custom help delegation, and additional attributes (`fab_examples`, `fab_aliases`, `fab_learnmore`).
- **`CustomHelpFormatter`** (`fab_parser_setup.py`): Custom help output with renamed sections (Flags, Arg(s)), appended Examples/Aliases/Learn More sections, and ANSI-colored comments.
- **Parser Registration Pattern**: Each area module exposes `register_*_parser(subparsers)` functions that attach subcommands to a shared `_SubParsersAction`.
- **Interactive Mode** (`fab_interactive.py`): Uses `prompt_toolkit` + `shlex.split()` + re-parsing through the same argparse parser tree, with `SystemExit` catching.
- **Shell Completion**: `argcomplete` with custom completers per argument.
- **Lazy Loading**: Deferred imports for heavy modules (questionary), but all parsers loaded eagerly at startup.
- **Test Infrastructure**: `CLIExecutor` wraps `InteractiveCLI` for command execution in tests.

### Custom Argparse Extensions

```
fab_examples   → List of example strings (comments greyed with ANSI)
fab_aliases    → Alternative command names (e.g., dir = ls)
fab_learnmore  → Documentation links (["_"] = default link)
```

These are **not natively supported** by argparse and required custom `HelpFormatter` + `ArgumentParser` subclasses.

---

## 2. Why Consider Typer?

### Motivations from the Problem Statement

| Goal | argparse (Current) | Typer (Proposed) |
|------|-------------------|------------------|
| **UX** | Custom help formatting needed | Rich help formatting built-in, colored output, better error messages |
| **Performance** | All parsers loaded eagerly; ~2K lines parsed at startup | Lazy command loading via `@app.command()` + `lazy_group` |
| **Scalability** | Each new command needs parser boilerplate (~20-30 lines) | Commands defined as typed functions (~5-10 lines) |
| **Maintenance** | Custom classes to maintain (`CustomArgumentParser`, `CustomHelpFormatter`) | Built-in support for most custom features |

### What Typer Brings

1. **Type-hint-driven commands**: Commands are regular Python functions with type annotations
2. **Built on Click**: Battle-tested Click library underneath
3. **Rich integration**: Beautiful help text, error messages, and progress bars via `rich`
4. **Auto-completion**: Built-in shell completion (replaces `argcomplete`)
5. **Nested command groups**: Native support for `app.add_typer()` hierarchies
6. **Testing**: `typer.testing.CliRunner` for isolated command testing
7. **Reduced boilerplate**: ~60-70% less parser code per command

---

## 3. Detailed Comparison

### Command Definition: Before vs After

**Current (argparse) — 30 lines:**
```python
# fab_config_parser.py
def register_parser(subparsers):
    parser = subparsers.add_parser("config", help="Manage CLI config")
    parser.set_defaults(func=show_help)
    config_subparsers = parser.add_subparsers(dest="config_subcommand")
    
    parser_set = config_subparsers.add_parser(
        "set", help="Set a configuration value",
        fab_examples=["$ config set mode command_line"],
        fab_learnmore=["_"],
    )
    parser_set.add_argument("key", metavar="<key>", help="Configuration key")
    parser_set.add_argument("value", metavar="<value>", help="Configuration value")
    parser_set.set_defaults(func=config.set_config)
```

**Proposed (Typer) — 12 lines:**
```python
# config_commands.py
import typer

config_app = typer.Typer(help="Manage CLI configuration")

@config_app.command()
def set(
    key: str = typer.Argument(help="Configuration key"),
    value: str = typer.Argument(help="Configuration value"),
):
    """Set a configuration value.
    
    Example: $ config set mode command_line
    """
    config_set.exec_command(key, value)
```

### Help Output Comparison

**Current (argparse + CustomHelpFormatter):**
```
Usage: fab config set <key> <value>

Arg(s):
  <key>     Configuration key
  <value>   Configuration value

Examples:
  # switch to command line mode
  $ config set mode command_line

Learn more:
  For more usage examples, see https://aka.ms/fabric-cli
```

**Proposed (Typer + Rich):**
```
 Usage: fab config set [OPTIONS] KEY VALUE

 Set a configuration value.

╭─ Arguments ──────────────────────────────────╮
│ *  KEY    Configuration key [required]       │
│ *  VALUE  Configuration value [required]     │
╰──────────────────────────────────────────────╯

 Examples:
  # switch to command line mode
  $ config set mode command_line

 Learn more:
  https://aka.ms/fabric-cli
```

### Feature Mapping

| Feature | argparse (Current) | Typer (Migration Path) |
|---------|-------------------|----------------------|
| Subcommands | `add_subparsers()` + `add_parser()` | `typer.Typer()` + `app.add_typer()` |
| Positional args | `add_argument("path")` | `path: str = typer.Argument()` |
| Optional flags | `add_argument("-l", "--long")` | `long: bool = typer.Option("--long", "-l")` |
| Boolean flags | `action="store_true"` | `flag: bool = typer.Option(False)` |
| Choices | `choices=["json", "text"]` | `format: Format = typer.Option()` with `Enum` |
| Default values | `default=None` | Python default values |
| Help text | `help="..."` | `typer.Argument(help="...")` or docstring |
| Aliases | `aliases=["dir"]` | Not built-in; use Click group customization |
| fab_examples | Custom formatter | Epilog or `rich_help_panel` customization |
| fab_learnmore | Custom formatter | Epilog customization |
| Shell completion | `argcomplete` | Built-in Click completion |
| Error handling | `parser.error()` override | Click exception handling + callbacks |
| Mode tracking | `parser.fab_mode` | Context object or global state |

---

## 4. Impact Analysis

### Files Requiring Changes

| Area | Files | Effort | Risk |
|------|-------|--------|------|
| **Core parser setup** | `fab_parser_setup.py` | High (rewrite) | High |
| **Parser modules** | 13 files in `parsers/` | High (rewrite all) | Medium |
| **Main entry point** | `main.py` | High (rewrite) | High |
| **Interactive mode** | `fab_interactive.py` | High (rethink) | High |
| **Command implementations** | 136 files in `commands/` | Medium (adapt `args` access) | Medium |
| **Test infrastructure** | `commands_parser.py` + all tests | High (rewrite) | Medium |
| **Shell completion** | `scripts/completion/` | Low (replace) | Low |
| **Global params** | `fab_global_params.py` | Low (integrate into Typer) | Low |
| **Error handling** | `fab_error_parser.py` | Medium (adapt) | Medium |
| **Dependencies** | `pyproject.toml` | Low (add typer, remove argcomplete) | Low |

### What Can Be Preserved

- All command implementations (`exec_command()` functions) — these are argparse-agnostic
- Error types and messages (`FabricCLIError`, error codes)
- API client and network logic
- Configuration management
- Output formatting (`print_output_format`)
- Decorators (`handle_exceptions`, `set_command_context`)
- Context and navigation hierarchy

### What Must Change

- All 13 parser modules → Typer command groups
- `CustomArgumentParser` and `CustomHelpFormatter` → Typer help panels
- `main.py` entry point → Typer app invocation
- `fab_interactive.py` → New interactive dispatch
- `CLIExecutor` test helper → `CliRunner` based testing
- `argcomplete` → Typer/Click completion

---

## 5. Risk Assessment

### High Risks

| Risk | Mitigation |
|------|------------|
| **Interactive mode breakage** | Typer can invoke commands programmatically; test thoroughly |
| **Shell completion regression** | Typer has built-in completion; verify feature parity |
| **Custom help formatting loss** | Implement Typer callback for epilog/examples; use `rich_help_panel` |
| **Massive PR scope** | Phased migration with coexistence period |
| **Test suite breakage** | Migrate tests alongside commands; maintain CLIExecutor compat |

### Medium Risks

| Risk | Mitigation |
|------|------------|
| **`args.Namespace` access patterns** | Adapt command implementations to accept typed params |
| **Alias support** | Typer doesn't natively support aliases; use Click's underlying API |
| **`-c` multi-command execution** | Implement as Typer callback or custom invoke |
| **Performance regression** | Typer's lazy loading should improve startup; benchmark |

### Low Risks

| Risk | Mitigation |
|------|------------|
| **Dependency addition (typer, click, rich)** | Well-maintained, widely used libraries |
| **Python version compat** | Typer supports 3.7+; our minimum is 3.10 |

---

## 6. Recommended Approach

### Strategy: Phased Migration with Compatibility Layer

**Do NOT attempt a big-bang rewrite.** Instead:

1. **Phase 0** (This PR): Analysis + PoC for one command group
2. **Phase 1**: Create Typer app skeleton + compatibility layer for `args.Namespace`
3. **Phase 2**: Migrate command groups one at a time (config → auth → jobs → fs...)
4. **Phase 3**: Remove argparse infrastructure, update tests
5. **Phase 4**: Enhance with Typer-native features (rich help, better completion)

### Key Design Decisions

#### A. Compatibility Layer (`TyperArgs`)

To minimize changes to 136 command files, create a compatibility layer that converts Typer parameters into an `argparse.Namespace`-like object:

```python
class TyperArgs:
    """Compatibility layer: Typer params → argparse.Namespace-like object."""
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
```

This allows existing `exec_command(args)` functions to work unchanged during migration.

#### B. Interactive Mode

Replace `shlex.split()` + argparse re-parsing with Typer's programmatic invocation:

```python
# Instead of: subparser.parse_args(command_parts[1:])
# Use: app(command_parts, standalone_mode=False)
```

#### C. Custom Help (fab_examples, fab_learnmore)

Use Typer's `epilog` parameter and Click's `rich_help_panel`:

```python
@app.command(
    epilog="Examples:\\n  $ config set mode command_line\\n\\n"
           "Learn more:\\n  https://aka.ms/fabric-cli"
)
def set(key: str, value: str):
    ...
```

Or implement a custom `TyperGroup` class that adds these sections.

#### D. Aliases

Use Click's underlying `@app.command(name="ls")` plus register the same callback with `@app.command(name="dir")`, or use a custom `AliasGroup`.

---

## 7. Migration Plan

### Phase 0: Analysis + PoC (This PR)

- [x] Analyze current architecture
- [x] Document RFC
- [x] PoC: Migrate `config` command group to Typer
- [x] Validate: Tests pass, help output is equivalent

### Phase 1: Infrastructure (Estimated: 1-2 weeks)

- [ ] Add `typer[all]` dependency
- [ ] Create `FabTyperApp` base class with custom help
- [ ] Create `TyperArgs` compatibility layer
- [ ] Create Typer-based `main()` entry point (coexisting with argparse)
- [ ] Port interactive mode to use Typer invocation
- [ ] Port shell completion scripts

### Phase 2: Command Migration (Estimated: 2-4 weeks)

Migrate in order of complexity (simplest first):

1. [ ] `config` (4 subcommands, no path resolution)
2. [ ] `auth` (4 subcommands, special flow)
3. [ ] `labels` (4 subcommands)
4. [ ] `tables` (5 subcommands)
5. [ ] `acls` (5 subcommands)
6. [ ] `jobs` (9 subcommands)
7. [ ] `api` (1 command, complex args)
8. [ ] `describe` (1 command)
9. [ ] `fs` (20 commands — largest, most complex)

### Phase 3: Cleanup (Estimated: 1 week)

- [ ] Remove `CustomArgumentParser` and `CustomHelpFormatter`
- [ ] Remove all `fab_*_parser.py` modules
- [ ] Remove `argcomplete` dependency
- [ ] Update `CLIExecutor` to use `CliRunner`
- [ ] Update all test files

### Phase 4: Enhancement (Ongoing)

- [ ] Add `rich` progress bars for long operations
- [ ] Improve error messages with `rich` formatting
- [ ] Add command auto-suggestions on typo
- [ ] Add `--help` panels for grouped options

---

## 8. Proof of Concept

A proof-of-concept implementation is included in this PR:

- **File**: `src/fabric_cli/typer_poc/config_app.py` — Typer-based config commands
- **File**: `src/fabric_cli/typer_poc/__init__.py` — Package init
- **File**: `tests/test_typer_poc/test_config_typer.py` — Tests for the PoC

The PoC demonstrates:
- Typer command group with subcommands (set, get, ls, clear-cache)
- Custom help with examples and learn more sections via epilog
- Compatibility layer (`TyperArgs`) for existing `exec_command(args)` functions
- Testing with `typer.testing.CliRunner`
- Feature parity with current argparse implementation

---

## 9. Decision Matrix

| Criterion | Weight | argparse | Typer | Notes |
|-----------|--------|----------|-------|-------|
| **UX Quality** | 25% | 6/10 | 9/10 | Typer: colored help, better errors, panels |
| **Developer Experience** | 20% | 5/10 | 9/10 | Typer: type hints, less boilerplate |
| **Performance** | 15% | 6/10 | 8/10 | Typer: lazy groups, faster startup potential |
| **Scalability** | 15% | 5/10 | 9/10 | Typer: ~70% less code per command |
| **Maintenance** | 15% | 5/10 | 8/10 | Typer: no custom parser classes needed |
| **Migration Cost** | 10% | 10/10 | 3/10 | Significant effort for 136 commands |
| **Weighted Score** | 100% | **5.9** | **8.0** | **Typer wins by 2.1 points** |

---

## 10. Conclusion

### Recommendation: **Proceed with Migration**

The migration from argparse to Typer is **justified and recommended** for a v2.0 release based on:

1. **Clear UX improvement**: Rich-formatted help, colored output, better error messages
2. **Significant code reduction**: ~60-70% less parser boilerplate (from ~2,000 lines to ~600)
3. **Better developer experience**: Type-safe commands, less manual wiring
4. **Modern Python patterns**: Aligns with Python community best practices
5. **Reduced maintenance**: Eliminates ~140 lines of custom parser infrastructure

### Key Conditions

1. **Phased migration** — never a big-bang rewrite
2. **Compatibility layer** — existing `exec_command(args)` must work during transition
3. **Interactive mode validation** — must maintain feature parity
4. **Test migration** — each phase must include test updates
5. **Performance benchmarks** — startup time must not regress

### Estimated Total Effort

| Phase | Effort | Duration |
|-------|--------|----------|
| Phase 0 (PoC) | 1 developer | This PR |
| Phase 1 (Infrastructure) | 1-2 developers | 1-2 weeks |
| Phase 2 (Commands) | 2-3 developers | 2-4 weeks |
| Phase 3 (Cleanup) | 1 developer | 1 week |
| Phase 4 (Enhancement) | Ongoing | Continuous |
| **Total** | | **4-7 weeks** |

---

## Appendix A: Dependencies to Add

```toml
# pyproject.toml
dependencies = [
    "typer[all]>=0.15.0",  # Includes click, rich, shellingham
    # Remove: "argcomplete>=3.6.2",
]
```

## Appendix B: Key Typer Resources

- [Typer Documentation](https://typer.tiangolo.com/)
- [Typer GitHub](https://github.com/fastapi/typer)
- [Click Documentation](https://click.palletsprojects.com/)
- [Rich Documentation](https://rich.readthedocs.io/)
