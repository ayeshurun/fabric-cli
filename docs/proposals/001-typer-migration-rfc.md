# RFC 001: Fabric CLI v2 — Typer Migration, SDK Integration & Early Failure Detection

| Field        | Value                                  |
|--------------|----------------------------------------|
| **Status**   | Draft                                  |
| **Authors**  | Fabric CLI Team                        |
| **Created**  | 2026-03-13                             |
| **Target**   | Fabric CLI v2.0.0                      |

---

## 1. Summary

This RFC proposes three major architectural changes for a new major version of Fabric CLI:

1. **Migrate from `argparse` to `typer`** for the CLI framework
2. **Integrate the `microsoft-fabric-api` Python SDK** for standardized REST API calls
3. **Implement early failure detection** to validate commands before executing API calls

These changes aim to improve developer experience, reduce maintenance burden, increase type-safety, and provide better error messages to users.

---

## 2. Motivation

### 2.1 Current State

The Fabric CLI (`fab`) is built on:
- **argparse** (standard library) for CLI argument parsing — 13 parser modules, 61+ commands
- **requests** (raw HTTP) for all REST API calls — 17 custom API client modules with 70+ functions
- **No pre-execution validation** — errors are discovered only when API calls fail

### 2.2 Pain Points

| Area                    | Current Issue                                                                                     |
|-------------------------|---------------------------------------------------------------------------------------------------|
| **Parser boilerplate**  | Each command requires 15–30 lines of `add_argument()` calls; CustomHelpFormatter is 110 lines    |
| **Type safety**         | Arguments arrive as `Namespace` objects with no type checking; `getattr()` everywhere             |
| **Shell completion**    | Requires `argcomplete` as a separate dependency; limited completion quality                       |
| **Help output**         | Custom formatter patches `usage:`, `options:`, etc.; fragile regex-based formatting               |
| **API client code**     | 17 separate `fab_api_*.py` files with hand-crafted URL building, response parsing, retry logic    |
| **Error discovery**     | Unsupported command+item type combinations fail only after authentication and API call            |
| **Testing**             | Mocking raw HTTP is verbose; hard to test business logic independently                            |

### 2.3 Goals

- **Reduce boilerplate** by ≥50% for command definitions
- **Increase type safety** with Python type hints driving CLI behavior
- **Improve UX** with richer help, auto-completion, and clear error messages
- **Standardize API calls** using an official SDK with built-in auth, retry, and pagination
- **Fail fast** when a command/item combination is unsupported before making network calls

---

## 3. Analysis

### 3.1 Typer Migration

#### 3.1.1 Why Typer?

| Aspect              | argparse (current)                              | Typer (proposed)                                     |
|----------------------|------------------------------------------------|------------------------------------------------------|
| **Definition style** | Imperative `add_argument()` calls              | Declarative type hints on function params            |
| **Subcommands**      | Manual `add_subparsers()` + registration       | `@app.command()` decorator, `app.add_typer()`        |
| **Type validation**  | Manual `type=int`, `choices=[...]`             | Automatic from Python type hints and `Enum`          |
| **Help generation**  | Basic; needs CustomHelpFormatter               | Rich, auto-generated from docstrings + type hints    |
| **Shell completion**  | Requires argcomplete; limited                  | Built-in for Bash, Zsh, Fish, PowerShell             |
| **Testing**          | Must mock `sys.argv`                           | `CliRunner` from Click/Typer for isolated testing    |
| **Error handling**   | Override `parser.error()` method               | Callback-based; type-validated before handler runs   |
| **Dependencies**     | None (stdlib)                                  | `typer` (pulls `click`, `rich` optionally)           |
| **Maintenance**      | Active, but no new features                    | Actively maintained; v0.9.x with Pydantic support    |

#### 3.1.2 Impact Assessment

**Positive:**
- ~50% reduction in parser code (from ~650 lines across 13 parser files to ~300 lines)
- Automatic shell completion without `argcomplete`
- Type-safe arguments with IDE support
- Built-in testing utilities (`CliRunner`)
- Rich help output with formatting

