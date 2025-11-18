# Interactive Mode (REPL) Experience - Design Specification

## Executive Summary

This document redesigns the Fabric CLI's interactive mode (REPL) to provide a simple, intuitive experience. The key insight: **REPL is a runtime state, not a persisted configuration**. Users enter REPL explicitly with a dedicated command, and authentication happens on-demand when needed for specific operations.

---

## Problem Statement

### Current Behavior & Issues

#### Issue 1: Mode as Persisted Config Creates Confusion
**Current Implementation:**
- `mode` is stored in `~/.config/fab/config.json`
- Setting `mode=interactive` requires logout and re-login
- Config persists between sessions but behavior doesn't match

**Problems:**
- **Broken promise**: "Mode is preserved between sessions" but reopening terminal lands in command-line shell
- **State mismatch**: Config says "interactive" but experience is "command_line"
- **Unnecessary persistence**: REPL is a session state, not a user preference to persist
- **Coupling issues**: Mode setting tied to authentication lifecycle

#### Issue 2: Authentication Prerequisite for REPL
**Current Flow:**
- REPL only launches after successful `fab auth login`
- Lines 237-252 in [`main.py`](src/fabric_cli/main.py:237-252) show REPL only accessible via auth success path

**Problems:**
- **Unnecessary barrier**: REPL itself doesn't require authentication
- **Commands like `config ls`, `auth status`, `help` work without auth**
- **Poor UX**: User wants to explore CLI but forced to authenticate first

#### Issue 3: No Clear REPL Entry Point
**Current Behavior:**
- User must: Set config → Logout → Login → REPL appears
- No direct "enter REPL" command
- Confusing sequence with hidden dependencies

**Problems:**
- **Discoverability**: Users don't know how to enter interactive mode
- **Complexity**: Multi-step process for simple task
- **Fragility**: If any step fails, user is stuck

---

## Root Cause Analysis

### Architectural Issues

1. **Wrong Abstraction**: Mode is treated as persistent user preference when it should be runtime session state
2. **Tight Coupling**: REPL launch coupled to authentication success
3. **Missing Command**: No `fab interactive` or `fab repl` command to enter REPL directly
4. **Config Misuse**: Config file used for session state instead of user preferences

### Current Code Flow

```
User types: fab config set mode interactive
  ↓
Config updated, cleanup context
  ↓
User types: fab auth login
  ↓
Auth succeeds
  ↓
Check: mode == interactive?
  ↓
Launch REPL (only path to REPL)
```

**Problems**: REPL launch hidden in auth flow, no direct access, mode persistence creates false expectations.

---

## Proposed Solution

### Design Philosophy

1. **REPL is a session state**: Not a persisted preference
2. **Explicit entry**: Dedicated command to enter REPL
3. **Auth on-demand**: Authenticate only when command requires it
4. **Stateless by default**: Each session starts fresh
5. **Simple mental model**: "I want REPL" → `fab repl` → Done

### Core Design Decisions

#### Decision 1: Remove Mode from Persistent Config

**Rationale:**
- REPL is a runtime state (like being in a subdirectory)
- Persisting it creates false expectations about session resume
- No user value in persisting REPL preference vs explicit entry

**Implementation:**
- Remove `FAB_MODE` from `FAB_CONFIG_KEYS_TO_VALID_VALUES`
- Remove `mode` from `CONFIG_DEFAULT_VALUES`
- Keep mode as runtime variable in parser/session only
- Clean up existing mode config on first run (migration)

#### Decision 2: Add Dedicated REPL Entry Command

**Options Considered:**

| Command | Pros | Cons |
|---------|------|------|
| `fab interactive` | Descriptive, matches current terminology | Longer to type |
| `fab repl` | Short, industry standard (Python, Node, etc.) | Less descriptive |
| `fab shell` | Familiar to shell users | Conflicts with OS shell concept |
| `fab -i` | Very short | Flag vs command inconsistency |

**Decision**: Implement **`fab repl`** as primary + **`fab interactive`** as alias

