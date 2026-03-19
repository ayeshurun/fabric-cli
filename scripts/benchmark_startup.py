#!/usr/bin/env python3
"""
Benchmark: Current Code vs Latest PyPI Release.

Compares the current (local) code against the latest published PyPI version
of ms-fabric-cli, measuring:
  1. CLI startup latency  (fab --version, cold subprocess)
  2. Python module import  (fabric_cli.main, in-process)
  3. HTTP request pipeline  (mocked network round-trip overhead)
  4. Memory footprint       (peak RSS after import)
  5. Heavy-dependency loading (eager vs deferred)
  6. Live API calls          (optional, requires active auth)

Results are printed to stdout as a Markdown report ready for leadership review.

Usage:
    python scripts/benchmark_startup.py                   # default comparison
    python scripts/benchmark_startup.py -n 20             # more iterations
    python scripts/benchmark_startup.py --live             # include live API calls
    python scripts/benchmark_startup.py --output report.md # save report to file
    python scripts/benchmark_startup.py --pypi-version 1.4.0  # pin baseline version
    python scripts/benchmark_startup.py --keep-venvs      # keep temp venvs for debugging
    python scripts/benchmark_startup.py --current-only     # benchmark local code only
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
from datetime import datetime, timezone
from pathlib import Path

PYPI_PACKAGE = "ms-fabric-cli"
DEFAULT_ITERATIONS = 10

# ---------------------------------------------------------------------------
# Runner script – executed inside each isolated venv.
# Outputs a single JSON object to stdout; progress goes to stderr.
# ---------------------------------------------------------------------------
RUNNER_SCRIPT = r'''#!/usr/bin/env python3
"""Benchmark runner executed inside an isolated virtualenv."""
import importlib, io, json, os, platform, resource, shutil, statistics
import subprocess, sys, time
from unittest.mock import MagicMock, patch

HEAVY_MODULES = ["msal", "jwt", "cryptography", "requests", "prompt_toolkit", "psutil"]


def _eprint(*a, **kw):
    print(*a, file=sys.stderr, **kw)


def _stats(times):
    if not times:
        return {"error": "no successful iterations"}
    n = len(times)
    return {
        "median_ms": round(statistics.median(times), 1),
        "mean_ms": round(statistics.mean(times), 1),
        "min_ms": round(min(times), 1),
        "max_ms": round(max(times), 1),
        "stdev_ms": round(statistics.stdev(times), 1) if n > 1 else 0,
        "p95_ms": round(sorted(times)[min(int(n * 0.95), n - 1)], 1) if n >= 5 else round(max(times), 1),
        "iterations": n,
    }


def _clear_fabric_modules():
    for k in [k for k in sys.modules if k.startswith("fabric_cli")]:
        del sys.modules[k]


# --- 1. CLI startup (fab --version) ----------------------------------------
def measure_startup(n):
    fab = shutil.which("fab")
    if not fab:
        return {"error": "fab not on PATH"}
    times = []
    for i in range(n):
        t0 = time.perf_counter()
        subprocess.run([fab, "--version"], capture_output=True, text=True)
        ms = (time.perf_counter() - t0) * 1000
        times.append(ms)
        _eprint(f"    startup {i+1}/{n}: {ms:.0f}ms")
    return _stats(times)


# --- 2. Module import time -------------------------------------------------
def measure_import(n):
    times = []
    for i in range(n):
        _clear_fabric_modules()
        t0 = time.perf_counter()
        importlib.import_module("fabric_cli.main")
        ms = (time.perf_counter() - t0) * 1000
        times.append(ms)
        _eprint(f"    import  {i+1}/{n}: {ms:.0f}ms")
    return _stats(times)


# --- 3. Heavy-module analysis -----------------------------------------------
def check_heavy_modules():
    _clear_fabric_modules()
    for mod in HEAVY_MODULES:
        for k in [k for k in sys.modules if k.startswith(mod)]:
            del sys.modules[k]
    importlib.import_module("fabric_cli.main")
    return {mod: mod in sys.modules for mod in HEAVY_MODULES}


# --- 4. HTTP pipeline overhead (mocked) ------------------------------------
def measure_http_pipeline(n):
    """Import CLI, mock network + auth, run 'ls /', measure overhead."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.ok = True
    mock_resp.headers = {"x-ms-request-id": "bench-0", "Content-Type": "application/json"}
    payload = {"value": [
        {"id": "00000000-0000-0000-0000-000000000001",
         "displayName": "Bench", "type": "Workspace",
         "capacityId": "00000000-0000-0000-0000-000000000099"}
    ]}
    mock_resp.json.return_value = payload
    mock_resp.text = json.dumps(payload)
    mock_resp.content = mock_resp.text.encode()

    times, errors = [], []
    # n+1 runs; first is a warm-up (discarded) to prime module caches
    for i in range(-1, n):
        _clear_fabric_modules()
        try:
            import fabric_cli.main as fab_main

            req_patcher = patch("requests.Session.request", return_value=mock_resp)
            req_patcher.start()

            # Best-effort auth mock (path may differ across versions)
            auth_patcher = None
            for target in [
                "fabric_cli.core.fab_auth.FabAuth.get_access_token",
                "fabric_cli.auth.get_access_token",
            ]:
                try:
                    auth_patcher = patch(target, return_value="mock-bench-token")
                    auth_patcher.start()
                    break
                except Exception:
                    auth_patcher = None

            old_stdout, old_argv = sys.stdout, sys.argv
            sys.stdout = io.StringIO()
            sys.argv = ["fab", "ls", "/"]
            try:
                t0 = time.perf_counter()
                try:
                    fab_main.main()
                except SystemExit:
                    pass
                ms = (time.perf_counter() - t0) * 1000
                if i >= 0:  # skip warm-up (i == -1)
                    times.append(ms)
                    _eprint(f"    http    {i+1}/{n}: {ms:.0f}ms")
                else:
                    _eprint(f"    http    warmup: {ms:.0f}ms (discarded)")
            finally:
                sys.stdout = old_stdout
                sys.argv = old_argv
                req_patcher.stop()
                if auth_patcher:
                    try:
                        auth_patcher.stop()
                    except RuntimeError:
                        pass
        except Exception as exc:
            if i >= 0:
                errors.append(str(exc))
            _eprint(f"    http    {'warmup' if i < 0 else f'{i+1}/{n}'}: ERROR – {exc}")

    if not times:
        return {"error": errors[0] if errors else "unknown failure"}
    result = _stats(times)
    if errors:
        result["partial_errors"] = len(errors)
    return result


