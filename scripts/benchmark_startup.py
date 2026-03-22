#!/usr/bin/env python3
"""
Benchmark CLI startup performance.

Compares the current branch against 'main' (or any other branch) by measuring:
  1. Module import time (fabric_cli.main)
  2. CLI invocation time (fab --version)
  3. Heavy dependency loading (msal, jwt, cryptography, requests, prompt_toolkit)

Usage:
    # Compare current branch against main
    python scripts/benchmark_startup.py

    # Compare current branch against a specific branch/tag/commit
    python scripts/benchmark_startup.py --baseline v1.3.0

    # Run only on the current branch (no git checkout)
    python scripts/benchmark_startup.py --current-only

    # Change number of iterations (default: 10)
    python scripts/benchmark_startup.py --iterations 20
"""

import argparse
import importlib
import json
import os
import shutil
import statistics
import subprocess
import sys
import time


HEAVY_MODULES = ["msal", "jwt", "cryptography", "requests", "prompt_toolkit", "psutil"]


def measure_import_time(iterations: int) -> dict:
    """Measure fabric_cli.main import time across multiple iterations."""
    times = []
    for _ in range(iterations):
        # Clear all fabric_cli modules from cache
        mods = [k for k in sys.modules if k.startswith("fabric_cli")]
        for m in mods:
            del sys.modules[m]

        start = time.perf_counter()
        importlib.import_module("fabric_cli.main")
        elapsed_ms = (time.perf_counter() - start) * 1000
        times.append(elapsed_ms)

    return {
        "median_ms": round(statistics.median(times), 1),
        "min_ms": round(min(times), 1),
        "max_ms": round(max(times), 1),
        "mean_ms": round(statistics.mean(times), 1),
        "stdev_ms": round(statistics.stdev(times), 1) if len(times) > 1 else 0,
        "samples": times,
    }


def check_heavy_modules() -> dict:
    """Check which heavy modules are loaded after importing fabric_cli.main."""
    # Clear all fabric_cli modules
    mods = [k for k in sys.modules if k.startswith("fabric_cli")]
    for m in mods:
        del sys.modules[m]

    # Also clear heavy modules
    for mod in HEAVY_MODULES:
        keys = [k for k in sys.modules if k.startswith(mod)]
        for k in keys:
            del sys.modules[k]

    importlib.import_module("fabric_cli.main")

    return {mod: mod in sys.modules for mod in HEAVY_MODULES}


