# POSIX Compliance Design Architecture

## Executive Summary

This document provides a comprehensive design architecture for POSIX compliance in the Microsoft Fabric CLI. It identifies gaps, proposes solutions, and documents the implementation of POSIX standards across the command-line interface.

---

## Table of Contents

1. [Introduction](#introduction)
2. [POSIX Standards Overview](#posix-standards-overview)
3. [Gap Analysis](#gap-analysis)
4. [Design Decisions](#design-decisions)
5. [Implementation Details](#implementation-details)
6. [Testing Strategy](#testing-strategy)
7. [Migration Guide](#migration-guide)
8. [Future Considerations](#future-considerations)

---

## 1. Introduction

### Objective

Make the Fabric CLI fully compliant with POSIX (Portable Operating System Interface) standards to ensure:
- **Portability**: Consistent behavior across Unix-like systems
- **Interoperability**: Better integration with shell scripts and automation
- **Standards Compliance**: Alignment with industry best practices
- **Predictability**: Expected behavior for command-line users

### Scope

This design covers the following POSIX compliance areas:
1. Exit codes
2. Command-line option syntax
3. Signal handling
4. Environment variable naming
5. Standard stream usage (stdout/stderr)

---

## 2. POSIX Standards Overview

### 2.1 Exit Codes (POSIX.1-2017, Section 2.8.2)

| Code | Meaning | Standard |
|------|---------|----------|
| 0 | Successful completion | Required |
| 1-125 | Errors (general) | Standard practice |
| 1 | General error | Common convention |
| 2 | Misuse of shell builtins | Bash convention |
| 126 | Command cannot execute | Shell standard |
| 127 | Command not found | Shell standard |
| 128+n | Fatal signal "n" | Shell standard |

### 2.2 Option Syntax (POSIX.1-2017, Section 12.2)

**Guidelines:**
- Single-character options preceded by single hyphen: `-h`, `-v`, `-a`
- Multi-character options preceded by double hyphen: `--help`, `--version`
- Options can be combined: `-abc` equivalent to `-a -b -c`
- Arguments can follow options: `-f file` or `-ffile`
- `--` terminates option processing

### 2.3 Signal Handling

**Common Signals:**
- `SIGINT` (2): Keyboard interrupt (Ctrl+C)
- `SIGTERM` (15): Termination request
- `SIGHUP` (1): Terminal hangup
- `SIGQUIT` (3): Quit with core dump (Ctrl+\)

**Expected Behavior:**
- Graceful shutdown on SIGTERM
- Cleanup resources on exit
- Exit with 128 + signal number

### 2.4 Environment Variables

**Naming Convention:**
- UPPERCASE letters only
- Underscores for word separation
- No leading digits

**Examples:**
- ✅ `PATH`, `HOME`, `USER`
- ✅ `FAB_TOKEN`, `FAB_TENANT_ID`
- ❌ `fab_token`, `Fab_Token`

### 2.5 Standard Streams

- **stdin** (fd 0): Standard input
- **stdout** (fd 1): Standard output (data/results)
- **stderr** (fd 2): Standard error (diagnostics/errors)

---

## 3. Gap Analysis

### 3.1 Exit Codes

| Component | Before | After | Compliance | Priority |
|-----------|--------|-------|------------|----------|
| Success | `0` | `0` | ✅ Compliant | N/A |
| General error | `1` | `1` | ✅ Compliant | N/A |
| Misuse | `2` | `2` | ✅ Compliant | N/A |
| Authorization | **`4`** ❌ | **`126`** ✅ | Fixed | **HIGH** |
| Command not found | Missing | `127` | Added | **MEDIUM** |
| Signal exits | Incomplete | `128+n` | Enhanced | **HIGH** |

**Gap:** Non-standard exit code 4 for authorization errors  
**Solution:** Use exit code 126 (command cannot execute) per POSIX shell standards  
**Impact:** 🔴 **Breaking change** for scripts checking exit code 4

### 3.2 Command-Line Options

| Component | Before | After | Compliance | Priority |
|-----------|--------|-------|------------|----------|
| Help flag | **`-help`** ❌ | **`-h, --help`** ✅ | Fixed | **HIGH** |
| Version flag | `-v` | `-v, -V, --version` | Enhanced | **LOW** |
| Output format | `--output_format` | `--output_format` | ✅ Compliant | N/A |
| Command flag | `-c` | `-c, --command` | ✅ Compliant | N/A |

**Gap:** Single-dash long option `-help` violates POSIX  
**Solution:** Use argparse default `-h` (short) and `--help` (long)  
**Impact:** 🟢 **Non-breaking** (argparse provides both by default)

### 3.3 Signal Handling

| Signal | Before | After | Compliance | Priority |
|--------|--------|-------|------------|----------|
| SIGINT | ✅ Handled | ✅ Handled | Enhanced | **HIGH** |
| SIGTERM | ❌ Not handled | ✅ Handled | **Fixed** | **HIGH** |
| SIGHUP | ❌ Not handled | ✅ Handled | **Fixed** | **MEDIUM** |
| SIGQUIT | ❌ Not handled | ✅ Handled | **Fixed** | **MEDIUM** |

**Gap:** Only SIGINT (KeyboardInterrupt) was handled  
**Solution:** Add handlers for SIGTERM, SIGHUP, SIGQUIT with exit code 128+n  
**Impact:** 🟢 **Non-breaking** enhancement

### 3.4 Environment Variables

| Variable | Before | After | Compliance | Priority |
|----------|--------|-------|------------|----------|
| FAB_TOKEN | **`"fab_token"`** ❌ | **`"FAB_TOKEN"`** ✅ | Fixed | **HIGH** |
| FAB_TENANT_ID | **`"fab_tenant_id"`** ❌ | **`"FAB_TENANT_ID"`** ✅ | Fixed | **HIGH** |
| FAB_SPN_CLIENT_ID | **`"fab_spn_client_id"`** ❌ | **`"FAB_SPN_CLIENT_ID"`** ✅ | Fixed | **HIGH** |
| (All others) | lowercase | UPPERCASE | Fixed | **HIGH** |

**Gap:** Environment variable names used lowercase strings  
**Solution:** Change all env var constant strings to uppercase  
**Impact:** 🔴 **Breaking change** - users must update env var exports

### 3.5 Standard Streams

| Component | Before | After | Compliance | Priority |
|-----------|--------|-------|------------|----------|
| Data output | stdout | stdout | ✅ Compliant | N/A |
| Error messages | stderr | stderr | ✅ Compliant | N/A |
| Warnings | stderr | stderr | ✅ Compliant | N/A |
| Diagnostics | stderr | stderr | ✅ Compliant | N/A |

**Gap:** None - already compliant  
**Solution:** No changes needed  
**Impact:** 🟢 **None**

---

## 4. Design Decisions

### 4.1 Exit Code Strategy

**Decision:** Replace exit code 4 with 126 for authorization errors

**Rationale:**
- POSIX shells use 126 for "command cannot execute" (e.g., permission denied)
- Exit code 4 has no standard meaning
- Aligns with shell behavior when commands lack execute permission

**Alternatives Considered:**
1. Keep exit code 4 (rejected - not POSIX compliant)
2. Use exit code 1 (rejected - too generic)
3. Use exit code 126 ✅ (selected - POSIX standard for permission errors)

**Trade-offs:**
- ➕ Standards compliant
- ➕ Clear semantic meaning
- ➖ Breaking change for existing scripts

### 4.2 Help Flag Strategy

**Decision:** Rely on argparse default `-h` and `--help`

**Rationale:**
- argparse provides POSIX-compliant help flags by default
- `-h` is short form (single dash, single character)
- `--help` is long form (double dash, multi-character)
- Removing custom `-help` simplifies code

**Alternatives Considered:**
1. Keep `-help` (rejected - violates POSIX)
2. Add `-h` alongside `-help` (rejected - redundant)
3. Use argparse default ✅ (selected - standard and simple)

**Trade-offs:**
- ➕ POSIX compliant
- ➕ Simpler code
- ➕ Consistent with other tools
- ➖ None (argparse handles this automatically)

### 4.3 Signal Handling Strategy

**Decision:** Add handlers for all common POSIX signals

**Rationale:**
- Docker containers send SIGTERM for graceful shutdown
- SSH disconnections send SIGHUP
- Users expect Ctrl+\ (SIGQUIT) to work
- Exit codes 128+n are universally recognized

**Alternatives Considered:**
1. Handle only SIGINT (rejected - incomplete)
2. Handle SIGINT and SIGTERM only (rejected - missing SIGHUP)
3. Handle all common signals ✅ (selected - comprehensive)

**Trade-offs:**
- ➕ Better container support
- ➕ Graceful shutdown in all scenarios
- ➕ Clear exit codes
- ➖ Slightly more complex signal handling code

### 4.4 Environment Variable Strategy

**Decision:** Change all env var constant strings to UPPERCASE

**Rationale:**
- POSIX convention for environment variables
- Distinguishes env vars from regular variables
- Standard across all Unix-like systems

**Alternatives Considered:**
1. Keep lowercase (rejected - not POSIX compliant)
2. Add uppercase aliases (rejected - confusing)
3. Change to uppercase ✅ (selected - clear and standard)

**Trade-offs:**
- ➕ Standards compliant
- ➕ Industry best practice
- ➖ Breaking change for users setting env vars

---

## 5. Implementation Details

### 5.1 Exit Codes

**File:** `src/fabric_cli/core/fab_constant.py`

```python
# Exit codes (POSIX compliant)
# 0 - Success
# 1 - General errors
# 2 - Misuse of shell builtins
# 126 - Command cannot execute
# 127 - Command not found
# 128+n - Fatal error signal "n"
EXIT_CODE_SUCCESS = 0
EXIT_CODE_ERROR = 1
EXIT_CODE_CANCELLED_OR_MISUSE_BUILTINS = 2
EXIT_CODE_CANNOT_EXECUTE = 126  # Used for authorization/permission errors
EXIT_CODE_COMMAND_NOT_FOUND = 127
```

**Usage:**

```python
# In fab_decorators.py
if e.status_code == ERROR_UNAUTHORIZED:
    return EXIT_CODE_CANNOT_EXECUTE  # Returns 126
```

### 5.2 Signal Handling

**File:** `src/fabric_cli/main.py`

```python
import signal
import sys

def _signal_handler(signum, frame):
    """Handle POSIX signals gracefully."""
    signal_names = {
        signal.SIGINT: "SIGINT",
        signal.SIGTERM: "SIGTERM",
        signal.SIGHUP: "SIGHUP",
        signal.SIGQUIT: "SIGQUIT",
    }
    
    signal_name = signal_names.get(signum, f"Signal {signum}")
    sys.stderr.write(f"\n{signal_name} received, exiting gracefully...\n")
    sys.stderr.flush()
    
    # Exit with 128 + signal number (POSIX convention)
    sys.exit(128 + signum)

def _setup_signal_handlers():
    """Setup POSIX-compliant signal handlers."""
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGQUIT, _signal_handler)
    if hasattr(signal, 'SIGHUP'):
        signal.signal(signal.SIGHUP, _signal_handler)

def main():
    _setup_signal_handlers()  # Called at startup
    # ... rest of main
```

**Signal-to-Exit-Code Mapping:**

| Signal | Number | Exit Code | Use Case |
|--------|--------|-----------|----------|
| SIGINT | 2 | 130 | User pressed Ctrl+C |
| SIGTERM | 15 | 143 | System/Docker shutdown |
| SIGQUIT | 3 | 131 | User pressed Ctrl+\ |
| SIGHUP | 1 | 129 | Terminal disconnect |

### 5.3 Environment Variables

**File:** `src/fabric_cli/core/fab_constant.py`

```python
# Env variables (POSIX compliant: uppercase with underscores)
FAB_TOKEN = "FAB_TOKEN"
FAB_TOKEN_ONELAKE = "FAB_TOKEN_ONELAKE"
FAB_TOKEN_AZURE = "FAB_TOKEN_AZURE"
FAB_SPN_CLIENT_ID = "FAB_SPN_CLIENT_ID"
FAB_SPN_CLIENT_SECRET = "FAB_SPN_CLIENT_SECRET"
FAB_SPN_CERT_PATH = "FAB_SPN_CERT_PATH"
FAB_SPN_CERT_PASSWORD = "FAB_SPN_CERT_PASSWORD"
FAB_SPN_FEDERATED_TOKEN = "FAB_SPN_FEDERATED_TOKEN"
FAB_TENANT_ID = "FAB_TENANT_ID"
FAB_REFRESH_TOKEN = "FAB_REFRESH_TOKEN"
IDENTITY_TYPE = "IDENTITY_TYPE"
FAB_AUTH_MODE = "FAB_AUTH_MODE"
FAB_AUTHORITY = "FAB_AUTHORITY"
```

**Usage:**

```python
# In fab_auth.py
import os
from fabric_cli.core import fab_constant

# Get token from environment
token = os.environ.get(fab_constant.FAB_TOKEN)  # Looks for "FAB_TOKEN"
tenant_id = os.environ.get(fab_constant.FAB_TENANT_ID)  # Looks for "FAB_TENANT_ID"
```

### 5.4 Help and Version Flags

**Help Flag:**
- Automatically provided by argparse
- No custom implementation needed
- Both `-h` and `--help` work by default

**Version Flag:**

**File:** `src/fabric_cli/core/fab_parser_setup.py`

```python
# -v/-V and --version (POSIX compliant: both short and long forms)
parser.add_argument("-v", "-V", "--version", action="store_true")
```

---

## 6. Testing Strategy

### 6.1 Test Coverage

**File:** `tests/test_posix_compliance.py`

**Test Classes:**
1. `TestExitCodes` - Verify exit code values
2. `TestHelpFlags` - Verify help flag patterns
3. `TestVersionFlags` - Verify version flag patterns
4. `TestSignalHandling` - Verify signal handlers
5. `TestEnvironmentVariables` - Verify env var naming
6. `TestStandardStreams` - Verify stdout/stderr usage
7. `TestOptionPatterns` - Verify option syntax

**Total:** 37 tests

### 6.2 Test Execution

```bash
# Run all POSIX compliance tests
pytest tests/test_posix_compliance.py -v

# Run with coverage
pytest tests/test_posix_compliance.py --cov=fabric_cli

# Run specific test class
pytest tests/test_posix_compliance.py::TestSignalHandling -v
```

### 6.3 Manual Testing

```bash
# Test help flags
fab -h
fab --help
fab ls -h

# Test version flags
fab -v
fab -V
fab --version

# Test exit codes
fab auth login; echo $?  # Should be 0 or 1/126
fab nonexistent_command; echo $?  # Should be appropriate error code

# Test signal handling
fab <command> &
kill -TERM $!  # Should exit with 143
```

### 6.4 Integration Testing

```bash
# Test in shell scripts
#!/bin/bash
fab auth login
if [ $? -eq 126 ]; then
    echo "Authorization error"
    exit 1
fi

# Test with environment variables
export FAB_TOKEN="..."
export FAB_TENANT_ID="..."
fab ls

# Test signal handling in Docker
docker run -it fabric-cli fab <long-running-command>
docker stop <container>  # Should exit gracefully with 143
```

---

## 7. Migration Guide

### 7.1 For Users

#### Environment Variables (Breaking Change)

**Before:**
```bash
export fab_token="eyJ..."
export fab_tenant_id="..."
export fab_spn_client_id="..."
export fab_spn_client_secret="..."
```

**After:**
```bash
export FAB_TOKEN="eyJ..."
export FAB_TENANT_ID="..."
export FAB_SPN_CLIENT_ID="..."
export FAB_SPN_CLIENT_SECRET="..."
```

**Script Updates:**
```bash
# Option 1: Update all environment variable names
sed -i 's/fab_token=/FAB_TOKEN=/g' setup.sh
sed -i 's/fab_tenant_id=/FAB_TENANT_ID=/g' setup.sh

# Option 2: Create wrapper script
#!/bin/bash
# wrapper.sh - Converts old env vars to new format
export FAB_TOKEN="${fab_token:-$FAB_TOKEN}"
export FAB_TENANT_ID="${fab_tenant_id:-$FAB_TENANT_ID}"
# ... rest of exports
```

#### Exit Codes (Breaking Change)

**Before:**
```bash
fab auth login
if [ $? -eq 4 ]; then
    echo "Authorization required"
fi
```

**After:**
```bash
fab auth login
case $? in
    0)
        echo "Success"
        ;;
    126)
        echo "Authorization/permission error"
        ;;
    1)
        echo "General error"
        ;;
    *)
        echo "Other error: $?"
        ;;
esac
```

### 7.2 For Developers

#### Exit Code Constants

**Before:**
```python
from fabric_cli.core import fab_constant
if auth_error:
    return fab_constant.EXIT_CODE_AUTHORIZATION_REQUIRED  # No longer exists
```

**After:**
```python
from fabric_cli.core import fab_constant
if auth_error:
    return fab_constant.EXIT_CODE_CANNOT_EXECUTE  # Use 126
```

#### Environment Variable Access

**Before:**
```python
token = os.environ.get(fab_constant.FAB_TOKEN)  # Returns "fab_token"
```

**After:**
```python
token = os.environ.get(fab_constant.FAB_TOKEN)  # Returns "FAB_TOKEN"
```

---

## 8. Future Considerations

### 8.1 Additional POSIX Enhancements

1. **Option Terminator (`--`)**
   - Implement `--` to separate options from arguments
   - Example: `fab ls -- -strange-name.txt`

2. **Long Option Equivalents**
   - Ensure all short options have long equivalents
   - Example: `-f` → `--force`, `-q` → `--quiet`

3. **Option Bundling**
   - Allow combining single-character options
   - Example: `-abc` equivalent to `-a -b -c`

4. **Exit Code Granularity**
   - Add more specific exit codes for different error types
   - Example: 3 for network errors, 5 for file I/O errors

### 8.2 Cross-Platform Considerations

1. **Windows Support**
   - Signals work differently on Windows
   - Consider signal emulation or Windows-specific handlers

2. **Signal Recovery**
   - Implement cleanup handlers before exit
   - Save state, close connections, flush buffers

3. **Locale Support**
   - POSIX locale standards (LC_ALL, LANG, etc.)
   - UTF-8 handling in different environments

### 8.3 Performance

1. **Signal Handler Overhead**
   - Minimal impact on performance
   - Handlers execute only on signal receipt

2. **Exit Code Checking**
   - No performance impact
   - Simple integer comparisons

---

## 9. Conclusion

The Fabric CLI now adheres to POSIX standards across all major areas:

✅ **Exit Codes** - Standard values (0, 1, 2, 126, 127, 128+n)  
✅ **Command-Line Options** - Standard syntax (`-h`, `--help`)  
✅ **Signal Handling** - Comprehensive handlers (SIGINT, SIGTERM, SIGHUP, SIGQUIT)  
✅ **Environment Variables** - Uppercase naming convention  
✅ **Standard Streams** - Proper stdout/stderr usage  

### Benefits

1. **Portability** - Works consistently across Unix-like systems
2. **Interoperability** - Better integration with shell scripts and automation
3. **Standards Compliance** - Follows industry best practices
4. **Predictability** - Expected behavior for command-line users
5. **Container Support** - Graceful shutdown in Docker/Kubernetes

### Breaking Changes

⚠️ **Environment Variables** - Must use uppercase (FAB_TOKEN, not fab_token)  
⚠️ **Exit Code 4** - Replaced with 126 for authorization errors  

### Testing

✅ 37 comprehensive POSIX compliance tests (all passing)  
✅ Manual testing completed  
✅ Integration testing guidelines provided  

---

## References

- [POSIX.1-2017 Standard](https://pubs.opengroup.org/onlinepubs/9699919799/)
- [Shell & Utilities](https://pubs.opengroup.org/onlinepubs/9699919799/utilities/V3_chap02.html)
- [Exit Status Values](https://pubs.opengroup.org/onlinepubs/9699919799/utilities/V3_chap02.html#tag_18_08_02)
- [Utility Conventions](https://pubs.opengroup.org/onlinepubs/9699919799/basedefs/V1_chap12.html)
- [Signal Concepts](https://pubs.opengroup.org/onlinepubs/9699919799/functions/V2_chap02.html#tag_15_04)
- [Environment Variables](https://pubs.opengroup.org/onlinepubs/9699919799/basedefs/V1_chap08.html)

---

**Document Version:** 1.0  
**Last Updated:** 2026-01-15  
**Status:** Implementation Complete