# --- 5. Memory footprint ---------------------------------------------------
def measure_memory():
    _clear_fabric_modules()
    importlib.import_module("fabric_cli.main")
    usage = resource.getrusage(resource.RUSAGE_SELF)
    rss = usage.ru_maxrss
    if platform.system() == "Darwin":
        rss_kb = rss / 1024
    else:
        rss_kb = rss  # Linux reports in KB already
    return {"peak_rss_kb": round(rss_kb), "peak_rss_mb": round(rss_kb / 1024, 1)}


# --- 6. Live API call (optional) -------------------------------------------
def measure_live(n, command_args):
    fab = shutil.which("fab")
    if not fab:
        return {"error": "fab not on PATH"}
    times, errors = [], []
    for i in range(n):
        t0 = time.perf_counter()
        proc = subprocess.run([fab] + command_args, capture_output=True, text=True)
        ms = (time.perf_counter() - t0) * 1000
        if proc.returncode == 0:
            times.append(ms)
            _eprint(f"    live    {i+1}/{n}: {ms:.0f}ms")
        else:
            snippet = (proc.stderr or proc.stdout or "")[:120].strip()
            errors.append(snippet)
            _eprint(f"    live    {i+1}/{n}: FAIL – {snippet}")
    if not times:
        return {"error": errors[0] if errors else "command failed"}
    result = _stats(times)
    if errors:
        result["partial_errors"] = len(errors)
    return result


# --- CLI version ------------------------------------------------------------
def get_version():
    try:
        from fabric_cli import __version__
        return __version__
    except Exception:
        return "unknown"


# --- main -------------------------------------------------------------------
def main():
    import argparse as ap
    p = ap.ArgumentParser()
    p.add_argument("--iterations", "-n", type=int, default=10)
    p.add_argument("--live", action="store_true")
    p.add_argument("--skip-http", action="store_true")
    a = p.parse_args()
    n = a.iterations

    ver = get_version()
    _eprint(f"\n  Version : {ver}")
    _eprint(f"  Iters   : {n}")

    results = {"version": ver}

    _eprint("\n  [1/6] CLI startup …")
    results["startup"] = measure_startup(n)

    _eprint("\n  [2/6] Module import …")
    results["import_time"] = measure_import(n)

    _eprint("\n  [3/6] Heavy modules …")
    results["heavy_modules"] = check_heavy_modules()

    if not a.skip_http:
        _eprint("\n  [4/6] HTTP pipeline (mocked) …")
        results["http_pipeline"] = measure_http_pipeline(n)
    else:
        results["http_pipeline"] = {"skipped": True}

    _eprint("\n  [5/6] Memory footprint …")
    results["memory"] = measure_memory()

    if a.live:
        _eprint("\n  [6/6] Live API call (fab ls /) …")
        results["live_api"] = measure_live(n, ["ls", "/"])
    else:
        results["live_api"] = {"skipped": True}

    print(json.dumps(results))