def measure_cli_time(iterations: int) -> dict:
    """Measure 'fab --version' wall-clock time."""
    fab_path = shutil.which("fab")
    if not fab_path:
        return {"error": "'fab' not found in PATH. Run 'pip install -e .' first."}

    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        subprocess.run(
            [fab_path, "--version"],
            capture_output=True,
            text=True,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000
        times.append(elapsed_ms)

    return {
        "median_ms": round(statistics.median(times), 1),
        "min_ms": round(min(times), 1),
        "max_ms": round(max(times), 1),
        "mean_ms": round(statistics.mean(times), 1),
        "stdev_ms": round(statistics.stdev(times), 1) if len(times) > 1 else 0,
    }


def run_benchmark(label: str, iterations: int) -> dict:
    """Run all benchmarks and return results."""
    print(f"\n{'=' * 60}")
    print(f"  Benchmarking: {label}")
    print(f"{'=' * 60}")

    # 1. Import time
    print(f"  Measuring import time ({iterations} iterations)...", end="", flush=True)
    import_results = measure_import_time(iterations)
    print(f" {import_results['median_ms']:.0f}ms median")

    # 2. Heavy modules
    print("  Checking heavy module loading...", end="", flush=True)
    heavy_results = check_heavy_modules()
    loaded = [m for m, v in heavy_results.items() if v]
    print(f" {len(loaded)} loaded: {', '.join(loaded) if loaded else 'none'}")

    # 3. CLI time
    print(f"  Measuring 'fab --version' ({iterations} iterations)...", end="", flush=True)
    cli_results = measure_cli_time(iterations)
    if "error" in cli_results:
        print(f" {cli_results['error']}")
    else:
        print(f" {cli_results['median_ms']:.0f}ms median")

    return {
        "label": label,
        "import_time": import_results,
        "heavy_modules": heavy_results,
        "cli_time": cli_results,
    }


def print_comparison(baseline: dict, current: dict):
    """Print a formatted comparison table."""
    print(f"\n{'=' * 60}")
    print("  COMPARISON")
    print(f"{'=' * 60}\n")

    bl = baseline["import_time"]["median_ms"]
    cu = current["import_time"]["median_ms"]
    diff = bl - cu
    pct = (diff / bl * 100) if bl > 0 else 0

    print(f"  {'Metric':<30} {'Baseline':>10} {'Current':>10} {'Change':>10}")
    print(f"  {'-' * 62}")
    print(f"  {'Import time (median):':<30} {bl:>9.0f}ms {cu:>9.0f}ms {diff:>+8.0f}ms")
    print(f"  {'Import improvement:':<30} {'':>10} {'':>10} {pct:>+8.0f}%")

    if "error" not in baseline["cli_time"] and "error" not in current["cli_time"]:
        bl_cli = baseline["cli_time"]["median_ms"]
        cu_cli = current["cli_time"]["median_ms"]
        cli_diff = bl_cli - cu_cli
        cli_pct = (cli_diff / bl_cli * 100) if bl_cli > 0 else 0
        print(f"  {'CLI time (median):':<30} {bl_cli:>9.0f}ms {cu_cli:>9.0f}ms {cli_diff:>+8.0f}ms")
        print(f"  {'CLI improvement:':<30} {'':>10} {'':>10} {cli_pct:>+8.0f}%")

    print(f"\n  {'Heavy modules at startup:':<30}")
    for mod in HEAVY_MODULES:
        bl_loaded = "LOADED" if baseline["heavy_modules"].get(mod) else "deferred"
        cu_loaded = "LOADED" if current["heavy_modules"].get(mod) else "deferred"
        marker = " ✓" if cu_loaded == "deferred" and bl_loaded == "LOADED" else ""
        print(f"    {mod:<25} {bl_loaded:>10} {cu_loaded:>10}{marker}")

    print()


def git_checkout_and_install(ref: str):
    """Checkout a git ref and reinstall the package."""
    print(f"\n  Switching to '{ref}'...")
    subprocess.run(["git", "checkout", ref], capture_output=True, check=True)
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-e", ".", "-q"],
        capture_output=True,
        check=True,
    )
    # Clear all cached fabric_cli modules after reinstall
    mods = [k for k in sys.modules if k.startswith("fabric_cli")]
    for m in mods:
        del sys.modules[m]


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark CLI startup performance between branches."
    )
    parser.add_argument(
        "--baseline",
        default="main",
        help="Git ref to compare against (default: main)",
    )
    parser.add_argument(
        "--iterations", "-n",
        type=int,
        default=10,
        help="Number of iterations per measurement (default: 10)",
    )
    parser.add_argument(
        "--current-only",
        action="store_true",
        help="Only benchmark the current branch (skip baseline)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    args = parser.parse_args()

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(repo_root)

    # Get current branch name
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True, text=True,
    )
    current_branch = result.stdout.strip()

    print(f"  Repo: {repo_root}")
    print(f"  Current branch: {current_branch}")
    print(f"  Baseline: {args.baseline}")
    print(f"  Iterations: {args.iterations}")

    results = {}

    if not args.current_only:
        # Benchmark baseline
        try:
            git_checkout_and_install(args.baseline)
            results["baseline"] = run_benchmark(f"Baseline ({args.baseline})", args.iterations)
        except subprocess.CalledProcessError:
            print(f"\n  ERROR: Could not checkout '{args.baseline}'. Does it exist?")
            print(f"  Try: python scripts/benchmark_startup.py --current-only")
            sys.exit(1)
        finally:
            # Always return to original branch
            subprocess.run(["git", "checkout", current_branch], capture_output=True)
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-e", ".", "-q"],
                capture_output=True,
            )
            # Clear modules again
            mods = [k for k in sys.modules if k.startswith("fabric_cli")]
            for m in mods:
                del sys.modules[m]

    # Benchmark current
    results["current"] = run_benchmark(f"Current ({current_branch})", args.iterations)

    # Print comparison
    if "baseline" in results:
        print_comparison(results["baseline"], results["current"])

    # JSON output
    if args.json:
        # Remove raw samples for cleaner JSON
        for key in results:
            if "samples" in results[key].get("import_time", {}):
                del results[key]["import_time"]["samples"]
        print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