**Rationale:**
- `repl` is industry standard (Python, Node, Ruby, etc.)
- Short and memorable
- Clear intent: "I want the REPL"
- `interactive` as alias provides discoverability

#### Decision 3: Authentication on Demand

**Principle**: REPL launches immediately, no auth check upfront.

**Flow:**
```
User types: fab repl
  ↓
Launch REPL immediately (no auth check)
  ↓
Welcome to Fabric CLI REPL
fab:/$ help           # Works - no auth needed
fab:/$ config ls      # Works - no auth needed
fab:/$ auth status    # Shows not authenticated
fab:/$ ls             # Fails - prompts for auth
  ↓
User authenticates
  ↓
fab:/$ ls             # Now works
```

**Benefits:**
- Instant access to REPL
- Explore CLI without auth barrier
- Auth only when actually needed
- Natural, intuitive flow

---

## Solution Architecture

### Component 1: Remove Mode from Persistent Config

**File**: [`src/fabric_cli/core/fab_constant.py`](src/fabric_cli/core/fab_constant.py)

**Current Code** (lines 76, 102, 118):
```python
FAB_MODE = "mode"

FAB_CONFIG_KEYS_TO_VALID_VALUES = {
    # ... other keys ...
    FAB_MODE: [FAB_MODE_INTERACTIVE, FAB_MODE_COMMANDLINE],
    # ... other keys ...
}

CONFIG_DEFAULT_VALUES = {
    FAB_MODE: FAB_MODE_COMMANDLINE,
    # ... other values ...
}
```

**Updated Code**:
```python
# FAB_MODE removed from config - now runtime only
FAB_MODE_INTERACTIVE = "interactive"  # Keep constants for runtime use
FAB_MODE_COMMANDLINE = "command_line"

FAB_CONFIG_KEYS_TO_VALID_VALUES = {
    # FAB_MODE removed - not a persisted config anymore
    FAB_CACHE_ENABLED: ["true", "false"],
    FAB_CONTEXT_PERSISTENCE: ["true", "false"],
    # ... other keys ...
}

CONFIG_DEFAULT_VALUES = {
    # FAB_MODE removed - not a persisted config
    FAB_CACHE_ENABLED: "true",
    # ... other values ...
}
```

**Migration**: Add cleanup logic in [`fab_state_config.py:init_defaults()`](src/fabric_cli/core/fab_state_config.py:52):
```python
def init_defaults():
    """
    Ensures that all known config keys have default values if they are not already set.
    Also handles migration from old config structure.
    """
    current_config = read_config(config_file)
    
    # MIGRATION: Remove deprecated 'mode' config
    if "mode" in current_config:
        del current_config["mode"]
    if "fab_mode" in current_config:
        del current_config["fab_mode"]

    # ... rest of existing logic ...
```

### Component 2: Add REPL Entry Command

**File**: [`src/fabric_cli/parsers/fab_repl_parser.py`](src/fabric_cli/parsers/fab_repl_parser.py) (NEW)

```python
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

from fabric_cli.core import fab_constant


def register_parser(subparsers):
    """Register the REPL command parser."""
    
    repl_parser = subparsers.add_parser(
        "repl",
        help="Enter interactive REPL mode",
        description="Launch the Fabric CLI interactive REPL (Read-Eval-Print Loop).",
        fab_examples=[
            "# Enter interactive mode",
            "fab repl",
            "",
            "# Once in REPL, commands run without 'fab' prefix:",
            "fab:/$ ls",
            "fab:/$ cd MyWorkspace.Workspace", 
            "fab:/$ pwd",
        ],
        fab_aliases=["fab interactive"],
        fab_learnmore=["See docs/essentials/modes.md for more about interactive mode"],
    )
    
    repl_parser.set_defaults(func=_launch_repl)
    
    # Also register 'interactive' as an alias
    interactive_parser = subparsers.add_parser(
        "interactive",
        help="Alias for 'repl' - enter interactive mode",
        description="Launch the Fabric CLI interactive REPL. This is an alias for 'fab repl'.",
    )
    interactive_parser.set_defaults(func=_launch_repl)


def _launch_repl(args):
    """Launch the interactive REPL."""
    from fabric_cli.core.fab_interactive import InteractiveCLI
    from fabric_cli.main import parser, subparsers
    from fabric_cli.utils import fab_ui
    
    # Set runtime mode to interactive
    parser.set_mode(fab_constant.FAB_MODE_INTERACTIVE)
    
    try:
        interactive_cli = InteractiveCLI(parser, subparsers)
        interactive_cli.start_interactive()
    except (KeyboardInterrupt, EOFError):
        fab_ui.print(f"\n{fab_constant.INTERACTIVE_EXIT_MESSAGE}")
```

