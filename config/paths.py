"""Application path constants and directory management."""
from __future__ import annotations

import sys
from pathlib import Path


def _get_app_dir() -> Path:
    """Return the base directory for user data.

    When frozen (PyInstaller), use the folder containing the executable.
    During development, use the project root (parent of config/).
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    # Development: two levels up from this file (config/ -> project root)
    return Path(__file__).resolve().parent.parent


APP_DIR: Path = _get_app_dir()
DATA_DIR: Path = APP_DIR / "data"
DATABASE_DIR: Path = DATA_DIR / "database"
IMPORTS_DIR: Path = DATA_DIR / "imports"
EXPORTS_DIR: Path = DATA_DIR / "exports"
BACKUPS_DIR: Path = DATA_DIR / "backups"
LOGS_DIR: Path = DATA_DIR / "logs"

DB_PATH: Path = DATABASE_DIR / "quiz_app.db"


def ensure_data_dirs() -> None:
    """Create all required data directories if they do not exist."""
    for directory in (DATABASE_DIR, IMPORTS_DIR, EXPORTS_DIR, BACKUPS_DIR, LOGS_DIR):
        directory.mkdir(parents=True, exist_ok=True)
