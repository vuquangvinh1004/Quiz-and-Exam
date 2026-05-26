"""Facade for submission settings persistence and SMTP smoke checks."""
from __future__ import annotations

import smtplib

from core.database.session import get_session
from core.domain.services.submission_service import SubmissionService, SubmissionSettings


class SubmissionSettingsFacade:
    """Centralize submission-settings workflow for UI dialogs."""

    def __init__(self) -> None:
        self._service = SubmissionService()

    def load_settings(self) -> SubmissionSettings:
        with get_session() as session:
            return self._service.load_settings(session)

    def save_settings(self, cfg: SubmissionSettings) -> None:
        with get_session() as session:
            self._service.save_settings(session, cfg)

    @staticmethod
    def test_smtp_connection(
        *,
        server: str,
        port: int,
        user: str,
        password: str,
        use_tls: bool,
    ) -> None:
        """Raise on SMTP connectivity/auth failures; returns None on success."""
        with smtplib.SMTP(server, port, timeout=10) as smtp:
            smtp.ehlo()
            if use_tls:
                smtp.starttls()
                smtp.ehlo()
            if user:
                smtp.login(user, password)
