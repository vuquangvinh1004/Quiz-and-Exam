"""Unit tests for config/paths.py"""
from __future__ import annotations

import pytest
from pathlib import Path

from config.paths import (
    APP_DIR,
    BACKUPS_DIR,
    DATABASE_DIR,
    DB_PATH,
    EXPORTS_DIR,
    IMPORTS_DIR,
    LOGS_DIR,
    ensure_data_dirs,
)


class TestPaths:
    def test_app_dir_is_absolute(self):
        assert APP_DIR.is_absolute()

    def test_db_path_ends_with_db(self):
        assert DB_PATH.suffix == ".db"

    def test_db_path_inside_database_dir(self):
        assert DB_PATH.parent == DATABASE_DIR

    def test_all_data_dirs_under_data(self):
        for d in (DATABASE_DIR, IMPORTS_DIR, EXPORTS_DIR, BACKUPS_DIR, LOGS_DIR):
            assert "data" in str(d)


class TestEnsureDataDirs:
    def test_creates_directories(self, tmp_path, monkeypatch):
        """ensure_data_dirs must create all required directories."""
        import config.paths as paths_module

        # Redirect all paths to tmp_path sub-dirs
        new_data = tmp_path / "data"
        monkeypatch.setattr(paths_module, "DATABASE_DIR", new_data / "database")
        monkeypatch.setattr(paths_module, "IMPORTS_DIR", new_data / "imports")
        monkeypatch.setattr(paths_module, "EXPORTS_DIR", new_data / "exports")
        monkeypatch.setattr(paths_module, "BACKUPS_DIR", new_data / "backups")
        monkeypatch.setattr(paths_module, "LOGS_DIR", new_data / "logs")

        paths_module.ensure_data_dirs()

        for d in (
            new_data / "database",
            new_data / "imports",
            new_data / "exports",
            new_data / "backups",
            new_data / "logs",
        ):
            assert d.is_dir(), f"Directory not created: {d}"
