"""Facade for dashboard data loading workflows."""
from __future__ import annotations

from dataclasses import dataclass

from core.database.models import Question
from core.database.session import get_session
from core.domain.services.question_service import (
    QuestionService,
    QuestionTypeBreakdown,
    QuestionUsageRow,
    QuestionUsageSummary,
)


@dataclass
class DashboardOverview:
    total_banks: int
    total_questions: int
    type_breakdown: QuestionTypeBreakdown
    recent_banks: list[tuple[int, str, int]]


class DashboardFacade:
    """Centralize dashboard DB/session orchestration for UI."""

    def __init__(self) -> None:
        self._service = QuestionService()

    def load_overview(self) -> DashboardOverview:
        with get_session() as session:
            stats = self._service.get_bank_stats(session)
            total_banks = len(stats)
            total_q = sum(s.question_count for s in stats)
            type_breakdown = self._service.get_question_type_breakdown(session)

        recent = [(s.bank_id, s.bank_name, s.question_count) for s in stats[:10]]
        return DashboardOverview(
            total_banks=total_banks,
            total_questions=total_q,
            type_breakdown=type_breakdown,
            recent_banks=recent,
        )

    def load_usage_banks(self) -> list[tuple[int, str]]:
        with get_session() as session:
            stats = self._service.get_usage_banks(session)
            return [(s.bank_id, s.bank_name) for s in stats]

    def load_usage_stats(
        self, bank_id: int
    ) -> tuple[list[QuestionUsageRow], QuestionUsageSummary]:
        with get_session() as session:
            rows = self._service.get_question_usage_rows(session, bank_id)
            summary = self._service.build_usage_summary(rows)
        return rows, summary

    def get_question_for_edit(self, question_id: int) -> Question | None:
        with get_session() as session:
            return self._service.get_question_for_edit(session, question_id)
