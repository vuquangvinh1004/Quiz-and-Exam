"""Local backup and restore for the SQLite database.

Business rules (ARCHITECTURE §5.6):
  - Backup: copy DB to timestamped file in the backups directory.
  - Restore: overwrite DB with a selected backup file.
  - Restore MUST be confirmed by the user before this module is called.
    No confirmation dialogs are shown here; that is the UI layer's
    responsibility.

Usage::

    from modules.backup.backup_manager import BackupManager
    from config.paths import DB_PATH, BACKUPS_DIR

    # Create backup
    dest = BackupManager.create_backup(DB_PATH, BACKUPS_DIR)
    print(f"Backup saved to: {dest}")

    # Restore (after user confirmation in UI)
    BackupManager.restore_from_backup(DB_PATH, backup_file)
"""
from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path


class BackupManager:
    """Creates and manages timestamped local backups of the SQLite database."""

    # Filename prefix used so list_backups() can filter correctly.
    _FILE_PREFIX = "quiz_app_"
    _FILE_SUFFIX = ".db"

    @staticmethod
    def create_backup(db_path: Path, backup_dir: Path) -> Path:
        """Copy *db_path* to *backup_dir* with a timestamp in the filename.

        Parameters
        ----------
        db_path:
            Absolute path to the live SQLite database file.
        backup_dir:
            Directory where the backup file will be written.
            Created automatically if it does not exist.

        Returns
        -------
        Path
            Absolute path of the newly created backup file.

        Raises
        ------
        FileNotFoundError
            If *db_path* does not exist.
        """
        if not db_path.exists():
            raise FileNotFoundError(f"Database file not found: {db_path}")
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        dest_name = f"{BackupManager._FILE_PREFIX}{timestamp}{BackupManager._FILE_SUFFIX}"
        dest = backup_dir / dest_name
        shutil.copy2(db_path, dest)
        return dest

    @staticmethod
    def list_backups(backup_dir: Path) -> list[Path]:
        """Return backup files in *backup_dir*, sorted newest first.

        Only files matching the standard naming pattern
        ``quiz_app_*.db`` are returned.
        """
        if not backup_dir.exists():
            return []
        pattern = f"{BackupManager._FILE_PREFIX}*{BackupManager._FILE_SUFFIX}"
        return sorted(backup_dir.glob(pattern), reverse=True)

    @staticmethod
    def restore_from_backup(db_path: Path, backup_file: Path) -> None:
        """Overwrite *db_path* with *backup_file*.

        The caller is responsible for:
        1. Closing or disposing all existing database connections/engines
           before calling this method.
        2. Confirming the destructive operation with the user.
        3. Informing the user to restart the application afterwards.

        Raises
        ------
        FileNotFoundError
            If *backup_file* does not exist.
        """
        if not backup_file.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_file}")
        db_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(backup_file, db_path)