**Risks:**
- Breaking change for all existing `argparse` Namespace consumers
- `typer` is a third-party dependency (not stdlib)
- Interactive REPL mode needs custom integration (typer doesn't have native REPL)
- Learning curve for contributors

**Mitigation:**
- Provide a `TyperArgs` compatibility layer bridging typer params to the existing `Namespace`-style
- Migrate incrementally: start with simple commands, keep argparse as fallback during transition
- Interactive mode can delegate to typer's Click-based invocation via `app(standalone_mode=False)`

#### 3.1.3 Migration Strategy

**Phase 1 (v2.0-alpha):** Scaffold + bridge layer
- Create `typer_poc/` with main app, command groups, and `TyperArgs` adapter
- Migrate 3–5 representative commands (ls, config get, config set, auth login, mkdir)
- Run both parsers in parallel; compare outputs

**Phase 2 (v2.0-beta):** Full migration
- Migrate all 61 commands to typer
- Remove argparse dependency
- Update interactive mode to work with typer

**Phase 3 (v2.0-rc):** Polish
- Finalize help text, examples, aliases
- Update documentation and shell completion scripts
- Performance testing and optimization

#### 3.1.4 Code Comparison

**Before (argparse) — `register_ls_parser`:**
```python
def register_ls_parser(subparsers):
    ls_parser = subparsers.add_parser("ls", aliases=["dir"], help="List items")
    ls_parser.add_argument("path", nargs="*", type=str, default=None, help="Directory path")
    ls_parser.add_argument("-l", "--long", action="store_true", help="Show detailed output")
    ls_parser.add_argument("-a", "--all", action="store_true", help="Show all")
    ls_parser.add_argument("-q", "--query", metavar="", help="JMESPath query")
    ls_parser.set_defaults(func=fs.ls_command)
```

**After (typer):**
```python
@fs_app.command("ls", help="List items in the current context or at a given path.")
def ls_command(
    path: Annotated[Optional[str], typer.Argument(help="Directory path")] = None,
    long: Annotated[bool, typer.Option("--long", "-l", help="Show detailed output")] = False,
    all: Annotated[bool, typer.Option("--all", "-a", help="Show all")] = False,
    query: Annotated[Optional[str], typer.Option("--query", "-q", help="JMESPath query")] = None,
):
    ...
```

### 3.2 Microsoft Fabric API SDK Integration

#### 3.2.1 SDK Evaluation

| Aspect               | Current (`requests`)                           | `microsoft-fabric-api` SDK                           |
|-----------------------|-----------------------------------------------|------------------------------------------------------|
| **Version**           | N/A (raw HTTP)                                | 0.1.0b6 (March 2026, preview)                       |
| **Auth**              | Custom MSAL token management                  | `azure-identity` credential objects                  |
| **Retry/Backoff**     | Custom `HTTPAdapter` + retry logic            | Built-in via `azure-core` pipeline                   |
| **Pagination**        | Manual continuation token handling            | Built-in iterator pattern                            |
| **Error handling**    | Manual HTTP status → exception mapping        | Typed exceptions from SDK                            |
| **Type safety**       | Dict-based responses                          | Typed response models with attributes                |
| **API coverage**      | Full (custom implementation)                  | Core APIs (workspaces, items); expanding             |
| **Maintenance**       | All on CLI team                               | Maintained by Microsoft SDK team                     |

#### 3.2.2 Impact Assessment

**Positive:**
- Eliminates ~2000 lines of custom API client code (17 files)
- Standardized authentication compatible with Azure ecosystem
- Built-in retry, throttling, and pagination
- Typed response objects improve IDE support
- Maintained by dedicated SDK team

**Risks:**
- SDK is in preview (0.1.0b6) — API surface may change
- Not all current CLI API calls may be covered by the SDK yet
- Different authentication flow from current MSAL-based approach
- OneLake/storage operations may not be in the Fabric SDK

**Recommendation:** **Adopt incrementally for covered APIs; keep fallback for uncovered ones.**

#### 3.2.3 Migration Strategy

Create an **adapter layer** (`sdk_adapter.py`) that:
1. Wraps the SDK's `FabricClient` with the CLI's authentication context
2. Provides the same function signatures as current `fab_api_*.py` modules
3. Falls back to raw HTTP for operations not yet covered by the SDK
4. Returns data in the format expected by the CLI's output layer

**Phase 1:** Migrate workspace and item CRUD operations
**Phase 2:** Migrate capacity, domain, connection, gateway operations
**Phase 3:** Evaluate OneLake/storage operations (may need separate SDK)

#### 3.2.4 Code Comparison

**Before (raw requests):**
```python
def list_workspaces(args):
    args.method = "get"
    args.uri = "workspaces"
    return do_request(args)
```

**After (SDK adapter):**
```python
def list_workspaces(credential):
    client = FabricClient(credential)
    return [ws for ws in client.core.workspaces.list_workspaces()]
```

### 3.3 Early Failure Detection

#### 3.3.1 Current Problem

The CLI's `command_support.yaml` defines which commands support which item types and elements, but this information is only used for documentation — not for runtime validation. Users currently see API errors (404, 400) when they attempt unsupported operations:

```
$ fab start ws1.Workspace/nb1.Notebook
[BadRequest] The operation 'start' is not supported for item type 'Notebook'
```

This error occurs **after** authentication and an API round-trip.

#### 3.3.2 Proposed Solution

Implement a **command validation layer** that checks `command_support.yaml` before executing any command handler:

```
User Input → Parse Args → Validate Support → Execute Command
                              ↓ (fails fast)
                         FabricCLIError with actionable message
```

**Validator Features:**
1. Load and cache `command_support.yaml` at startup
2. Before executing a command, check if the target element/item type is supported
3. Check for explicitly unsupported items and provide clear error messages
4. Provide suggestions for alternative commands when available

**Example improved error:**
```
$ fab start ws1.Workspace/nb1.Notebook
Error: The 'start' command does not support 'Notebook' items.
Supported item types for 'start': Capacity, MirroredDatabase
```

#### 3.3.3 Implementation

The validator will be a module `fab_command_validator.py` that:
- Loads `command_support.yaml` once and caches it
- Exposes `validate_command(command, subcommand, element_type, item_type)` → raises `FabricCLIError` or returns `True`
- Can be used as a decorator or called explicitly before API calls
- Integrates with both the current argparse flow and the future typer flow

---

## 4. Proof of Concept

This RFC includes working PoC implementations:

| Component                 | Location                                         | Description                                        |
|---------------------------|--------------------------------------------------|----------------------------------------------------|
| Typer PoC                 | `src/fabric_cli/typer_poc/main_app.py`          | Main app with command groups                       |
| TyperArgs bridge          | `src/fabric_cli/typer_poc/typer_args.py`        | Compatibility layer for existing handlers          |
| Config commands           | `src/fabric_cli/typer_poc/config_app.py`        | Config get/set/ls migrated to typer                |
| SDK Adapter               | `src/fabric_cli/typer_poc/sdk_adapter.py`       | Wrapper showing SDK integration pattern            |
| Command Validator         | `src/fabric_cli/core/fab_command_validator.py`  | Early failure detection using command_support.yaml |
| Validator Tests           | `tests/test_core/test_fab_command_validator.py` | Tests for the validation layer                     |

---

## 5. Value Assessment

### 5.1 Does the Migration Make Sense?

| Criterion                     | Score | Notes                                                        |
|-------------------------------|-------|--------------------------------------------------------------|
| Reduced boilerplate           | ✅ High | 50%+ reduction in parser code                               |
| Type safety                   | ✅ High | Type hints drive validation, IDE support, and documentation  |
| UX improvement                | ✅ High | Better help, completion, error messages                      |
| Maintenance reduction         | ✅ High | SDK handles auth/retry/pagination; typer handles parsing     |
| Risk                          | ⚠️ Medium | Major version bump; SDK in preview; typer is 3rd-party      |
| Migration effort              | ⚠️ Medium | 61 commands to migrate; test suite updates needed           |
| Backward compatibility        | ❌ Breaking | New major version; CLI surface may differ slightly         |

### 5.2 Recommendation

**Proceed with a phased approach:**

1. **Immediate (v1.x):** Implement the command validator — this is backward-compatible and provides immediate value
2. **v2.0-alpha:** Scaffold typer-based CLI alongside argparse; migrate representative commands
3. **v2.0-beta:** Complete typer migration; begin SDK integration for stable APIs
4. **v2.0-rc:** Full SDK integration; remove argparse; performance testing

---

## 6. Migration Risks & Mitigations

| Risk                                              | Impact | Mitigation                                                   |
|---------------------------------------------------|--------|--------------------------------------------------------------|
| Typer is a third-party dependency                 | Low    | Widely adopted (30k+ GitHub stars); built on Click           |
| SDK is in preview (breaking API changes)          | Medium | Adapter layer isolates CLI from SDK changes                  |
| Interactive REPL mode not native in typer          | Medium | Use Click's `invoke()` under the hood; keep custom REPL      |
| Contributors need to learn typer                   | Low    | Typer has excellent docs; simpler than argparse               |
| Not all Fabric APIs covered by SDK                | Medium | Fallback to raw HTTP for uncovered operations                |
| Test suite needs significant updates               | Medium | TyperArgs bridge minimizes handler changes; CliRunner simplifies tests |

---

## 7. Timeline Estimate

| Phase          | Duration  | Deliverables                                                      |
|----------------|-----------|-------------------------------------------------------------------|
| PoC & RFC      | 2 weeks   | This document, PoC code, stakeholder review                      |
| v1.x validator | 1 week    | Command validator integrated into current CLI                     |
| v2.0-alpha     | 4 weeks   | Typer scaffold, 15 commands migrated, SDK adapter for core APIs  |
| v2.0-beta      | 6 weeks   | All 61 commands migrated, SDK integration expanded                |
| v2.0-rc        | 3 weeks   | Testing, docs, performance tuning, shell completion scripts       |
| v2.0 GA        | 1 week    | Release, announcement, migration guide for users                  |

---

## 8. Open Questions

1. Should the interactive REPL mode be reimplemented with `prompt_toolkit` + typer, or kept as-is?
2. What is the timeline for `microsoft-fabric-api` reaching GA (1.0)?
3. Should the CLI support both `fab` (v2, typer) and `fab1` (v1, argparse) during transition?
4. How should custom shell completion (path completion for Fabric paths) be implemented in typer?

---

## 9. References

- [Typer Documentation](https://typer.tiangolo.com/)
- [microsoft-fabric-api on PyPI](https://pypi.org/project/microsoft-fabric-api/)
- [Fabric REST API Reference](https://learn.microsoft.com/en-us/rest/api/fabric/articles/)
- [Click Documentation](https://click.palletsprojects.com/)
- [Azure Identity for Python](https://learn.microsoft.com/en-us/python/api/overview/azure/identity-readme)
