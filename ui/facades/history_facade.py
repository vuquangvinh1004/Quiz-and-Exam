"""Facade for result-history workflows used by history UI."""
from __future__ import annotations

from core.database.session import get_session
from core.domain.services.history_service import HistoryService


class HistoryFacade:
    """Centralize history DB/session orchestration for UI layers."""

    def get_attempt_detail(self, attempt_id: int) -> dict | None:
        with get_session() as session:
            return HistoryService.get_attempt_detail(session, attempt_id)

    def delete_attempt(self, attempt_id: int) -> bool:
        with get_session() as session:
            return HistoryService.delete_attempt(session, attempt_id)
