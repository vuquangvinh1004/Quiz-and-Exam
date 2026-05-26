"""Fail when staged/tracked files include sensitive data artifacts.

Used by pre-commit and CI to prevent leaking local user data/secrets.
"""
from __future__ import annotations

import argparse
import fnmatch
import subprocess
import sys
from pathlib import Path

FORBIDDEN_PATH_PATTERNS = [
    "data/**",
    "**/data/**",
    "**/backups/**",
    "**/logs/**",
]

FORBIDDEN_FILE_PATTERNS = [
    "*.db",
    "*.db3",
    "*.sqlite",
    "*.sqlite3",
    "*.bak",
    "*.tmp",
    "*.log",
    "*.key",
    "*.pem",
    "*.p12",
    "*.pfx",
    ".env",
    ".env.*",
    "secrets.json",
    "credentials.json",
]

ALLOWED_EXACT = {
    ".env.example",
}


def _normalize(path: str) -> str:
    return path.strip().replace("\\", "/")


def _matches(path: str, pattern: str) -> bool:
    return fnmatch.fnmatch(path, pattern)


def _is_forbidden(path: str) -> bool:
    if path in ALLOWED_EXACT:
        return False

    for pattern in FORBIDDEN_PATH_PATTERNS:
        if _matches(path, pattern):
            return True

    name = Path(path).name
    for pattern in FORBIDDEN_FILE_PATTERNS:
        if _matches(name, pattern) or _matches(path, pattern):
            return True

    return False


def _tracked_files() -> list[str]:
    proc = subprocess.run(
        ["git", "ls-files"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return []
    return [_normalize(line) for line in proc.stdout.splitlines() if line.strip()]


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tracked-only", action="store_true")
    parser.add_argument("files", nargs="*")
    args = parser.parse_args(argv)

    files = [_normalize(p) for p in args.files if p.strip()]
    if args.tracked_only:
        files = _tracked_files()

    offenders = [p for p in files if _is_forbidden(p)]
    if offenders:
        print("ERROR: Sensitive or local-data files detected. Remove from commit:")
        for item in offenders:
            print(f" - {item}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
