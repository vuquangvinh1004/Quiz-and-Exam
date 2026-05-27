"""Fail CI when full Ruff error count regresses above a stored baseline.

This lets the repo keep a strict high-signal lint gate while gradually paying
style/modernization debt without allowing it to grow.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--baseline-file",
        type=Path,
        default=Path("scripts/ruff_baseline.txt"),
        help="Path containing the maximum allowed Ruff error count.",
    )
    parser.add_argument(
        "--target",
        default=".",
        help="Path to lint with Ruff (default: current repository).",
    )
    return parser.parse_args()


def run_ruff_statistics(target: str) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, "-m", "ruff", "check", target, "--statistics"],
        capture_output=True,
        text=True,
        check=False,
    )
    output = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")

    match = re.search(r"Found\s+(\d+)\s+errors\.", output)
    if not match:
        print("Unable to parse Ruff error count from output:")
        print(output)
        return 2, output

    return int(match.group(1)), output


def main() -> int:
    args = parse_args()

    if not args.baseline_file.exists():
        print(f"Baseline file not found: {args.baseline_file}")
        return 2

    try:
        baseline = int(args.baseline_file.read_text(encoding="utf-8").strip())
    except ValueError:
        print(f"Baseline file must contain a single integer: {args.baseline_file}")
        return 2

    count, output = run_ruff_statistics(args.target)
    if count == 2:
        return 2

    print(f"Ruff full-check count: {count}")
    print(f"Allowed baseline   : {baseline}")

    if count > baseline:
        print("\nRuff debt regressed above baseline. Failing check.")
        print("\n--- Ruff statistics output ---")
        print(output)
        return 1

    print("\nRuff debt did not regress.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
