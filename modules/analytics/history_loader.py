"""Background loader for history list and pending GSheets count."""
from __future__ import annotations

from core.database.session import get_session
from core.domain.services.history_service import HistoryService


def load_attempts_and_pending_count() -> tuple[list[dict], int]:
    """Load attempts and pending queue count for non-blocking UI refresh."""
    with get_session() as session:
        attempts = HistoryService.list_attempts(session)

    try:
        from modules.google_sheets.pending_queue import PendingGSheetsQueue

        pending_count = PendingGSheetsQueue().count()
    except (ImportError, OSError, ValueError):
        pending_count = 0

    return attempts, pending_count