**File**: [`src/fabric_cli/main.py`](src/fabric_cli/main.py)

**Add import** (after line 23):
```python
from fabric_cli.parsers import fab_repl_parser as repl_parser
```

**Register parser** (after line 218):
```python
repl_parser.register_parser(subparsers)  # repl
```

### Component 3: Remove REPL Launch from Auth Flow

**File**: [`src/fabric_cli/main.py`](src/fabric_cli/main.py)

**Current Code** (lines 237-252):
```python
if args.command == "auth" and args.auth_command == "login":
    if login.init(args):
        if (
            fab_state_config.get_config(fab_constant.FAB_MODE)
            == fab_constant.FAB_MODE_INTERACTIVE
        ):
            # Initialize InteractiveCLI
            from fabric_cli.core.fab_interactive import InteractiveCLI

            try:
                interactive_cli = InteractiveCLI(parser, subparsers)
                interactive_cli.start_interactive()
            except (KeyboardInterrupt, EOFError):
                fab_ui.print(
                    "\nInteractive mode cancelled. Returning to previous menu."
                )
```

**Updated Code**:
```python
if args.command == "auth" and args.auth_command == "login":
    login.init(args)
    # REMOVED: No longer auto-launch REPL after login
    # Users enter REPL explicitly with 'fab repl'
```

### Component 4: Clean Up Config Set Mode Logic

**File**: [`src/fabric_cli/commands/config/fab_config_set.py`](src/fabric_cli/commands/config/fab_config_set.py)

**Current Code** (lines 65-85):
```python
previous_mode = fab_state_config.get_config(key)
fab_state_config.set_config(key, value)
if verbose:
    utils_ui.print_output_format(
        args, message=f"Configuration '{key}' set to '{value}'"
    )
current_mode = fab_state_config.get_config(fab_constant.FAB_MODE)

# Clean up context files when changing mode
if key == fab_constant.FAB_MODE:
    from fabric_cli.core.fab_context import Context

    Context().cleanup_context_files(cleanup_all_stale=True, cleanup_current=True)

if (
    key == fab_constant.FAB_MODE
    and current_mode == fab_constant.FAB_MODE_COMMANDLINE
    and previous_mode == fab_constant.FAB_MODE_INTERACTIVE
):
    utils_ui.print("Exiting interactive mode. Goodbye!")
    os._exit(0)
```

**Updated Code**:
```python
fab_state_config.set_config(key, value)
if verbose:
    utils_ui.print_output_format(
        args, message=f"Configuration '{key}' set to '{value}'"
    )

# REMOVED: All mode-specific logic
# Mode is no longer a persisted config, so no special handling needed
```

### Component 5: Update Interactive CLI to Handle Unauthenticated State

**File**: [`src/fabric_cli/core/fab_interactive.py`](src/fabric_cli/core/fab_interactive.py)

**Enhancement**: Modify [`handle_command()`](src/fabric_cli/core/fab_interactive.py:37) to catch auth errors gracefully:

