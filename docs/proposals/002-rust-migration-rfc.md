# RFC-002: Rust Migration & Agentic CLI Architecture

| Field          | Value                                                      |
|----------------|------------------------------------------------------------|
| **Status**     | Draft                                                      |
| **Authors**    | Fabric CLI Team                                            |
| **Created**    | 2026-03-15                                                 |
| **Updated**    | 2026-03-15                                                 |
| **Supersedes** | Current Python implementation (`ms-fabric-cli` v1.4.0)     |

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Motivation](#2-motivation)
3. [Current Architecture Analysis](#3-current-architecture-analysis)
4. [Proposed Rust Architecture](#4-proposed-rust-architecture)
5. [Authentication Migration: MSAL → Azure Identity](#5-authentication-migration-msal--azure-identity)
6. [Performance Benchmark Methodology](#6-performance-benchmark-methodology)
7. [REPL & Command-Line Mode Design](#7-repl--command-line-mode-design)
8. [Agentic CLI Design](#8-agentic-cli-design)
9. [Rust Crate Selection](#9-rust-crate-selection)
10. [Migration Phases](#10-migration-phases)
11. [Risk Analysis](#11-risk-analysis)
12. [Decision Log](#12-decision-log)

---

## 1. Executive Summary

This RFC proposes migrating the Microsoft Fabric CLI (`fab`) from Python to Rust, replacing MSAL with the Azure Identity SDK, and redesigning the CLI as an **agentic-first** tool. The migration targets significant improvements in startup latency, memory footprint, and throughput—critical for agent-driven automation at scale—while maintaining feature parity with the current Python implementation across both REPL (interactive) and command-line modes.

### Key Outcomes

| Dimension            | Current (Python)         | Target (Rust)                  |
|----------------------|--------------------------|--------------------------------|
| Cold start           | ~800–1200 ms             | < 50 ms                       |
| Binary distribution  | pip + Python runtime     | Single static binary (~10 MB) |
| Memory (idle REPL)   | ~45–60 MB                | < 10 MB                       |
| Auth library         | MSAL (`msal[broker]`)   | `azure_identity` (Rust SDK)   |
| Agent interface      | stdout text/JSON         | Structured JSON, MCP, tool-use |
| Concurrent API calls | GIL-limited threads      | Tokio async, true parallelism |

---

## 2. Motivation

### 2.1 Performance & Distribution

The Python CLI currently requires a Python 3.10+ runtime and `pip install`, creating friction for:

- **CI/CD pipelines** that need to install Python + pip dependencies on every run.
- **Agent runtimes** (LangChain, Semantic Kernel, AutoGen) that spawn CLI subprocesses and pay startup cost per invocation.
- **Containerized environments** that benefit from small, static binaries.

Rust produces a single self-contained binary with near-instant startup, eliminating the Python interpreter overhead and dependency resolution.

### 2.2 Agentic CLI Paradigm

The industry is shifting toward AI agents that orchestrate tools via CLIs. Modern agents (GPT-4, Claude, Copilot) use CLIs as tool-calling interfaces. An agentic CLI must:

- **Start instantly** — agents spawn hundreds of subprocesses.
- **Emit structured output** — JSON/JSON Lines that agents parse without heuristics.
- **Support machine-readable error codes** — so agents can decide retry/fallback logic.
- **Expose a tool manifest** — describing available commands, parameters, and types for LLM function-calling schemas.
- **Minimize resource consumption** — agents run many tools concurrently.

### 2.3 Azure Identity Alignment

The current MSAL-based auth (`msal[broker]`, `msal_extensions`) works but:

- Requires managing encrypted token caches manually.
- Does not align with the Azure SDK's unified `TokenCredential` chain.
- The Rust `azure_identity` crate provides `DefaultAzureCredential` with automatic chaining (environment → managed identity → Azure CLI → interactive browser), simplifying auth configuration.

---

## 3. Current Architecture Analysis

### 3.1 Codebase Metrics

| Metric                | Value                       |
|-----------------------|-----------------------------|
| Python source files   | 242                         |
| Lines of code         | ~24,000                     |
| Command categories    | 9 (auth, api, config, fs, jobs, acls, labels, tables, +parsers) |
| Individual commands   | 61 (registered via argparse) |
| Resource types        | 18+ (Workspace, Notebook, SemanticModel, etc.) |
| API endpoints         | 4 (Fabric, OneLake, Azure Management, Power BI) |
| Auth modes            | 5 (interactive, SPN secret, SPN cert, federated, managed identity) |
| Test files            | 64                          |
| Test LOC              | ~15,000                     |

### 3.2 Architecture Diagram (Current)

```
┌─────────────────────────────────────────────────────┐
│                    fab (Python CLI)                  │
├──────────┬──────────┬───────────┬───────────────────┤
│ argparse │ REPL     │ Commands  │ Output Formatting │
│ parsers  │ (prompt  │ (61 cmds  │ (text/json/table) │
│ (13      │  toolkit)│  in 9     │                   │
│  modules)│          │  areas)   │                   │
├──────────┴──────────┴───────────┴───────────────────┤
│            Core Layer                                │
│  ┌──────────┐  ┌────────────┐  ┌─────────────────┐ │
│  │ FabAuth  │  │ FabContext │  │ MemStore (cache) │ │
│  │ (MSAL)   │  │ (nav pwd)  │  │ (cachetools)     │ │
│  └──────────┘  └────────────┘  └─────────────────┘ │
├─────────────────────────────────────────────────────┤
│          API Client (requests + retry)              │
│  ┌─────────┐  ┌──────────┐  ┌──────┐  ┌─────────┐ │
│  │ Fabric  │  │ OneLake  │  │Azure │  │Power BI │ │
│  │ API     │  │ DFS API  │  │Mgmt  │  │API      │ │
│  └─────────┘  └──────────┘  └──────┘  └─────────┘ │
├─────────────────────────────────────────────────────┤
│  Config: ~/.config/fab/{config,auth,context,cache}  │
└─────────────────────────────────────────────────────┘
```

### 3.3 Performance Bottlenecks in Python

| Bottleneck             | Impact                                         | Root Cause                              |
|------------------------|-------------------------------------------------|-----------------------------------------|
| Cold start latency     | ~800–1200 ms per invocation                     | Python interpreter + module imports      |
| Import chain           | 13 parser modules + all commands loaded eagerly  | argparse subparser registration          |
| MSAL initialization    | ~200 ms for encrypted cache load                 | `msal_extensions` + crypto operations    |
| GIL contention         | Limited HTTP concurrency                         | Python GIL prevents true parallelism     |
| Memory baseline        | ~45–60 MB idle                                   | Python runtime + loaded modules          |
| Lazy load workaround   | Only `questionary` deferred via `fab_lazy_load`  | Ad-hoc, not systematic                   |

---

## 4. Proposed Rust Architecture

### 4.1 High-Level Design

```
┌──────────────────────────────────────────────────────────┐
│                    fab (Rust CLI)                         │
├────────────┬─────────────┬───────────┬───────────────────┤
│ clap v4    │ REPL        │ Commands  │ Output Formatter  │
│ (derive    │ (rustyline  │ (modular  │ (serde_json,      │
│  macros,   │  + custom   │  command  │  tabled,          │
│  subcommds)│  completer) │  trait)   │  json-lines)      │
├────────────┴─────────────┴───────────┴───────────────────┤
│                    Core Layer                             │
│  ┌──────────────┐  ┌────────────┐  ┌──────────────────┐ │
│  │ AzureIdentity│  │ Context    │  │ Cache (moka)     │ │
│  │ (DefaultAzure│  │ (nav state │  │ (async, TTL,     │ │
│  │  Credential) │  │  + persist)│  │  bounded)        │ │
│  └──────────────┘  └────────────┘  └──────────────────┘ │
├──────────────────────────────────────────────────────────┤
│              HTTP Client (reqwest + tower)                │
│  ┌─────────┐  ┌──────────┐  ┌──────┐  ┌──────────────┐ │
│  │ Fabric  │  │ OneLake  │  │Azure │  │ Power BI     │ │
│  │ API     │  │ DFS API  │  │Mgmt  │  │ API          │ │
│  └─────────┘  └──────────┘  └──────┘  └──────────────┘ │
├──────────────────────────────────────────────────────────┤
│  Agentic Layer                                           │
│  ┌──────────────┐  ┌───────────────┐  ┌───────────────┐ │
│  │ Tool Manifest│  │ MCP Server    │  │ JSON-Lines    │ │
│  │ (OpenAPI/    │  │ (stdio/SSE    │  │ Streaming     │ │
│  │  JSON Schema)│  │  transport)   │  │ Output        │ │
│  └──────────────┘  └───────────────┘  └───────────────┘ │
├──────────────────────────────────────────────────────────┤
│   Config: ~/.config/fab/{config,context}.json            │
│   Auth:   Delegated to azure_identity credential chain   │
└──────────────────────────────────────────────────────────┘
```

### 4.2 Module Structure

```
fab-cli/                         (Cargo workspace)
├── Cargo.toml                   (workspace root)
├── crates/
│   ├── fab-cli/                 (binary crate — entry point)
│   │   ├── src/
│   │   │   ├── main.rs          (CLI entry, clap dispatch)
│   │   │   ├── repl.rs          (interactive REPL loop)
│   │   │   └── commands/
│   │   │       ├── mod.rs
│   │   │       ├── auth.rs
│   │   │       ├── fs.rs        (ls, cd, mkdir, rm, get, set, cp, mv)
│   │   │       ├── jobs.rs
│   │   │       ├── config.rs
│   │   │       ├── api.rs
│   │   │       ├── acls.rs
│   │   │       ├── labels.rs
│   │   │       └── tables.rs
│   │   └── Cargo.toml
│   ├── fab-core/                (library crate — shared logic)
│   │   ├── src/
│   │   │   ├── lib.rs
│   │   │   ├── auth.rs          (azure_identity integration)
│   │   │   ├── client.rs        (reqwest HTTP client)
│   │   │   ├── context.rs       (navigation state)
│   │   │   ├── cache.rs         (moka in-memory cache)
│   │   │   ├── config.rs        (JSON config persistence)
│   │   │   ├── types.rs         (Fabric resource types)
│   │   │   ├── errors.rs        (error hierarchy)
│   │   │   ├── output.rs        (formatter: json/text/table)
│   │   │   └── hierarchy.rs     (Tenant > Workspace > Folder > Item)
│   │   └── Cargo.toml
│   └── fab-agent/               (library crate — agentic interfaces)
│       ├── src/
│       │   ├── lib.rs
│       │   ├── manifest.rs      (tool manifest generation)
│       │   ├── mcp.rs           (Model Context Protocol server)
│       │   └── jsonlines.rs     (streaming structured output)
│       └── Cargo.toml
├── tests/                       (integration tests)
│   ├── cli_tests.rs
│   ├── auth_tests.rs
│   ├── repl_tests.rs
│   └── fixtures/
└── benches/                     (criterion benchmarks)
    ├── startup.rs
    ├── http_throughput.rs
    ├── filesystem_ops.rs
    └── repl_responsiveness.rs
```

### 4.3 Command Trait Design

```rust
use async_trait::async_trait;
use clap::Subcommand;

/// Every command implements this trait for uniform dispatch.
#[async_trait]
pub trait FabCommand {
    /// Execute the command and return structured output.
    async fn execute(&self, ctx: &mut FabContext) -> Result<CommandOutput, FabError>;
}

/// Structured output that can be rendered as text, JSON, table, or JSON-Lines.
pub enum CommandOutput {
    /// Single JSON value (object or array).
    Json(serde_json::Value),
    /// Streaming JSON-Lines for large result sets.
    JsonLines(Vec<serde_json::Value>),
    /// Plain text message.
    Text(String),
    /// Empty (no output, e.g., successful delete).
    Empty,
}
```

---

## 5. Authentication Migration: MSAL → Azure Identity

### 5.1 Current State (Python + MSAL)

The current implementation uses `msal[broker]` and `msal_extensions`:

```python
# Current: fab_auth.py (~850 lines)
from msal import PublicClientApplication, ConfidentialClientApplication
from msal_extensions import build_encrypted_persistence

class FabAuth:
    def get_access_token(self, scope) -> str:
        # 1. Check env vars (FAB_TOKEN, FAB_TOKEN_ONELAKE, FAB_TOKEN_AZURE)
        # 2. Try MSAL silent token acquisition
        # 3. Fall back to interactive/device-code flow
        # 4. Manage encrypted cache in ~/.config/fabric_cli/cache.bin
```

**Pain points:**
- Manual cache encryption management (`msal_extensions`).
- Separate code paths for each auth mode (5 modes × 3 scopes = complex matrix).
- `MsalTokenCredential` bridge class needed to wrap MSAL for Azure SDK compatibility.
- ~850 lines of auth code.

### 5.2 Proposed State (Rust + Azure Identity)

```rust
use azure_identity::DefaultAzureCredential;
use azure_core::auth::TokenCredential;

/// Simplified auth: DefaultAzureCredential chains all auth methods automatically.
pub struct FabAuth {
    credential: Arc<dyn TokenCredential>,
}

impl FabAuth {
    pub async fn new() -> Result<Self, FabError> {
        // DefaultAzureCredential automatically tries (in order):
        // 1. Environment variables (AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_CLIENT_SECRET)
        // 2. Managed Identity (system/user-assigned)
        // 3. Azure CLI credential
        // 4. Azure Developer CLI credential
        // 5. Interactive browser (if enabled)
        let credential = DefaultAzureCredential::new()
            .map_err(|e| FabError::auth(format!("Failed to initialize Azure credential chain: {e}")))?;
        Ok(Self { credential: Arc::new(credential) })
    }

    pub async fn get_token(&self, scope: &str) -> Result<String, FabError> {
        let token = self.credential
            .get_token(&[scope])
            .await?;
        Ok(token.token.secret().to_string())
    }
}
```

### 5.3 Auth Mode Mapping

| Current (MSAL)                       | Rust (azure_identity)                          | Environment Variables              |
|--------------------------------------|------------------------------------------------|------------------------------------|
| Interactive browser login            | `DefaultAzureCredential` → interactive         | (none, auto-detected)              |
| SPN + client secret                  | `ClientSecretCredential`                       | `AZURE_CLIENT_ID/SECRET/TENANT_ID` |
| SPN + certificate                    | `ClientCertificateCredential`                  | `AZURE_CLIENT_CERTIFICATE_PATH`    |
| SPN + federated (GitHub Actions)     | `WorkloadIdentityCredential` (via Default)     | `AZURE_FEDERATED_TOKEN_FILE`       |
| Managed Identity                     | `ManagedIdentityCredential` (via Default)      | `AZURE_CLIENT_ID` (user-assigned)  |
| Pre-set token (`FAB_TOKEN`)          | Custom `StaticTokenCredential`                 | `FAB_TOKEN` (preserved)            |

### 5.4 Migration Benefits

| Aspect                  | MSAL (Python)                    | azure_identity (Rust)                 |
|-------------------------|----------------------------------|---------------------------------------|
| Lines of auth code      | ~850                             | ~150 (estimated)                      |
| Token cache             | Manual encrypted file            | Automatic (OS keyring via `azure_identity`) |
| Credential chaining     | Manual if/else chain             | `DefaultAzureCredential` auto-chain   |
| Azure SDK compatibility | Requires `MsalTokenCredential` bridge | Native `TokenCredential` trait         |
| Broker support (WAM)    | `msal[broker]` optional extra    | Future: `azure_identity` broker       |

### 5.5 Environment Variable Migration

To maintain backward compatibility during the transition, `fab` should support both the current `FAB_*` environment variables and the Azure SDK standard `AZURE_*` variables:

```rust
// Priority: FAB_* (legacy) > AZURE_* (standard) > DefaultAzureCredential chain
fn resolve_credential(config: &FabConfig) -> Arc<dyn TokenCredential> {
    if let Some(token) = env::var("FAB_TOKEN").ok() {
        return Arc::new(StaticTokenCredential::new(token));
    }
    if let Some(client_id) = env::var("FAB_SPN_CLIENT_ID").ok() {
        // Map FAB_* to AZURE_* for azure_identity compatibility
        env::set_var("AZURE_CLIENT_ID", &client_id);
        env::set_var("AZURE_TENANT_ID", env::var("FAB_TENANT_ID").unwrap_or_default());
        if let Some(secret) = env::var("FAB_SPN_CLIENT_SECRET").ok() {
            env::set_var("AZURE_CLIENT_SECRET", &secret);
        }
    }
    Arc::new(DefaultAzureCredential::new()
        .map_err(|e| FabError::auth(format!("Failed to initialize Azure credential chain: {e}")))?)
}
```

---

## 6. Performance Benchmark Methodology

### 6.1 Benchmark Categories

We propose four categories aligned with the critical paths of CLI usage, especially in agentic contexts:

#### A. Cold Start / Load Time

**What it measures:** Time from process spawn to first useful output.

**Why it matters:** Agents spawn `fab` as a subprocess hundreds of times. Every millisecond of startup cost is multiplied.

**Benchmark design:**

```bash
# Benchmark: time to `--version` (minimal path)
hyperfine --warmup 3 --min-runs 100 \
  'fab --version' \
  './fab-rust --version'

# Benchmark: time to `--help` (parser initialization)
hyperfine --warmup 3 --min-runs 100 \
  'fab --help' \
  './fab-rust --help'

# Benchmark: time to first command parse (no network)
hyperfine --warmup 3 --min-runs 50 \
  'fab ls --help' \
  './fab-rust ls --help'
```

**Expected results:**

| Scenario        | Python (ms) | Rust (ms) | Speedup |
|-----------------|-------------|-----------|---------|
| `--version`     | 800–1200    | 5–15      | ~80–100× |
| `--help`        | 900–1400    | 10–25     | ~50–90×  |
| `ls --help`     | 1000–1500   | 10–30     | ~50–80×  |

**Criterion benchmark (Rust-internal):**

```rust
// benches/startup.rs
use criterion::{criterion_group, criterion_main, Criterion};

fn bench_cli_parse(c: &mut Criterion) {
    c.bench_function("parse_ls_command", |b| {
        b.iter(|| {
            let parsed_command = Cli::parse_from(["fab", "ls", "/workspace.Workspace"]);
            std::hint::black_box(parsed_command);
        })
    });
}

fn bench_config_load(c: &mut Criterion) {
    c.bench_function("load_config_json", |b| {
        b.iter(|| {
            let config = FabConfig::load_from_path("/tmp/test_config.json");
            std::hint::black_box(config);
        })
    });
}

criterion_group!(startup, bench_cli_parse, bench_config_load);
criterion_main!(startup);
```

#### B. HTTP Call Throughput

**What it measures:** End-to-end latency for API calls, including auth token acquisition, TLS handshake, request serialization, and response parsing.

**Why it matters:** Most commands make 1–5 API calls. Network dominates wall-clock time, but client-side overhead (serialization, auth, retry logic) adds up—especially under concurrency.

**Benchmark design:**

```bash
# Benchmark: single API call (mocked server)
# Uses a local HTTP server returning fixed JSON responses
hyperfine --warmup 5 --min-runs 50 \
  'fab ls /workspace.Workspace --output json' \
  './fab-rust ls /workspace.Workspace --output json'

# Benchmark: paginated listing (100 items across 5 pages)
hyperfine --warmup 3 --min-runs 20 \
  'fab ls /workspace.Workspace --top 100 --output json' \
  './fab-rust ls /workspace.Workspace --top 100 --output json'

# Benchmark: concurrent API calls (batch operations)
hyperfine --warmup 3 --min-runs 20 \
  'fab api request GET /v1/workspaces --output json && fab api request GET /v1/capacities --output json' \
  './fab-rust batch /v1/workspaces /v1/capacities --output json'
```

**Expected results:**

| Scenario              | Python (ms) | Rust (ms) | Notes                           |
|-----------------------|-------------|-----------|----------------------------------|
| Single GET (mocked)   | 900–1400    | 50–100    | Startup dominates in Python      |
| Paginated 5-page GET  | 1500–2500   | 200–400   | Rust: parallel page fetch        |
| 2 concurrent GETs     | 2000–3000   | 100–200   | Rust: tokio::join!, Python: serial |

**Criterion benchmark (Rust-internal):**

```rust
// benches/http_throughput.rs
use criterion::{criterion_group, criterion_main, Criterion};

fn bench_json_serialization(c: &mut Criterion) {
    let items: Vec<FabricItem> = generate_test_items(1000);
    c.bench_function("serialize_1000_items", |b| {
        b.iter(|| {
            let json = serde_json::to_string(&items).unwrap();
            std::hint::black_box(json);
        })
    });
}

fn bench_json_deserialization(c: &mut Criterion) {
    let json_str = include_str!("../tests/fixtures/workspace_items_1000.json");
    c.bench_function("deserialize_1000_items", |b| {
        b.iter(|| {
            let items: Vec<FabricItem> = serde_json::from_str(json_str).unwrap();
            std::hint::black_box(items);
        })
    });
}

criterion_group!(http, bench_json_serialization, bench_json_deserialization);
criterion_main!(http);
```

#### C. File System Operations

**What it measures:** Performance of export/import operations, config read/write, and OneLake file operations.

**Why it matters:** Commands like `cp`, `export`, `import`, and `deploy` involve file I/O. Config and context files are read on every invocation.

**Benchmark design:**

```bash
# Benchmark: config file load (JSON parse + validate)
hyperfine --warmup 5 --min-runs 100 \
  'fab config ls --output json' \
  './fab-rust config ls --output json'

# Benchmark: export operation (mocked API, write to disk)
hyperfine --warmup 3 --min-runs 20 \
  'fab export /ws.Workspace/item.Notebook --path /tmp/export_py' \
  './fab-rust export /ws.Workspace/item.Notebook --path /tmp/export_rs'

# Benchmark: large file handling (OneLake upload/download simulation)
hyperfine --warmup 2 --min-runs 10 \
  'fab cp /local/file.parquet /ws.Workspace/lh.Lakehouse/Files/' \
  './fab-rust cp /local/file.parquet /ws.Workspace/lh.Lakehouse/Files/'
```

**Expected results:**

| Scenario                 | Python (ms) | Rust (ms)  | Notes                        |
|--------------------------|-------------|------------|------------------------------|
| Config load + display    | 850–1200    | 15–40      | JSON parse: serde >> json    |
| Export 1 item (mocked)   | 1200–2000   | 100–300    | File I/O + startup           |
| 100 MB file upload       | 5000–8000   | 2000–4000  | Network-bound, Rust streams  |

**Criterion benchmark (Rust-internal):**

```rust
// benches/filesystem_ops.rs
use criterion::{criterion_group, criterion_main, Criterion};
use tempfile::TempDir;

fn bench_config_read_write(c: &mut Criterion) {
    let dir = TempDir::new().unwrap();
    let config = FabConfig::default();
    let path = dir.path().join("config.json");
    config.save(&path).unwrap();

    c.bench_function("config_load", |b| {
        b.iter(|| {
            let c = FabConfig::load_from_path(&path).unwrap();
            std::hint::black_box(c);
        })
    });

    c.bench_function("config_save", |b| {
        b.iter(|| {
            config.save(&path).unwrap();
        })
    });
}

fn bench_context_persistence(c: &mut Criterion) {
    let dir = TempDir::new().unwrap();
    let ctx = FabContext::with_path("/workspace.Workspace/folder.Folder");

    c.bench_function("context_save_load_cycle", |b| {
        b.iter(|| {
            let path = dir.path().join("context.json");
            ctx.save(&path).unwrap();
            let loaded = FabContext::load(&path).unwrap();
            std::hint::black_box(loaded);
        })
    });
}

criterion_group!(fs_ops, bench_config_read_write, bench_context_persistence);
criterion_main!(fs_ops);
```

#### D. REPL Responsiveness

**What it measures:** Keystroke-to-response latency in interactive mode, including tab completion and command execution.

**Why it matters:** Interactive users expect sub-100ms response times. Tab completion must feel instant.

**Benchmark design:**

```bash
# Benchmark: REPL startup to first prompt
echo "exit" | timeout 5 fab
echo "exit" | timeout 5 ./fab-rust

# Benchmark: command execution within REPL (pre-warmed)
# Use expect/pexpect to script REPL interactions
python3 -c "
import pexpect, time
child = pexpect.spawn('./fab-rust')
child.expect(r'fab:.*\$')
start = time.perf_counter()
child.sendline('ls --help')
child.expect(r'fab:.*\$')
elapsed = (time.perf_counter() - start) * 1000
print(f'REPL command: {elapsed:.1f} ms')
child.sendline('exit')
"
```

**Expected results:**

| Scenario                 | Python (ms) | Rust (ms) | Notes                        |
|--------------------------|-------------|-----------|------------------------------|
| REPL startup to prompt   | 1200–1800   | 20–50     | Module imports vs binary     |
| Command in REPL          | 50–150      | 5–20      | Already loaded, parse only   |
| Tab completion (50 items)| 100–300     | 10–30     | In-memory lookup             |

**Criterion benchmark (Rust-internal):**

```rust
// benches/repl_responsiveness.rs
use criterion::{criterion_group, criterion_main, Criterion};

fn bench_command_parse_in_repl(c: &mut Criterion) {
    // Simulate REPL command parsing (no network)
    c.bench_function("repl_parse_ls_command", |b| {
        b.iter(|| {
            let tokens = shlex::split("ls /workspace.Workspace -o json").unwrap();
            let cmd = parse_repl_command(&tokens);
            std::hint::black_box(cmd);
        })
    });
}

fn bench_tab_completion(c: &mut Criterion) {
    let completions = generate_completion_candidates(100);
    c.bench_function("tab_complete_50_items", |b| {
        b.iter(|| {
            let matches = completions.complete("sem");
            std::hint::black_box(matches);
        })
    });
}

criterion_group!(repl, bench_command_parse_in_repl, bench_tab_completion);
criterion_main!(repl);
```

### 6.2 Benchmarking Tools & Infrastructure

| Tool             | Purpose                                   | Phase         |
|------------------|-------------------------------------------|---------------|
| **hyperfine**    | Cross-language CLI startup/end-to-end     | Comparison    |
| **criterion.rs** | Micro-benchmarks for Rust internals       | Development   |
| **wrk / k6**     | HTTP throughput under load (mock server)  | Integration   |
| **pexpect**      | REPL interaction scripting                | REPL testing  |
| **valgrind/heaptrack** | Memory profiling                   | Optimization  |
| **tokio-console**| Async task profiling                      | Development   |

### 6.3 Benchmark Environment

All benchmarks should be run on standardized hardware:

- **CI runner**: GitHub Actions `ubuntu-latest` (2-core, 7 GB RAM)
- **Local reference**: Developer machine (Apple M-series or AMD64, 16+ GB RAM)
- **Controlled variables**: Same mock API server, same config files, same network conditions (localhost)

### 6.4 Continuous Benchmarking

Integrate criterion benchmarks into CI to detect performance regressions:

```yaml
# .github/workflows/bench.yml
name: Benchmarks
on:
  pull_request:
    paths: ['crates/**']
jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable
      - name: Run benchmarks
        run: cargo bench --workspace
      - name: Compare with baseline
        uses: benchmark-action/github-action-benchmark@v1
        with:
          tool: cargo-bench
          output-file-path: target/criterion/output.json
          alert-threshold: '120%'      # Alert if 20% slower
          fail-on-alert: true
```

---

## 7. REPL & Command-Line Mode Design

### 7.1 Dual-Mode Architecture

The Rust CLI must support both modes with a shared command execution core:

```rust
fn main() -> Result<(), FabError> {
    let runtime = tokio::runtime::Builder::new_multi_thread()
        .enable_all()
        .build()?;

    runtime.block_on(async {
        let config = FabConfig::load()?;
        let auth = FabAuth::new().await?;
        let mut ctx = FabContext::load_or_default(&config)?;

        match Cli::try_parse() {
            Ok(cli) => {
                // Command-line mode: parse → execute → exit
                let output = cli.command.execute(&mut ctx).await?;
                render_output(&output, cli.output_format);
                Ok(())
            }
            Err(_) if std::env::args().len() == 1 => {
                // No arguments: enter REPL mode
                repl::start(&mut ctx, &auth, &config).await
            }
            Err(e) => {
                // clap error (--help, --version, unknown flag) — exits process
                // with appropriate exit code (0 for help/version, 2 for errors)
                e.exit();
            }
        }
    })
}
```

### 7.2 REPL Implementation

```rust
// crates/fab-cli/src/repl.rs
use rustyline::{Editor, Config, EditMode};
use rustyline::hint::HistoryHinter;

pub async fn start(ctx: &mut FabContext, auth: &FabAuth, config: &FabConfig) -> Result<(), FabError> {
    let rl_config = Config::builder()
        .edit_mode(EditMode::Emacs)
        .auto_add_history(true)
        .build();

    let mut rl = Editor::with_config(rl_config)?;
    rl.set_helper(Some(FabCompleter::new(ctx)));

    // History file
    let history_path = config.data_dir().join("history.txt");
    let _ = rl.load_history(&history_path);

    loop {
        let prompt = format!("fab:{}$ ", ctx.current_path_display());
        match rl.readline(&prompt) {
            Ok(line) => {
                let line = line.trim();
                if line.is_empty() { continue; }
                if matches!(line, "exit" | "quit") { break; }

                match execute_repl_command(line, ctx, auth).await {
                    Ok(output) => render_output(&output, config.output_format()),
                    Err(e) => eprintln!("Error: {}", e),
                }
            }
            Err(ReadlineError::Interrupted) => {
                println!("Use 'exit' or 'quit' to leave.");
            }
            Err(ReadlineError::Eof) => break,
            Err(e) => return Err(e.into()),
        }
    }

    rl.save_history(&history_path)?;
    Ok(())
}
```

### 7.3 Feature Parity Matrix

| Feature                     | Python (current)        | Rust (target)            |
|-----------------------------|-------------------------|--------------------------|
| Command parsing             | argparse (13 modules)   | clap v4 (derive macros)  |
| Tab completion              | argcomplete             | rustyline + custom       |
| History                     | prompt_toolkit memory   | rustyline file-backed    |
| Styled prompt               | prompt_toolkit HTML     | crossterm + colored      |
| Shell-like editing          | prompt_toolkit          | rustyline Emacs/Vi mode  |
| Context persistence         | JSON file per PPID      | JSON file per PPID       |
| Keyboard interrupt          | `Ctrl+C` → continue    | `Ctrl+C` → continue     |
| EOF                         | `Ctrl+D` → exit        | `Ctrl+D` → exit         |
| Multiple commands           | `--commands` flag       | `--commands` flag        |

---

## 8. Agentic CLI Design

### 8.1 Design Principles for Agent-Friendly CLIs

Modern AI agents (GPT-4, Claude, Copilot, AutoGen, LangChain) interact with CLIs as external tools. The CLI must be designed as a **first-class tool interface**:

1. **Structured output by default** — Agents should not need to parse human-readable text.
2. **Machine-readable errors** — Error codes and structured error objects, not free-form messages.
3. **Discoverable capabilities** — A manifest describing all commands, parameters, and types.
4. **Idempotent operations** — Agents may retry commands; side effects should be safe to repeat.
5. **Streaming support** — For long-running operations, emit progress as JSON-Lines.
6. **Minimal startup cost** — Agents spawn CLIs frequently; fast startup is essential.
7. **Composable commands** — Small, focused commands that can be chained or batched.

### 8.2 Tool Manifest (for LLM Function Calling)

The CLI should be able to emit a machine-readable manifest of its capabilities:

```bash
$ fab --manifest
```

```json
{
  "name": "fab",
  "version": "2.0.0",
  "description": "Microsoft Fabric CLI — manage workspaces, items, and data assets",
  "commands": [
    {
      "name": "ls",
      "description": "List items in a Fabric path",
      "parameters": {
        "path": {
          "type": "string",
          "description": "Fabric path (e.g., /workspace.Workspace)",
          "required": true
        },
        "all": {
          "type": "boolean",
          "description": "Include hidden entities (.capacities, .gateways)",
          "default": false
        },
        "output": {
          "type": "string",
          "enum": ["json", "text", "table", "jsonl"],
          "default": "json"
        }
      },
      "returns": {
        "type": "array",
        "items": { "$ref": "#/types/FabricItem" }
      }
    }
  ],
  "types": {
    "FabricItem": {
      "type": "object",
      "properties": {
        "name": { "type": "string" },
        "type": { "type": "string" },
        "id": { "type": "string", "format": "uuid" }
      }
    }
  }
}
```

This manifest can be consumed by:

- **OpenAI function calling** schemas
- **Anthropic tool-use** definitions
- **LangChain `StructuredTool`** definitions
- **Semantic Kernel** plugin manifests
- **MCP tool definitions**

### 8.3 Model Context Protocol (MCP) Server Mode

The CLI should optionally run as an MCP server, allowing agents to invoke commands without subprocess overhead:

```bash
# Start as MCP server (stdio transport)
$ fab --mcp

# Start as MCP server (SSE transport for remote agents)
$ fab --mcp --transport sse --port 8080
```

**MCP integration:**

```rust
// crates/fab-agent/src/mcp.rs
use mcp_server::{McpServer, Tool, ToolResult};

pub async fn start_mcp_server(ctx: FabContext, auth: FabAuth) -> Result<(), FabError> {
    let server = McpServer::new("fab", "2.0.0");

    // Register each command as an MCP tool
    server.register_tool(Tool {
        name: "fab_ls",
        description: "List items in a Fabric workspace or path",
        input_schema: serde_json::json!({
            "type": "object",
            "properties": {
                "path": { "type": "string" },
                "all": { "type": "boolean" }
            },
            "required": ["path"]
        }),
        handler: |params| async {
            let path = params["path"].as_str().unwrap();
            let items = ls_command(path, &ctx, &auth).await?;
            Ok(ToolResult::json(items))
        },
    });

    // Start server on stdio (for Claude Desktop, Copilot, etc.)
    server.run_stdio().await
}
```

### 8.4 Structured Output Modes

```bash
# JSON (single response, default for agents)
$ fab ls /ws.Workspace --output json
{"items": [{"name": "report1", "type": "Report", "id": "..."}]}

# JSON-Lines (streaming, for large result sets)
$ fab ls /ws.Workspace --output jsonl
{"name": "report1", "type": "Report", "id": "..."}
{"name": "model1", "type": "SemanticModel", "id": "..."}

# Machine-readable errors
$ fab get /ws.Workspace/nonexistent.Notebook --output json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Item 'nonexistent.Notebook' not found in workspace",
    "request_id": "abc-123",
    "retryable": false
  }
}

# Exit codes for agent decision-making
# 0 = success, 1 = error, 2 = cancelled, 3 = auth required, 4 = not found, 5 = conflict
```

### 8.5 Agent-Friendly Batch Operations

```bash
# Batch mode: execute multiple commands, return array of results
$ fab batch --commands '["ls /ws.Workspace", "get /ws.Workspace/item.Report"]' --output json
[
  {"command": "ls /ws.Workspace", "status": "success", "result": [...]},
  {"command": "get /ws.Workspace/item.Report", "status": "success", "result": {...}}
]
```

### 8.6 Agent Workflow Example

```python
# Example: LangChain agent using fab as a tool
from langchain.tools import StructuredTool
import subprocess, json

def fab_tool(command: str) -> dict:
    result = subprocess.run(
        ["fab"] + command.split() + ["--output", "json"],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode == 0:
        return json.loads(result.stdout)
    else:
        return json.loads(result.stderr)  # Structured error

# With Rust CLI: ~50ms per invocation (vs ~1200ms with Python)
# An agent making 20 sequential tool calls saves ~23 seconds
```

### 8.7 Comparison: Python vs Rust for Agentic Use

| Metric                        | Python CLI     | Rust CLI       | Impact on Agents           |
|-------------------------------|----------------|----------------|----------------------------|
| Per-invocation startup        | ~1000 ms       | ~10 ms         | 100× faster tool calls     |
| 20 sequential tool calls      | ~25 s overhead | ~0.3 s overhead| Agent workflows 80× faster |
| Memory per instance           | ~50 MB         | ~5 MB          | 10× more concurrent tools  |
| MCP server mode               | Not supported  | Supported      | Zero subprocess overhead   |
| Tool manifest                 | Not available  | `--manifest`   | Auto-generate tool schemas  |
| Structured errors             | Partial        | Full JSON      | Reliable error handling     |
| JSON-Lines streaming          | Not available  | `--output jsonl`| Streaming large results    |

---

## 9. Rust Crate Selection

### 9.1 Core Dependencies

| Purpose              | Crate              | Version | Why                                           |
|----------------------|--------------------|---------|------------------------------------------------|
| CLI framework        | `clap`             | 4.x     | Derive macros, subcommands, completions, stable |
| Async runtime        | `tokio`            | 1.x     | Industry standard, mature, multi-threaded       |
| HTTP client          | `reqwest`          | 0.12+   | Built on hyper/tokio, TLS, connection pooling   |
| JSON                 | `serde` + `serde_json` | 1.x | Zero-cost serialization, derive macros         |
| Auth                 | `azure_identity`   | 0.22+   | Official Azure SDK, DefaultAzureCredential      |
| Azure core           | `azure_core`       | 0.22+   | TokenCredential trait, retry policies           |
| REPL                 | `rustyline`        | 14.x    | History, completion, Emacs/Vi modes             |
| Terminal colors      | `crossterm`        | 0.28+   | Cross-platform terminal manipulation            |
| Colored output       | `colored`          | 2.x     | Simple color API for text output                |
| In-memory cache      | `moka`             | 0.12+   | Concurrent cache with TTL, bounded size         |
| Config file          | `serde_json`       | 1.x     | JSON config (reuse serde)                       |
| Path resolution      | `dirs`             | 5.x     | Platform config/data directory resolution       |
| Error handling       | `thiserror`        | 2.x     | Derive error enums with display messages        |
| Error context        | `anyhow`           | 1.x     | Rich error context for binary crate             |
| Logging              | `tracing`          | 0.1.x   | Structured async-aware logging                  |
| Table formatting     | `tabled`           | 0.17+   | Text table rendering for `--output table`       |
| UUID                 | `uuid`             | 1.x     | GUID generation and parsing                     |
| Shell splitting      | `shlex`            | 1.x     | POSIX shell-like argument splitting for REPL    |
| Benchmarking         | `criterion`        | 0.5+    | Statistical micro-benchmarks                    |
| JSON path            | `jmespath`         | 0.3     | JMESPath query support (feature parity)         |
| YAML                 | `serde_yaml`       | 0.9     | command_support.yaml parsing                    |

### 9.2 Agentic Dependencies

| Purpose              | Crate              | Version | Why                                           |
|----------------------|--------------------|---------|------------------------------------------------|
| MCP server           | `mcp-server`       | 0.x     | Model Context Protocol implementation           |
| JSON Schema          | `schemars`         | 0.8     | Generate JSON Schema from Rust types            |
| JSON Lines           | `serde_json`       | 1.x     | Line-delimited JSON streaming (built-in)        |

### 9.3 Testing Dependencies

| Purpose              | Crate              | Version | Why                                           |
|----------------------|--------------------|---------|------------------------------------------------|
| Test framework       | built-in           | —       | `#[test]`, `#[tokio::test]`                   |
| Assertions           | `assert_cmd`       | 2.x     | CLI integration test assertions                |
| HTTP mocking         | `wiremock`         | 0.6+    | Mock HTTP server for API tests                 |
| Temp directories     | `tempfile`         | 3.x     | Temporary files and directories for tests       |
| Snapshot testing     | `insta`            | 1.x     | Snapshot-based output testing                   |
| Test fixtures        | `rstest`           | 0.22+   | Parameterized tests (like pytest parametrize)   |

---

## 10. Migration Phases

### Phase 0: Foundation (Weeks 1–3)

**Goal:** Scaffold the Rust workspace, set up CI, and implement core infrastructure.

- [ ] Initialize Cargo workspace with `fab-cli`, `fab-core`, `fab-agent` crates.
- [ ] Implement `FabConfig` (JSON config read/write, compatible with existing `~/.config/fab/config.json`).
- [ ] Implement `FabContext` (navigation state, PPID-based persistence).
- [ ] Implement `FabAuth` with `azure_identity::DefaultAzureCredential`.
- [ ] Implement HTTP client (`reqwest` + retry + auth header injection).
- [ ] Implement output formatter (JSON, text, table).
- [ ] Set up CI: `cargo build`, `cargo test`, `cargo clippy`, `cargo fmt`.
- [ ] Set up criterion benchmarks for startup, JSON serialization, config I/O.

### Phase 1: Core Commands (Weeks 4–7)

**Goal:** Implement the most-used commands to achieve a usable CLI.

- [ ] `fab auth login/logout/status` (azure_identity flows)
- [ ] `fab ls` (workspace listing, item listing, hidden collections)
- [ ] `fab cd` (context navigation)
- [ ] `fab get` (item details)
- [ ] `fab mkdir` (item creation for top resource types)
- [ ] `fab rm` (item deletion)
- [ ] `fab config ls/get/set`
- [ ] Implement REPL mode with rustyline.
- [ ] Integration tests with wiremock for all commands.

### Phase 2: Full Command Parity (Weeks 8–12)

**Goal:** Implement remaining commands and achieve feature parity.

- [ ] `fab cp`, `fab mv` (copy/move operations)
- [ ] `fab export`, `fab import` (item export/import)
- [ ] `fab jobs run/status/list/cancel`
- [ ] `fab acls ls/get/set/rm`
- [ ] `fab labels set/rm/list-local`
- [ ] `fab tables load/schema/optimize`
- [ ] `fab api request` (raw API calls)
- [ ] `fab open` (browser integration)
- [ ] `fab deploy` (configuration deployment)
- [ ] OneLake file operations (DFS API)
- [ ] All 18+ resource types across commands
- [ ] Shell completions (bash, zsh, PowerShell, fish)

### Phase 3: Agentic Features (Weeks 13–16)

**Goal:** Implement agentic-first interfaces.

- [ ] `fab --manifest` (tool manifest generation)
- [ ] `fab --mcp` (MCP server mode, stdio transport)
- [ ] `fab --mcp --transport sse` (MCP server, SSE transport)
- [ ] `fab batch` (multi-command execution)
- [ ] `--output jsonl` (JSON-Lines streaming)
- [ ] Structured error responses with error codes
- [ ] Extended exit codes for agent decision-making
- [ ] Documentation: agent integration guides for LangChain, Semantic Kernel, AutoGen

### Phase 4: Performance Validation & Release (Weeks 17–20)

**Goal:** Validate performance claims, publish benchmarks, and release.

- [ ] Run full benchmark suite (hyperfine, criterion, memory profiling)
- [ ] Publish benchmark results as part of documentation
- [ ] Cross-platform builds (Linux, macOS, Windows) via CI
- [ ] Binary distribution (GitHub Releases, Homebrew, winget, cargo install)
- [ ] Migration guide from Python `fab` to Rust `fab`
- [ ] Deprecation notice for Python version
- [ ] Release v2.0.0

---

## 11. Risk Analysis

### 11.1 Technical Risks

| Risk                                          | Likelihood | Impact | Mitigation                                                |
|-----------------------------------------------|------------|--------|-----------------------------------------------------------|
| `azure_identity` Rust crate lacks feature X   | Medium     | High   | Contribute upstream; fallback to raw MSAL REST calls      |
| MCP ecosystem too immature in Rust            | Medium     | Medium | Implement minimal MCP subset; use JSON-RPC directly       |
| REPL feature parity (prompt_toolkit is rich)  | Low        | Medium | rustyline covers 90%+; custom completer fills gaps        |
| Windows broker auth (WAM) not in Rust SDK     | High       | Medium | Use `az login` credential chain as fallback               |
| 242 Python files → Rust rewrite effort        | Low        | High   | Phased approach; Rust is more concise (~60% fewer lines)  |
| Community adoption friction (pip → binary)    | Medium     | Medium | Offer both `cargo install` and direct binary download     |

### 11.2 Organizational Risks

| Risk                                          | Likelihood | Impact | Mitigation                                                |
|-----------------------------------------------|------------|--------|-----------------------------------------------------------|
| Maintaining two codebases during migration    | High       | High   | Freeze Python at v1.x; focus Rust on v2                   |
| Contributors unfamiliar with Rust             | Medium     | Medium | Provide onboarding guide; leverage Rust's tooling          |
| Breaking existing user workflows              | Medium     | High   | Keep CLI interface identical; only internals change        |

### 11.3 What We Keep

- **CLI interface** — Same commands, flags, paths, and dot-suffix convention.
- **Config format** — Same `~/.config/fab/config.json` schema.
- **Context persistence** — Same PPID-based `context-{ppid}.json` files.
- **Environment variables** — All `FAB_*` variables honored (mapped to `AZURE_*` internally).
- **Output formats** — `text`, `json`, `table` (add `jsonl`).
- **Exit codes** — Same numeric codes (add more for agents).

---

## 12. Decision Log

| Decision                         | Options Considered                    | Chosen         | Rationale                                     |
|----------------------------------|---------------------------------------|----------------|-----------------------------------------------|
| Language                         | Python (optimize), Go, Rust           | Rust           | Best startup perf, memory safety, single binary |
| CLI framework                    | clap, argh, structopt                 | clap v4        | Most popular, derive macros, completions       |
| Auth library                     | MSAL REST, azure_identity, manual     | azure_identity | Official SDK, DefaultAzureCredential chain     |
| HTTP client                      | reqwest, hyper, ureq                  | reqwest        | High-level API, tokio integration, TLS         |
| Async runtime                    | tokio, async-std, smol                | tokio          | Ecosystem standard, most library support       |
| REPL library                     | rustyline, reedline, crossterm raw    | rustyline      | Mature, readline-compatible, history support   |
| Serialization                    | serde, manual, simd-json             | serde          | Ecosystem standard, zero-cost abstractions     |
| Cache                            | moka, dashmap+ttl, custom            | moka           | Concurrent, TTL, bounded, well-maintained      |
| MCP implementation               | Custom JSON-RPC, mcp-server crate    | mcp-server     | Standards-compliant, community maintained      |
| Benchmarking                     | criterion, divan, custom             | criterion      | Statistical, well-documented, CI integration   |

---

## Appendix A: Estimated Lines of Code (Rust vs Python)

| Module                | Python LOC | Estimated Rust LOC | Ratio  |
|-----------------------|------------|---------------------|--------|
| Auth                  | 850        | 150                 | 0.18×  |
| API client            | 550        | 300                 | 0.55×  |
| Commands (61)         | 12,000     | 7,000               | 0.58×  |
| Core (context, config)| 3,500      | 1,500               | 0.43×  |
| Output formatting     | 800        | 400                 | 0.50×  |
| REPL                  | 400        | 250                 | 0.63×  |
| Error handling        | 1,500      | 500                 | 0.33×  |
| Utilities             | 4,400      | 2,500               | 0.57×  |
| Agentic (new)         | —          | 800                 | new    |
| **Total**             | **24,000** | **~13,400**         | **0.56×** |

Rust's type system, pattern matching, and derive macros significantly reduce boilerplate while increasing safety guarantees.

## Appendix B: Binary Size Estimates

| Configuration            | Estimated Size |
|--------------------------|----------------|
| Debug build              | ~50 MB         |
| Release build            | ~15 MB         |
| Release + strip          | ~10 MB         |
| Release + strip + UPX    | ~4 MB          |

## Appendix C: Platform Build Matrix

| Platform            | Target Triple                  | CI Runner          |
|---------------------|-------------------------------|--------------------|
| Linux x86_64        | `x86_64-unknown-linux-musl`   | `ubuntu-latest`    |
| Linux aarch64       | `aarch64-unknown-linux-musl`  | `ubuntu-latest` (cross) |
| macOS x86_64        | `x86_64-apple-darwin`         | `macos-13`         |
| macOS aarch64       | `aarch64-apple-darwin`         | `macos-14`         |
| Windows x86_64      | `x86_64-pc-windows-msvc`     | `windows-latest`   |
| Windows aarch64     | `aarch64-pc-windows-msvc`    | `windows-latest` (cross) |

---

*This RFC is a living document. Updates will be made as decisions are refined and implementation progresses.*
