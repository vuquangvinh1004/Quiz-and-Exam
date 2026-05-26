"""Unit tests for modules/backup/backup_manager.py (Phase 6).

Uses pytest's ``tmp_path`` fixture to avoid touching real files.

Tests:
  - create_backup: creates file, timestamp in name, raises on missing db
  - list_backups:  empty dir, sorted newest-first, filters by pattern
  - restore_from_backup: copies file to db_path, raises on missing backup
"""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from modules.backup.backup_manager import BackupManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_fake_db(tmp_path: Path, name: str = "quiz_app.db", content: bytes = b"DB") -> Path:
    p = tmp_path / name
    p.write_bytes(content)
    return p


# ---------------------------------------------------------------------------
# TestCreateBackup
# ---------------------------------------------------------------------------

class TestCreateBackup:

    def test_creates_file_in_backup_dir(self, tmp_path):
        db = _make_fake_db(tmp_path)
        backup_dir = tmp_path / "backups"
        dest = BackupManager.create_backup(db, backup_dir)
        assert dest.exists()

    def test_backup_file_is_in_backup_dir(self, tmp_path):
        db = _make_fake_db(tmp_path)
        backup_dir = tmp_path / "backups"
        dest = BackupManager.create_backup(db, backup_dir)
        assert dest.parent == backup_dir

    def test_backup_filename_contains_timestamp(self, tmp_path):
        db = _make_fake_db(tmp_path)
        backup_dir = tmp_path / "backups"
        dest = BackupManager.create_backup(db, backup_dir)
        # Name pattern: quiz_app_YYYY-MM-DD_HH-MM-SS.db
        assert dest.name.startswith("quiz_app_")
        assert dest.suffix == ".db"

    def test_backup_content_same_as_source(self, tmp_path):
        content = b"SQLITE_DB_CONTENT"
        db = _make_fake_db(tmp_path, content=content)
        backup_dir = tmp_path / "backups"
        dest = BackupManager.create_backup(db, backup_dir)
        assert dest.read_bytes() == content

    def test_raises_if_db_not_found(self, tmp_path):
        missing = tmp_path / "missing.db"
        backup_dir = tmp_path / "backups"
        with pytest.raises(FileNotFoundError):
            BackupManager.create_backup(missing, backup_dir)

    def test_creates_backup_dir_if_not_exists(self, tmp_path):
        db = _make_fake_db(tmp_path)
        backup_dir = tmp_path / "nested" / "backups"
        assert not backup_dir.exists()
        BackupManager.create_backup(db, backup_dir)
        assert backup_dir.exists()


# ---------------------------------------------------------------------------
# TestListBackups
# ---------------------------------------------------------------------------

class TestListBackups:

    def test_empty_dir_returns_empty_list(self, tmp_path):
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()
        result = BackupManager.list_backups(backup_dir)
        assert result == []

    def test_nonexistent_dir_returns_empty_list(self, tmp_path):
        missing_dir = tmp_path / "no_such_dir"
        assert BackupManager.list_backups(missing_dir) == []

    def test_returns_backup_files(self, tmp_path):
        db = _make_fake_db(tmp_path)
        backup_dir = tmp_path / "backups"
        BackupManager.create_backup(db, backup_dir)
        result = BackupManager.list_backups(backup_dir)
        assert len(result) == 1

    def test_ignores_non_backup_files(self, tmp_path):
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()
        (backup_dir / "README.txt").write_text("ignore me")
        (backup_dir / "other.db").write_bytes(b"not a backup")
        result = BackupManager.list_backups(backup_dir)
        assert result == []

    def test_sorted_newest_first(self, tmp_path):
        db = _make_fake_db(tmp_path)
        backup_dir = tmp_path / "backups"
        b1 = BackupManager.create_backup(db, backup_dir)
        time.sleep(1.1)  # ensure different timestamp
        b2 = BackupManager.create_backup(db, backup_dir)
        result = BackupManager.list_backups(backup_dir)
        # b2 is newer → should appear first
        assert result[0] == b2


# ---------------------------------------------------------------------------
# TestRestoreFromBackup
# ---------------------------------------------------------------------------

class TestRestoreFromBackup:

    def test_copies_backup_to_db_path(self, tmp_path):
        db = _make_fake_db(tmp_path, name="quiz_app.db", content=b"ORIGINAL")
        backup_dir = tmp_path / "backups"
        backup = BackupManager.create_backup(db, backup_dir)
        # Overwrite db with different content
        db.write_bytes(b"MODIFIED")
        # Restore
        BackupManager.restore_from_backup(db, backup)
        assert db.read_bytes() == b"ORIGINAL"

    def test_raises_if_backup_not_found(self, tmp_path):
        db = _make_fake_db(tmp_path)
        missing_backup = tmp_path / "no_backup.db"
        with pytest.raises(FileNotFoundError):
            BackupManager.restore_from_backup(db, missing_backup)

    def test_creates_db_parent_dir_if_missing(self, tmp_path):
        backup = tmp_path / "backup.db"
        backup.write_bytes(b"DATA")
        db_path = tmp_path / "nested" / "db" / "quiz_app.db"
        assert not db_path.parent.exists()
        BackupManager.restore_from_backup(db_path, backup)
        assert db_path.exists()
        assert db_path.read_bytes() == b"DATA"