```python
def handle_command(self, command):
    """Process the user command."""
    fab_logger.print_log_file_path()

    command_parts = command.strip().split()

    # Handle special commands first
    if command in fab_constant.INTERACTIVE_QUIT_COMMANDS:
        utils_ui.print(fab_constant.INTERACTIVE_EXIT_MESSAGE)
        return True  # Exit
    elif command in fab_constant.INTERACTIVE_HELP_COMMANDS:
        utils_ui.display_help(
            fab_commands.COMMANDS, "Usage: <command> <subcommand> [flags]"
        )
        return False
    elif command in fab_constant.INTERACTIVE_VERSION_COMMANDS:
        utils_ui.print_version()
        return False

    # Interactive mode
    self.parser.set_mode(fab_constant.FAB_MODE_INTERACTIVE)

    if command_parts:
        subcommand_name = command_parts[0]
        if subcommand_name in self.subparsers.choices:
            subparser = self.subparsers.choices[subcommand_name]

            try:
                subparser_args = subparser.parse_args(command_parts[1:])
                subparser_args.command = subcommand_name
                subparser_args.fab_mode = fab_constant.FAB_MODE_INTERACTIVE
                subparser_args.command_path = Command.get_command_path(
                    subparser_args
                )

                if not command_parts[1:]:
                    subparser_args.func(subparser_args)
                elif hasattr(subparser_args, "func"):
                    subparser_args.func(subparser_args)
                else:
                    utils_ui.print(
                        f"No function associated with the command: {command.strip()}"
                    )
            except FabricCLIError as e:
                # NEW: Catch auth errors and provide helpful message
                if e.status_code in [
                    fab_constant.ERROR_UNAUTHORIZED,
                    fab_constant.ERROR_AUTHENTICATION_FAILED,
                ]:
                    utils_ui.print_output_error(e, output_format_type="text")
                    utils_ui.print("\nTo authenticate, run: auth login")
                else:
                    utils_ui.print_output_error(e, output_format_type="text")
            except SystemExit:
                # Catch SystemExit raised by ArgumentParser and prevent exiting
                return
        else:
            self.parser.error(f"invalid choice: '{command.strip()}'")

    return False
```

### Component 6: Update Context Persistence Logic

**File**: [`src/fabric_cli/core/fab_context.py`](src/fabric_cli/core/fab_context.py)

**Current Code** (lines 138-145):
```python
def _should_use_context_file(self) -> bool:
    """Determine if the context file should be used based on the current mode and persistence settings."""
    mode = fab_state_config.get_config(fab_constant.FAB_MODE)
    persistence_enabled = fab_state_config.get_config(
        fab_constant.FAB_CONTEXT_PERSISTENCE
    )
    return (
        mode == fab_constant.FAB_MODE_COMMANDLINE
        and persistence_enabled == "true"
    )
```

**Updated Code**:
```python
def _should_use_context_file(self) -> bool:
    """
    Determine if the context file should be used based on persistence settings.
    
    Note: Mode is no longer a persisted config. Context persistence now only
    depends on the FAB_CONTEXT_PERSISTENCE setting, which defaults to 'true'
    for command-line usage.
    """
    persistence_enabled = fab_state_config.get_config(
        fab_constant.FAB_CONTEXT_PERSISTENCE
    )
    return persistence_enabled == "true"
```

---

## User Experience Flows

### Flow 1: Entering REPL (First Time)

```bash
# User wants to try interactive mode
$ fab repl

Welcome to the Fabric CLI ⚡
Type 'help' for help.

fab:/$ help
Available commands:
  ls, cd, mkdir, rm, ...
  auth, config, ...
  Type 'help <command>' for more info

fab:/$ auth status
✗ Not logged in to app.fabric.microsoft.com

fab:/$ config ls
cache_enabled: true
context_persistence: true
...

fab:/$ ls
Error: Authentication required
To authenticate, run: auth login

fab:/$ auth login
How would you like to authenticate Fabric CLI?
> Interactive with a web browser

[Browser opens, user authenticates]

✓ Logged in to app.fabric.microsoft.com

fab:/$ ls
Workspace1.Workspace
Workspace2.Workspace

fab:/$ exit
$
```

