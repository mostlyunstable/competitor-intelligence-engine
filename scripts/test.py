#!/usr/bin/env python3
"""
Test runner script.

Runs pytest, ruff, black, and mypy in sequence.
"""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


def run_step(name: str, cmd: list[str]) -> bool:
    print(f"\n{'=' * 60}")
    print(f"  Running: {name}")
    print(f"  Command: {' '.join(cmd)}")
    print(f"{'=' * 60}")

    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        print(f"\n  FAILED: {name} (exit code {result.returncode})")
        return False
    print(f"\n  PASSED: {name}")
    return True


def main() -> int:
    print("\n" + "=" * 60)
    print("  Utservio Competitor Intelligence - Test Suite")
    print("=" * 60)

    steps = [
        ("Ruff Linter", [sys.executable, "-m", "ruff", "check", "."]),
        ("Ruff Formatter", [sys.executable, "-m", "ruff", "format", "--check", "."]),
        ("MyPy Type Checker", [sys.executable, "-m", "mypy", "app/"]),
        ("Pytest", [sys.executable, "-m", "pytest", "tests/unit/", "-v"]),
    ]

    results = {}
    for name, cmd in steps:
        results[name] = run_step(name, cmd)

    print("\n" + "=" * 60)
    print("  Summary")
    print("=" * 60)

    all_passed = True
    for name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n  All checks passed!")
        return 0
    else:
        print("\n  Some checks failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
