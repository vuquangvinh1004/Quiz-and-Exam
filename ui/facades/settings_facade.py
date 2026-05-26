"""Facade for settings-related workflows used by SettingsView."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core.database.session import get_session
from core.domain.services.settings_service import SettingsService
from core.domain.services.submission_service import SubmissionService
from modules.backup.backup_manager import BackupManager


@dataclass
class SubmissionStatus:
    """Lightweight submission status summary for UI display."""

    mode: str
    default_email: str | None
    submit_folder: str | None


class SettingsFacade:
    """Centralize DB/session orchestration for settings UI."""

    def get_theme(self) -> str:
        with get_session() as session:
            return SettingsService.get_theme(session)

    def set_theme(self, theme: str) -> None:
        with get_session() as session:
            SettingsService.set_theme(session, theme)

    def get_submission_status(self) -> SubmissionStatus:
        with get_session() as session:
            cfg = SubmissionService().load_settings(session)
        return SubmissionStatus(
            mode=cfg.mode,
            default_email=cfg.default_email,
            submit_folder=cfg.submit_folder,
        )

    def create_backup(self, db_path: Path, backups_dir: Path) -> Path:
        return BackupManager.create_backup(db_path, backups_dir)

    def restore_backup(self, db_path: Path, backup_file: Path) -> None:
        BackupManager.restore_from_backup(db_path, backup_file)