**Result**: Seamless exploration, auth only when needed.

### Flow 2: Reopening Terminal

```bash
# User opens new terminal, wants REPL again
$ fab repl

Welcome to the Fabric CLI ⚡
Type 'help' for help.

fab:/$ ls
[Works if tokens still valid, or prompts for re-auth]
```

**Result**: Simple, predictable. Always `fab repl` to enter.

### Flow 3: Using Alias

```bash
$ fab interactive

Welcome to the Fabric CLI ⚡
Type 'help' for help.

fab:/$
```

**Result**: Alias provides discoverability.

### Flow 4: Quick Command (No REPL)

```bash
$ fab ls
[Runs in command-line mode, no REPL]

$ fab auth status
[Runs in command-line mode, no REPL]
```

**Result**: Command-line mode still works as before.

### Flow 5: REPL from Non-Auth Commands

```bash
$ fab repl

Welcome to the Fabric CLI ⚡

fab:/$ config get cache_enabled
true

fab:/$ auth status
✗ Not logged in

fab:/$ version
Fabric CLI 1.x.x

fab:/$ help ls
Usage: ls [path] [flags]
...
```

**Result**: Full CLI exploration without auth barrier.

---

## Implementation Details

### File Changes Summary

| File | Change Type | Description |
|------|-------------|-------------|
| `src/fabric_cli/core/fab_constant.py` | **Modify** | Remove `FAB_MODE` from config keys |
| `src/fabric_cli/core/fab_state_config.py` | **Modify** | Add migration to remove old mode config |
| `src/fabric_cli/parsers/fab_repl_parser.py` | **New** | Add REPL command parser |
| `src/fabric_cli/main.py` | **Modify** | Register REPL parser, remove auth-triggered REPL launch |
| `src/fabric_cli/commands/config/fab_config_set.py` | **Modify** | Remove mode-specific logic |
| `src/fabric_cli/core/fab_interactive.py` | **Modify** | Better auth error handling in REPL |
| `src/fabric_cli/core/fab_context.py` | **Modify** | Update persistence logic (remove mode dependency) |
| `docs/essentials/modes.md` | **Rewrite** | Document new REPL command approach |

### Migration Strategy

**Phase 1: Add new command alongside old behavior**
- Implement `fab repl` command
- Keep existing `mode` config working (deprecated)
- Add deprecation warning when using `config set mode`

**Phase 2: Remove old behavior**
- Remove `mode` from config
- Clean up mode-setting logic
- Update documentation

**Deprecation Message** (Phase 1):
```python
if key == "mode":
    utils_ui.print_warning(
        "The 'mode' config is deprecated. Use 'fab repl' to enter interactive mode."
    )
```

### Backwards Compatibility

**Breaking Changes:**
- `fab config set mode interactive` will no longer work (after Phase 2)
- `fab config get mode` will return nothing (after Phase 2)

