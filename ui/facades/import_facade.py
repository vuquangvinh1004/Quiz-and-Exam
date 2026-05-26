"""Import workflow facade for UI layers.

This facade centralizes session handling for ImportView and ImportPreviewDialog
so UI widgets do not manipulate DB sessions directly.
"""
from __future__ import annotations

from pathlib import Path

from core.database.session import get_session
from core.domain.services.import_service import ImportService, ImportSummary
from core.domain.services.question_service import QuestionService
from modules.question_bank.importer import ParseResult


class ImportFacade:
    """High-level import operations used by import UI components."""

    def __init__(self) -> None:
        self._import_service = ImportService()
        self._question_service = QuestionService()

    def load_banks(self) -> list[tuple[int, str]]:
        """Return bank tuples as (id, name) ordered by bank name."""
        with get_session() as session:
            banks = self._question_service.list_banks(session)
            return [(b.id, b.name) for b in banks]

    def create_bank(self, name: str) -> int:
        """Create a question bank and return its new id."""
        with get_session() as session:
            bank = self._question_service.create_bank(session, name)
            return bank.id

    def preview_file(self, file_path: Path) -> ParseResult:
        """Parse import file and enrich with duplicate checks."""
        with get_session() as session:
            return self._import_service.preview(file_path, session)

    def commit_preview(self, parse_result: ParseResult, bank_id: int) -> ImportSummary:
        """Commit validated parse result into target bank."""
        with get_session() as session:
            return self._import_service.commit(parse_result, bank_id, session)
