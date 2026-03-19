# Fabric CLI – Performance Benchmark Report

> **Date:** 2026-03-19 15:43 UTC  
> **Machine:** Linux aarch64  
> **Python:** 3.12.11  
> **Iterations per metric:** 20

## Summary

| Metric | PyPI (`1.4.0`) | Local (`1.5.0`) | Δ | |
|--------|---:|---:|---:|---|
| Startup (`fab --version`) | 152.2 ms | 153.0 ms | +0.5% | ⚠️ |
| Module import | 60.8 ms | 11.9 ms | -80.4% | ✅ |
| HTTP pipeline (mocked) | 14.0 ms | 48.6 ms | +247.1% | ❌ |
| Memory (peak RSS) | 82.9 MB | 78.3 MB | -5.5% | ✅ |
| Live API (`fab ls /`) | 1366.3 ms | 1352.5 ms | -1.0% | ✅ |

## Key Findings

- ➖ **Startup** is within **±1%** (no significant change)
- ✅ **Module import** improved by **80%**
- ❌ **HTTP pipeline** regressed by **247%**
- ✅ **Memory footprint** improved by **6%**

## Detailed Results

### 1. Startup Latency (`fab --version`)

Cold-start wall-clock time for a no-op `fab --version` invocation (subprocess).

| Stat | PyPI | Local |
|------|---:|---:|
| Median (ms) | 152.2 | 153.0 |
| Mean (ms) | 163.8 | 154.7 |
| Min (ms) | 150.3 | 149.7 |
| Max (ms) | 381.3 | 170.5 |
| P95 (ms) | 381.3 | 170.5 |
| Stdev (ms) | 51.2 | 5.5 |

### 2. Module Import Time

Time to `import fabric_cli.main` (in-process, modules cleared between runs).

| Stat | PyPI | Local |
|------|---:|---:|
| Median (ms) | 60.8 | 11.9 |
| Mean (ms) | 150.3 | 18.4 |
| Min (ms) | 55.9 | 11.4 |
| Max (ms) | 1788.0 | 137.6 |
| P95 (ms) | 1788.0 | 137.6 |
| Stdev (ms) | 385.7 | 28.1 |

### 3. HTTP Request Pipeline

End-to-end command execution with mocked network (`requests.Session.request`).
Measures argument parsing → auth token retrieval → URL construction → header building → request dispatch → response processing.

| Stat | PyPI | Local |
|------|---:|---:|
| Median (ms) | 14.0 | 48.6 |
| Mean (ms) | 15.7 | 53.1 |
| Min (ms) | 13.4 | 47.0 |
| Max (ms) | 46.6 | 80.1 |
| P95 (ms) | 46.6 | 80.1 |
| Stdev (ms) | 7.3 | 10.4 |

### 4. Memory Footprint

Peak RSS after importing `fabric_cli.main`.

| | PyPI | Local |
|--|---:|---:|
| Peak RSS | 82.9 MB | 78.3 MB |

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
| Median (ms) | 1366.3 | 1352.5 |
| Mean (ms) | 1323.5 | 1280.9 |
| Min (ms) | 1015.1 | 998.0 |
| Max (ms) | 1771.2 | 1640.4 |
| P95 (ms) | 1771.2 | 1640.4 |

## Methodology

- Each version is installed into its own isolated virtualenv to prevent cross-contamination.
- Every timing metric is run **20** iterations; we report median, mean, p95, min, max, and σ.
- **Startup** is measured via a cold subprocess (`fab --version`).
- **Import** clears `sys.modules` between runs for a clean slate.
- **HTTP pipeline** patches `requests.Session.request` and auth to isolate CLI overhead from network latency. One warm-up iteration is discarded.
- **Memory** uses `resource.getrusage(RUSAGE_SELF).ru_maxrss`.
- **Live API** calls the real Fabric API endpoint (requires prior `fab auth login`).