if __name__ == "__main__":
    main()
'''


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _log(msg: str, *, end: str = "\n") -> None:
    sys.stderr.write(msg + end)
    sys.stderr.flush()


def _run(cmd: list[str], *, check: bool = True, quiet: bool = False, **kw) -> subprocess.CompletedProcess:
    kw.setdefault("capture_output", quiet)
    kw.setdefault("text", True)
    return subprocess.run(cmd, check=check, **kw)


def _python_for_venv(venv: Path) -> str:
    if sys.platform == "win32":
        return str(venv / "Scripts" / "python")
    return str(venv / "bin" / "python")


# ---------------------------------------------------------------------------
# Venv lifecycle
# ---------------------------------------------------------------------------

def create_venv(venv_path: Path, label: str) -> None:
    _log(f"\n  Creating venv for {label} at {venv_path.name}/ …")
    _run([sys.executable, "-m", "venv", str(venv_path), "--clear"], quiet=True)


def install_from_pypi(venv: Path, version: str | None = None) -> None:
    pkg = PYPI_PACKAGE if version is None else f"{PYPI_PACKAGE}=={version}"
    _log(f"  Installing {pkg} from PyPI …")
    _run([_python_for_venv(venv), "-m", "pip", "install", "-q", "--upgrade", "pip"], quiet=True)
    _run([_python_for_venv(venv), "-m", "pip", "install", "-q", pkg], quiet=True)


def install_from_source(venv: Path, source_dir: Path) -> None:
    _log(f"  Installing local code from {source_dir.name}/ …")
    _run([_python_for_venv(venv), "-m", "pip", "install", "-q", "--upgrade", "pip"], quiet=True)
    _run([_python_for_venv(venv), "-m", "pip", "install", "-q", str(source_dir)], quiet=True)


# ---------------------------------------------------------------------------
# Run the runner script inside a venv
# ---------------------------------------------------------------------------

def run_benchmarks_in_venv(
    venv: Path, iterations: int, *, live: bool = False, skip_http: bool = False,
) -> dict:
    runner_path = venv / "_bench_runner.py"
    runner_path.write_text(RUNNER_SCRIPT)

    cmd = [_python_for_venv(venv), str(runner_path), "-n", str(iterations)]
    if live:
        cmd.append("--live")
    if skip_http:
        cmd.append("--skip-http")

    proc = subprocess.run(cmd, capture_output=True, text=True)
    # Forward stderr (progress) to our stderr
    if proc.stderr:
        sys.stderr.write(proc.stderr)
        sys.stderr.flush()

    if proc.returncode != 0:
        _log(f"  ⚠  Runner exited with code {proc.returncode}")
        _log(f"     stdout: {proc.stdout[:300]}")
        _log(f"     stderr: {proc.stderr[-300:]}")
        return {"error": f"runner failed (rc={proc.returncode})"}

    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        _log(f"  ⚠  Could not parse runner JSON: {proc.stdout[:200]}")
        return {"error": "invalid JSON from runner"}


# ---------------------------------------------------------------------------
# Markdown report generation
# ---------------------------------------------------------------------------

def _delta(baseline: float, current: float) -> tuple[str, str]:
    """Return (change_str, emoji) for a metric where lower is better."""
    if baseline == 0:
        return "n/a", ""
    diff = current - baseline
    pct = (diff / baseline) * 100
    sign = "+" if diff >= 0 else ""
    emoji = "✅" if pct <= -1 else ("⚠️" if pct <= 5 else "❌")
    return f"{sign}{pct:.1f}%", emoji


def _get(data: dict, *keys, default="–"):
    """Safely drill into nested dicts."""
    d = data
    for k in keys:
        if not isinstance(d, dict):
            return default
        d = d.get(k, default)
    return d


def generate_markdown(
    pypi: dict | None, local: dict, *, iterations: int, live: bool,
) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    machine = f"{platform.system()} {platform.machine()}"
    pyver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    lines: list[str] = []
    w = lines.append

    w("# Fabric CLI – Performance Benchmark Report\n")
    w(f"> **Date:** {now}  ")
    w(f"> **Machine:** {machine}  ")
    w(f"> **Python:** {pyver}  ")
    w(f"> **Iterations per metric:** {iterations}\n")

    pypi_ver = _get(pypi, "version", default="–") if pypi else "–"
    local_ver = _get(local, "version", default="–")

    # ── Summary table ──────────────────────────────────────────────────
    w("## Summary\n")
    if pypi:
        w(f"| Metric | PyPI (`{pypi_ver}`) | Local (`{local_ver}`) | Δ | |")
        w("|--------|---:|---:|---:|---|")

        rows = [
            ("Startup (`fab --version`)", "startup", "median_ms", "ms"),
            ("Module import", "import_time", "median_ms", "ms"),
            ("HTTP pipeline (mocked)", "http_pipeline", "median_ms", "ms"),
            ("Memory (peak RSS)", "memory", "peak_rss_mb", "MB"),
        ]
        for label, section, key, unit in rows:
            pv = _get(pypi, section, key)
            lv = _get(local, section, key)
            if isinstance(pv, (int, float)) and isinstance(lv, (int, float)):
                delta, emoji = _delta(pv, lv)
                w(f"| {label} | {pv} {unit} | {lv} {unit} | {delta} | {emoji} |")
            else:
                w(f"| {label} | {pv} | {lv} | – | |")

        if live:
            pv = _get(pypi, "live_api", "median_ms")
            lv = _get(local, "live_api", "median_ms")
            if isinstance(pv, (int, float)) and isinstance(lv, (int, float)):
                delta, emoji = _delta(pv, lv)
                w(f"| Live API (`fab ls /`) | {pv} ms | {lv} ms | {delta} | {emoji} |")
            else:
                w(f"| Live API (`fab ls /`) | {pv} | {lv} | – | |")
    else:
        # Current-only mode
        w(f"| Metric | Local (`{local_ver}`) |")
        w("|--------|---:|")
        for label, section, key, unit in [
            ("Startup (`fab --version`)", "startup", "median_ms", "ms"),
            ("Module import", "import_time", "median_ms", "ms"),
            ("HTTP pipeline (mocked)", "http_pipeline", "median_ms", "ms"),
            ("Memory (peak RSS)", "memory", "peak_rss_mb", "MB"),
        ]:
            lv = _get(local, section, key)
            w(f"| {label} | {lv} {unit} |")

    # ── Key findings ───────────────────────────────────────────────────
    if pypi:
        w("\n## Key Findings\n")
        findings: list[str] = []
        for label, section, key in [
            ("Startup", "startup", "median_ms"),
            ("Module import", "import_time", "median_ms"),
            ("HTTP pipeline", "http_pipeline", "median_ms"),
            ("Memory footprint", "memory", "peak_rss_mb"),
        ]:
            pv = _get(pypi, section, key)
            lv = _get(local, section, key)
            if isinstance(pv, (int, float)) and isinstance(lv, (int, float)) and pv > 0:
                pct = (lv - pv) / pv * 100
                if pct <= -1:
                    findings.append(f"- ✅ **{label}** improved by **{abs(pct):.0f}%**")
                elif pct >= 5:
                    findings.append(f"- ❌ **{label}** regressed by **{pct:.0f}%**")
                else:
                    findings.append(f"- ➖ **{label}** is within **±{abs(pct):.0f}%** (no significant change)")
        w("\n".join(findings) if findings else "- No significant changes detected.")

    # ── Detailed results ───────────────────────────────────────────────
    w("\n## Detailed Results\n")

    # Startup
    w("### 1. Startup Latency (`fab --version`)\n")
    w("Cold-start wall-clock time for a no-op `fab --version` invocation (subprocess).\n")
    if pypi:
        w(f"| Stat | PyPI | Local |")
        w("|------|---:|---:|")
        for stat in ["median_ms", "mean_ms", "min_ms", "max_ms", "p95_ms", "stdev_ms"]:
            pv = _get(pypi, "startup", stat)
            lv = _get(local, "startup", stat)
            w(f"| {_nice_stat(stat)} | {pv} | {lv} |")
    else:
        _detail_single(w, local, "startup")

    # Import
    w("\n### 2. Module Import Time\n")
    w("Time to `import fabric_cli.main` (in-process, modules cleared between runs).\n")
    if pypi:
        w(f"| Stat | PyPI | Local |")
        w("|------|---:|---:|")
        for stat in ["median_ms", "mean_ms", "min_ms", "max_ms", "p95_ms", "stdev_ms"]:
            pv = _get(pypi, "import_time", stat)
            lv = _get(local, "import_time", stat)
            w(f"| {_nice_stat(stat)} | {pv} | {lv} |")
    else:
        _detail_single(w, local, "import_time")

    # HTTP pipeline
    w("\n### 3. HTTP Request Pipeline\n")
    w("End-to-end command execution with mocked network (`requests.Session.request`).\n"
      "Measures argument parsing → auth token retrieval → URL construction → "
      "header building → request dispatch → response processing.\n")
    if pypi:
        ph = _get(pypi, "http_pipeline")
        lh = _get(local, "http_pipeline")
        if isinstance(ph, dict) and "error" not in ph and isinstance(lh, dict) and "error" not in lh:
            w(f"| Stat | PyPI | Local |")
            w("|------|---:|---:|")
            for stat in ["median_ms", "mean_ms", "min_ms", "max_ms", "p95_ms", "stdev_ms"]:
                w(f"| {_nice_stat(stat)} | {_get(ph, stat)} | {_get(lh, stat)} |")
        else:
            w(f"- **PyPI:** {ph}")
            w(f"- **Local:** {lh}")
    else:
        _detail_single(w, local, "http_pipeline")

    # Memory
    w("\n### 4. Memory Footprint\n")
    w("Peak RSS after importing `fabric_cli.main`.\n")
    if pypi:
        w(f"| | PyPI | Local |")
        w("|--|---:|---:|")
        w(f"| Peak RSS | {_get(pypi, 'memory', 'peak_rss_mb')} MB | {_get(local, 'memory', 'peak_rss_mb')} MB |")
    else:
        w(f"- Peak RSS: **{_get(local, 'memory', 'peak_rss_mb')} MB**")

    # Heavy modules
    w("\n### 5. Heavy Dependency Loading\n")
    w("Modules checked after `import fabric_cli.main`.\n")
    heavy_mods = ["msal", "jwt", "cryptography", "requests", "prompt_toolkit", "psutil"]
    if pypi:
        w("| Module | PyPI | Local |")
        w("|--------|------|------|")
        for mod in heavy_mods:
            pl = "LOADED" if _get(pypi, "heavy_modules", mod) else "deferred"
            ll = "LOADED" if _get(local, "heavy_modules", mod) else "deferred"
            marker = ""
            if ll == "deferred" and pl == "LOADED":
                marker = " ✅"
            elif ll == "LOADED" and pl == "deferred":
                marker = " ❌"
            w(f"| `{mod}` | {pl} | {ll}{marker} |")
    else:
        w("| Module | Status |")
        w("|--------|--------|")
        for mod in heavy_mods:
            ll = "LOADED" if _get(local, "heavy_modules", mod) else "deferred"
            w(f"| `{mod}` | {ll} |")

    # Live API
    if live:
        w("\n### 6. Live API Call (`fab ls /`)\n")
        w("End-to-end wall-clock time for listing workspaces against the live Fabric API.\n")
        if pypi:
            pl = _get(pypi, "live_api")
            ll = _get(local, "live_api")
            if isinstance(pl, dict) and "error" not in pl and isinstance(ll, dict) and "error" not in ll:
                w(f"| Stat | PyPI | Local |")
                w("|------|---:|---:|")
                for stat in ["median_ms", "mean_ms", "min_ms", "max_ms", "p95_ms"]:
                    w(f"| {_nice_stat(stat)} | {_get(pl, stat)} | {_get(ll, stat)} |")
            else:
                w(f"- **PyPI:** {pl}")
                w(f"- **Local:** {ll}")
        else:
            _detail_single(w, local, "live_api")

    # ── Methodology ────────────────────────────────────────────────────
    w("\n## Methodology\n")
    w("- Each version is installed into its own isolated virtualenv to prevent cross-contamination.")
    w(f"- Every timing metric is run **{iterations}** iterations; we report median, mean, p95, min, max, and σ.")
    w("- **Startup** is measured via a cold subprocess (`fab --version`).")
    w("- **Import** clears `sys.modules` between runs for a clean slate.")
    w("- **HTTP pipeline** patches `requests.Session.request` and auth to isolate CLI overhead from network latency. One warm-up iteration is discarded.")
    w("- **Memory** uses `resource.getrusage(RUSAGE_SELF).ru_maxrss`.")
    if live:
        w("- **Live API** calls the real Fabric API endpoint (requires prior `fab auth login`).")
    w("")

    return "\n".join(lines)


def _nice_stat(stat: str) -> str:
    """Convert stat key like 'median_ms' to 'Median (ms)'."""
    name = stat.replace("_ms", "").replace("_", " ")
    return name[0].upper() + name[1:] + " (ms)"


def _detail_single(w, data: dict, section: str) -> None:
    """Write a single-column detail table (current-only mode)."""
    d = _get(data, section)
    if isinstance(d, dict) and "error" not in d:
        w("| Stat | Value |")
        w("|------|------:|")
        for stat in ["median_ms", "mean_ms", "min_ms", "max_ms", "p95_ms", "stdev_ms"]:
            w(f"| {_nice_stat(stat)} | {_get(d, stat)} |")
    else:
        w(f"- Result: {d}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark current Fabric CLI code against the latest PyPI release.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
        examples:
          python scripts/benchmark_startup.py
          python scripts/benchmark_startup.py -n 20 --output report.md
          python scripts/benchmark_startup.py --live
          python scripts/benchmark_startup.py --pypi-version 1.4.0
        """),
    )
    parser.add_argument(
        "--iterations", "-n", type=int, default=DEFAULT_ITERATIONS,
        help=f"Iterations per metric (default: {DEFAULT_ITERATIONS})",
    )
    parser.add_argument(
        "--pypi-version", default=None,
        help="Pin the PyPI baseline to a specific version (default: latest)",
    )
    parser.add_argument(
        "--live", action="store_true",
        help="Include live API calls (requires active 'fab auth login')",
    )
    parser.add_argument(
        "--output", "-o", default=None, metavar="FILE",
        help="Write Markdown report to FILE instead of stdout",
    )
    parser.add_argument(
        "--current-only", action="store_true",
        help="Only benchmark the local code (skip PyPI comparison)",
    )
    parser.add_argument(
        "--keep-venvs", action="store_true",
        help="Do not delete temporary venvs after benchmarking",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Also dump raw results as JSON (to stderr)",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    os.chdir(repo_root)

    _log(f"\n{'=' * 60}")
    _log(f"  Fabric CLI Performance Benchmark")
    _log(f"{'=' * 60}")
    _log(f"  Repo        : {repo_root}")
    _log(f"  Iterations  : {args.iterations}")
    _log(f"  Live calls  : {'yes' if args.live else 'no'}")

    venv_dir = repo_root / ".bench_venvs"
    venv_dir.mkdir(exist_ok=True)
    venv_pypi = venv_dir / "pypi"
    venv_local = venv_dir / "local"

    pypi_results = None
    local_results = None

    try:
        # ── PyPI baseline ──────────────────────────────────────────────
        if not args.current_only:
            create_venv(venv_pypi, f"PyPI ({PYPI_PACKAGE})")
            install_from_pypi(venv_pypi, version=args.pypi_version)
            _log(f"\n  Running benchmarks for PyPI version …")
            pypi_results = run_benchmarks_in_venv(
                venv_pypi, args.iterations, live=args.live,
            )

        # ── Local code ─────────────────────────────────────────────────
        create_venv(venv_local, "local code")
        install_from_source(venv_local, repo_root)
        _log(f"\n  Running benchmarks for local code …")
        local_results = run_benchmarks_in_venv(
            venv_local, args.iterations, live=args.live,
        )

        # ── Report ─────────────────────────────────────────────────────
        if local_results and "error" not in local_results:
            report = generate_markdown(
                pypi_results, local_results,
                iterations=args.iterations, live=args.live,
            )
            if args.output:
                Path(args.output).write_text(report, encoding="utf-8")
                _log(f"\n  ✅ Report written to {args.output}")
            else:
                print(report)

            if args.json:
                _log("\n--- Raw JSON ---")
                _log(json.dumps({"pypi": pypi_results, "local": local_results}, indent=2))
        else:
            _log(f"\n  ❌ Local benchmark failed: {local_results}")
            sys.exit(1)

    finally:
        if not args.keep_venvs and venv_dir.exists():
            _log(f"\n  Cleaning up {venv_dir}/ …")
            shutil.rmtree(venv_dir, ignore_errors=True)
        elif args.keep_venvs:
            _log(f"\n  Keeping venvs at {venv_dir}/")

    _log(f"\n{'=' * 60}")
    _log(f"  Done.")
    _log(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
