# Fabric CLI – Performance Benchmark Report

> **Date:** 2026-03-19 15:32 UTC  
> **Machine:** Linux aarch64  
> **Python:** 3.12.11  
> **Iterations per metric:** 10

## Summary

| Metric | PyPI (`1.5.0`) | Local (`1.5.0`) | Δ | |
|--------|---:|---:|---:|---|
| Startup (`fab --version`) | 155.5 ms | 157.0 ms | +1.0% | ⚠️ |
| Module import | 170.5 ms | 13.0 ms | -92.4% | ✅ |
| HTTP pipeline (mocked) | 13.7 ms | 49.8 ms | +263.5% | ❌ |
| Memory (peak RSS) | 83.2 MB | 69.4 MB | -16.6% | ✅ |
| Live API (`fab ls /`) | 1454.7 ms | 1307.3 ms | -10.1% | ✅ |

## Key Findings

- ➖ **Startup** is within **±1%** (no significant change)
- ✅ **Module import** improved by **92%**
- ❌ **HTTP pipeline** regressed by **264%**
- ✅ **Memory footprint** improved by **17%**

## Detailed Results

### 1. Startup Latency (`fab --version`)

Cold-start wall-clock time for a no-op `fab --version` invocation (subprocess).

| Stat | PyPI | Local |
|------|---:|---:|
| Median (ms) | 155.5 | 157.0 |
| Mean (ms) | 156.3 | 158.8 |
| Min (ms) | 153.1 | 153.6 |
| Max (ms) | 166.6 | 172.1 |
| P95 (ms) | 166.6 | 172.1 |
| Stdev (ms) | 3.8 | 6.1 |

### 2. Module Import Time

Time to `import fabric_cli.main` (in-process, modules cleared between runs).

| Stat | PyPI | Local |
|------|---:|---:|
| Median (ms) | 170.5 | 13.0 |
| Mean (ms) | 375.0 | 27.9 |
| Min (ms) | 59.2 | 12.2 |
| Max (ms) | 2562.9 | 162.5 |
| P95 (ms) | 2562.9 | 162.5 |
| Stdev (ms) | 770.7 | 47.3 |

### 3. HTTP Request Pipeline

End-to-end command execution with mocked network (`requests.Session.request`).
Measures argument parsing → auth token retrieval → URL construction → header building → request dispatch → response processing.

| Stat | PyPI | Local |
|------|---:|---:|
| Median (ms) | 13.7 | 49.8 |
| Mean (ms) | 16.3 | 53.7 |
| Min (ms) | 12.8 | 46.9 |
| Max (ms) | 40.1 | 70.8 |
| P95 (ms) | 40.1 | 70.8 |
| Stdev (ms) | 8.4 | 8.8 |

### 4. Memory Footprint

Peak RSS after importing `fabric_cli.main`.

| | PyPI | Local |
|--|---:|---:|
| Peak RSS | 83.2 MB | 69.4 MB |

### 5. Heavy Dependency Loading

Modules checked after `import fabric_cli.main`.

| Module | PyPI | Local |
|--------|------|------|
| `msal` | LOADED | deferred ✅ |
| `jwt` | LOADED | deferred ✅ |
| `cryptography` | LOADED | deferred ✅ |
| `requests` | LOADED | deferred ✅ |
| `prompt_toolkit` | LOADED | deferred ✅ |
| `psutil` | LOADED | deferred ✅ |

### 6. Live API Call (`fab ls /`)

End-to-end wall-clock time for listing workspaces against the live Fabric API.

| Stat | PyPI | Local |
|------|---:|---:|
| Median (ms) | 1454.7 | 1307.3 |
| Mean (ms) | 1525.7 | 1260.5 |
| Min (ms) | 1361.0 | 1047.6 |
| Max (ms) | 2129.8 | 1399.0 |
| P95 (ms) | 2129.8 | 1399.0 |

## Methodology

- Each version is installed into its own isolated virtualenv to prevent cross-contamination.
- Every timing metric is run **10** iterations; we report median, mean, p95, min, max, and σ.
- **Startup** is measured via a cold subprocess (`fab --version`).
- **Import** clears `sys.modules` between runs for a clean slate.
- **HTTP pipeline** patches `requests.Session.request` and auth to isolate CLI overhead from network latency. One warm-up iteration is discarded.
- **Memory** uses `resource.getrusage(RUSAGE_SELF).ru_maxrss`.
- **Live API** calls the real Fabric API endpoint (requires prior `fab auth login`).