**Migration Path for Users:**
- Old: `fab config set mode interactive` + `fab auth login`
- New: `fab repl` (that's it!)

**Communication:**
- Deprecation warning in Phase 1
- Clear migration guide in release notes
- Updated documentation

---

## Design Rationale

### Why Remove Mode from Config?

| Aspect | As Persisted Config | As Runtime State |
|--------|---------------------|------------------|
| **Mental Model** | "REPL is a preference" ❌ | "REPL is a session" ✅ |
| **Session Resume** | Broken (config says yes, behavior says no) | Not applicable (explicit entry) |
| **User Intent** | Unclear (set once, forget?) | Crystal clear (`fab repl` = "I want REPL now") |
| **Coupling** | Tied to auth lifecycle | Independent |
| **Simplicity** | Multi-step setup | Single command |

### Why Dedicated Command?

| Approach | User Action | Pros | Cons |
|----------|-------------|------|------|
| **Config-based** | `fab config set mode interactive` + auth | Persistent preference | Broken session resume, complex |
| **Flag-based** | `fab -i` | Short | Inconsistent with command structure |
| **Auto-detect** | Just `fab` → REPL if mode set | Automatic | Unpredictable, requires config |
| **Dedicated Command** ✅ | `fab repl` | Clear intent, simple, standard | None significant |

### Why Auth on Demand?

**Principle**: Don't ask permission until you need it.

**Benefits:**
1. **Lower barrier**: New users can explore without auth
2. **Natural discovery**: Learn commands before committing
3. **Respect user time**: Auth only for operations that need it
4. **Better UX**: Immediate feedback vs upfront blocker

**Commands that work without auth:**
- `help`, `version`
- `config ls`, `config get`, `config set`
- `auth status`
- `exit`, `quit`

**Commands that need auth:**
- `ls`, `cd`, `mkdir`, etc. (Fabric API calls)
- Any workspace/item operations

---

## Testing Strategy

### Unit Tests

1. **REPL Command Registration**
   ```python
   def test_repl_command_registered():
       assert "repl" in subparsers.choices
       assert "interactive" in subparsers.choices  # Alias
   ```

2. **Mode Not in Config**
   ```python
   def test_mode_not_persisted():
       config = fab_state_config.list_configs()
       assert "mode" not in config
   ```

3. **Migration Removes Old Mode**
   ```python
   def test_migration_removes_mode():
       # Setup: Create config with old 'mode' key
       fab_state_config.set_config("mode", "interactive")
       
       # Execute: Run migration
       fab_state_config.init_defaults()
       
       # Verify: 'mode' removed
       config = fab_state_config.list_configs()
       assert "mode" not in config
   ```

### Integration Tests

1. **Enter REPL via Command**
   ```bash
   $ fab repl
   # Verify: REPL prompt appears
   # Verify: Can run commands
   # Verify: Exit works
   ```

2. **Auth on Demand**
   ```bash
   $ fab repl
   fab:/$ config ls  # Should work
   fab:/$ ls         # Should prompt for auth
   ```

3. **Alias Works**
   ```bash
   $ fab interactive
   # Verify: Same as 'fab repl'
   ```

### Manual Testing Checklist

- [ ] `fab repl` launches REPL immediately
- [ ] REPL works without authentication for safe commands
- [ ] REPL prompts for auth when needed
- [ ] `fab interactive` works as alias
- [ ] `exit`/`quit`/Ctrl+D/Ctrl+C exit REPL cleanly
- [ ] Reopening terminal, `fab repl` works again
- [ ] `fab config get mode` returns nothing (after migration)
- [ ] Old config with `mode` gets cleaned up on first run

---

## Documentation Updates

### 1. [`docs/essentials/modes.md`](docs/essentials/modes.md) - Complete Rewrite

```markdown
# Interactive Mode (REPL)

The Fabric CLI supports two ways of working:

1. **Command-line mode** (default): Run individual commands
2. **Interactive mode (REPL)**: Enter a shell-like environment

## Command-Line Mode

The default mode. You run commands by typing `fab` followed by the command:

```bash
$ fab ls
$ fab cd MyWorkspace.Workspace
$ fab pwd
```

Each command is independent. This mode is ideal for:
- Scripting and automation
- CI/CD pipelines
- One-off commands

## Interactive Mode (REPL)

Interactive mode provides a shell-like environment where you run commands without typing `fab` each time.

### Entering Interactive Mode

```bash
$ fab repl
```

Or use the longer alias:

```bash
$ fab interactive
```

You'll see a prompt:

```
Welcome to the Fabric CLI ⚡
Type 'help' for help.

fab:/$
```

Now you can run commands directly:

```
fab:/$ ls
fab:/$ cd MyWorkspace.Workspace
fab:/MyWorkspace.Workspace$ pwd
fab:/MyWorkspace.Workspace$ help
```

### Authentication in REPL

The REPL launches immediately without requiring authentication. Commands that don't need authentication work right away:

```
fab:/$ help
fab:/$ config ls
fab:/$ auth status
```

When you run a command that needs authentication, you'll be prompted:

```
fab:/$ ls
Error: Authentication required
To authenticate, run: auth login

fab:/$ auth login
[Authentication flow...]

fab:/$ ls
[Now works]
```

### Exiting Interactive Mode

To exit the REPL:
- Type `exit` or `quit`
- Press `Ctrl+D`
- Press `Ctrl+C`

```
fab:/$ exit
$
```

## Comparison

| Aspect | Command-Line Mode | Interactive Mode |
|--------|-------------------|------------------|
| **Entry** | Default, just run `fab <command>` | Run `fab repl` |
| **Commands** | `fab ls`, `fab cd`, etc. | `ls`, `cd`, etc. (no `fab` prefix) |
| **Best for** | Scripts, automation, one-off commands | Exploration, learning, multi-step workflows |
| **Persistence** | None needed | None (exit with `exit` or Ctrl+D) |
| **Authentication** | Per-command (if needed) | On-demand (when command needs it) |

## Tips

- Use interactive mode when learning the CLI or doing exploratory work
- Use command-line mode for scripts and automation
- You can freely switch between modes - they're just different ways to interact with the same CLI
- Tab completion works in both modes
```

### 2. Update Command Help

**`fab repl --help`**:
```
Usage: fab repl

Launch the Fabric CLI interactive REPL (Read-Eval-Print Loop).

In interactive mode, you can run commands without typing 'fab' each time.
Authentication is requested on-demand when commands need it.

Examples:
  # Enter interactive mode
  fab repl
  
  # Once in REPL, commands run without 'fab' prefix:
  fab:/$ ls
  fab:/$ cd MyWorkspace.Workspace
  fab:/$ pwd

Aliases:
  fab interactive

Learn more:
  See docs/essentials/modes.md for more about interactive mode
  For more usage examples, see https://aka.ms/fabric-cli
```

### 3. Update Troubleshooting

**Add to** [`docs/troubleshooting.md`](docs/troubleshooting.md):

```markdown
## Interactive Mode (REPL)

### How do I enter interactive mode?

Run:
```bash
fab repl
```

Or the longer alias:
```bash
fab interactive
```

### Do I need to authenticate before entering REPL?

No! The REPL launches immediately. You'll be prompted to authenticate only when you run a command that needs it.

### What commands work without authentication?

- `help`, `version`
- `config` commands (`config ls`, `config get`, etc.)
- `auth status`
- `exit`, `quit`

### I get "mode is deprecated" warning

If you see this warning when using `fab config set mode`, it means you're using the old way of entering interactive mode.

**Old way** (deprecated):
```bash
fab config set mode interactive
fab auth login
```

**New way**:
```bash
fab repl
```

### Can I still use 'fab config set mode'?

In newer versions, `mode` is no longer a configuration setting. Use `fab repl` to enter interactive mode instead.
```

---

## Security & Privacy Considerations

### No Security Changes
- **Auth flow**: Unchanged, same as command-line mode
- **Token storage**: Unchanged
- **Permissions**: Unchanged

### Privacy Enhancement
- **Less auth prompting**: Users can explore CLI without logging in
- **Transparent behavior**: Clear when auth is needed vs not needed

### Attack Surface
- **No new attack vectors**: REPL uses same command execution as command-line mode
- **Same security model**: Auth required for sensitive operations

---

## Performance Considerations

### REPL Launch Time
- **Target**: <200ms from `fab repl` to prompt
- **No upfront auth check**: Instant launch
- **Lazy loading**: Load modules as needed

### Memory Footprint
- **REPL session**: ~50MB (same as before)
- **Command history**: In-memory only (cleared on exit)

### Startup Optimization
- No mode config read on startup (removed overhead)
- No auth status check (removed overhead)
- Direct REPL launch (single code path)

---

## Migration Plan

### Phase 1: Soft Launch (v1.x)
- ✅ Add `fab repl` command
- ✅ Keep `mode` config working
- ✅ Add deprecation warning for `config set mode`
- ✅ Update docs to recommend `fab repl`

### Phase 2: Deprecation (v1.x+1)
- ⚠️ `config set mode` shows error with migration instructions
- ⚠️ `config get mode` returns deprecation message
- ✅ Migration script removes old `mode` config

### Phase 3: Removal (v2.0)
- ❌ Remove `FAB_MODE` from config entirely
- ❌ Remove mode-related code from `fab_config_set.py`
- ✅ Clean architecture, single REPL entry point

### User Communication

**Release Notes v1.x**:
```markdown
## New: Simplified Interactive Mode

We've made entering interactive mode much simpler!

**New way** (recommended):
```bash
fab repl
```

**Old way** (still works, but deprecated):
```bash
fab config set mode interactive
fab auth login
```

The old approach will be removed in v2.0. Please update your workflows to use `fab repl`.
```

**Release Notes v2.0**:
```markdown
## Breaking Change: Mode Config Removed

The `mode` configuration setting has been removed. Interactive mode is now a runtime session state.

**Migration**:
- Old: `fab config set mode interactive` + `fab auth login`
- New: `fab repl`

If you have `mode` in your config file, it will be automatically removed on first run.
```

---

## Success Metrics

### User Experience Metrics
1. **Reduced complexity**: One command vs multi-step flow
2. **Faster time to REPL**: <5 seconds from `fab repl` to first command
3. **Lower auth barrier**: Users can explore before committing to auth

### Technical Metrics
1. **Code complexity**: Remove ~50 lines of mode-handling code
2. **Config simplicity**: One less config key to manage
3. **Support burden**: Fewer issues about "mode not working"

### Adoption Metrics
- Track `fab repl` usage vs old `config set mode` approach
- Monitor time from first CLI use to REPL entry
- Measure drop-off rate at auth prompts

---

## Future Enhancements

### Phase 2 (Optional)
1. **REPL history persistence**: Save command history across sessions
2. **REPL customization**: Colors, prompt format, etc.
3. **Workspace-specific REPL**: Launch REPL in specific workspace context

### Phase 3 (Optional)
1. **REPL plugins**: Allow extensions to add custom REPL commands
2. **Multi-line editing**: Better support for complex commands
3. **REPL scripting**: Run script files from within REPL

---

## Conclusion

This redesign solves the core issues with interactive mode:

1. ✅ **Clear entry point**: `fab repl` - simple, memorable, standard
2. ✅ **No session persistence confusion**: REPL is a session state, not a persisted preference
3. ✅ **Auth on demand**: Explore CLI freely, authenticate when needed
4. ✅ **Simplified architecture**: Remove mode config complexity
5. ✅ **Better UX**: One command to REPL vs multi-step process

The solution follows industry standards (REPL commands in Python, Node, Ruby), removes architectural complexity, and provides a superior user experience.

---

## Appendix: Alternative Approaches Considered

### Alternative 1: Keep Mode Config, Fix Session Resume

**Approach**: Add logic to auto-launch REPL on `fab` when `mode=interactive`

**Why Rejected**:
- Adds complexity (startup checks, auth validation)
- Persisting session state is architecturally wrong
- Users might type `fab` expecting help, get REPL instead
- Doesn't solve the multi-step setup problem

### Alternative 2: Make `fab` with No Args Enter REPL

**Approach**: `fab` → REPL, `fab <command>` → run command

**Why Rejected**:
- Breaking change (currently shows help)
- Unpredictable (sometimes help, sometimes REPL based on config)
- Conflicts with standard CLI patterns

### Alternative 3: Environment Variable for Mode

**Approach**: `export FAB_MODE=interactive`

**Why Rejected**:
- Still requires persistence management
- Less discoverable than explicit command
- Conflicts with per-terminal customization

### Selected Approach: Dedicated Command ✅

**Why This Wins**:
- Industry standard (Python, Node, Ruby all use dedicated REPL commands)
- Clear, explicit intent
- Simple mental model
- No persistence issues
- Easy to discover and use