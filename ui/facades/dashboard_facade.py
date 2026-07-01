"""Facade for dashboard data loading workflows."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from config.paths import LOGS_DIR
from core.database.models import Question
from core.database.session import get_session
from core.domain.services.question_service import (
    QuestionService,
    QuestionTypeBreakdown,
    QuestionUsageRow,
    QuestionUsageSummary,
)
from core.domain.services.telemetry_service import (
    TelemetryService,
    TelemetryWarningSummary,
)
from modules.analytics.statistics import (
    AttemptBankBreakdownRow,
    AttemptModeBreakdown,
    AttemptStatistics,
    AttemptStats,
    AttemptTrendPoint,
    AttemptWindowSummary,
)


@dataclass
class DashboardOverview:
    total_banks: int
    total_questions: int
    type_breakdown: QuestionTypeBreakdown
    recent_banks: list[tuple[int, str, int]]
    attempt_stats: AttemptStats
    mode_breakdown: AttemptModeBreakdown
    recent_activity: list[AttemptTrendPoint]
    reporting_window_summary: AttemptWindowSummary
    reporting_bank_breakdown: list[AttemptBankBreakdownRow]


@dataclass
class DashboardReportingSnapshot:
    mode_breakdown: AttemptModeBreakdown
    recent_activity: list[AttemptTrendPoint]
    window_summary: AttemptWindowSummary
    bank_breakdown: list[AttemptBankBreakdownRow]


class DashboardFacade:
    """Centralize dashboard DB/session orchestration for UI."""

    def __init__(self) -> None:
        self._service = QuestionService()
        self._telemetry = TelemetryService()

    def load_overview(self) -> DashboardOverview:
        with get_session() as session:
            stats = self._service.get_bank_stats(session)
            total_banks = len(stats)
            total_q = sum(s.question_count for s in stats)
            type_breakdown = self._service.get_question_type_breakdown(session)
            attempt_stats = AttemptStatistics.get_overall_stats(session)
            mode_breakdown = AttemptStatistics.get_mode_breakdown(session)
            recent_activity = AttemptStatistics.get_recent_activity(session, days=7)
            reporting_window_summary = AttemptStatistics.get_filtered_window_summary(
                session,
                days=7,
            )
            reporting_bank_breakdown = AttemptStatistics.get_filtered_bank_breakdown(
                session,
                days=7,
            )

        recent = [(s.bank_id, s.bank_name, s.question_count) for s in stats[:10]]
        return DashboardOverview(
            total_banks=total_banks,
            total_questions=total_q,
            type_breakdown=type_breakdown,
            recent_banks=recent,
            attempt_stats=attempt_stats,
            mode_breakdown=mode_breakdown,
            recent_activity=recent_activity,
            reporting_window_summary=reporting_window_summary,
            reporting_bank_breakdown=reporting_bank_breakdown,
        )

    def load_usage_banks(self) -> list[tuple[int, str]]:
        with get_session() as session:
            stats = self._service.get_usage_banks(session)
            return [(s.bank_id, s.bank_name) for s in stats]

    def load_reporting_banks(self) -> list[tuple[int, str]]:
        return self.load_usage_banks()

    def load_reporting_quizzes(self, bank_id: int | None = None) -> list[tuple[int, str]]:
        with get_session() as session:
            return AttemptStatistics.list_reporting_quizzes(session, bank_id=bank_id)

    def load_filtered_reporting(
        self,
        *,
        bank_id: int | None,
        quiz_id: int | None,
        days: int,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> DashboardReportingSnapshot:
        with get_session() as session:
            mode_breakdown = AttemptStatistics.get_filtered_mode_breakdown(
                session,
                bank_id=bank_id,
                quiz_id=quiz_id,
                days=days,
                start_date=start_date,
                end_date=end_date,
            )
            recent_activity = AttemptStatistics.get_filtered_recent_activity(
                session,
                bank_id=bank_id,
                quiz_id=quiz_id,
                days=days,
                start_date=start_date,
                end_date=end_date,
            )
            window_summary = AttemptStatistics.get_filtered_window_summary(
                session,
                bank_id=bank_id,
                quiz_id=quiz_id,
                days=days,
                start_date=start_date,
                end_date=end_date,
            )
            bank_breakdown = AttemptStatistics.get_filtered_bank_breakdown(
                session,
                bank_id=bank_id,
                quiz_id=quiz_id,
                days=days,
                start_date=start_date,
                end_date=end_date,
            )
        return DashboardReportingSnapshot(
            mode_breakdown=mode_breakdown,
            recent_activity=recent_activity,
            window_summary=window_summary,
            bank_breakdown=bank_breakdown,
        )

    def export_reporting_csv(
        self,
        *,
        output_path: Path,
        bank_id: int | None,
        quiz_id: int | None,
        days: int,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> Path:
        snapshot = self.load_filtered_reporting(
            bank_id=bank_id,
            quiz_id=quiz_id,
            days=days,
            start_date=start_date,
            end_date=end_date,
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8-sig", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(["section", "metric", "value"])
            writer.writerow(["summary", "total_attempts", snapshot.window_summary.total_attempts])
            writer.writerow(["summary", "active_banks", snapshot.window_summary.active_banks])
            writer.writerow(["summary", "active_quizzes", snapshot.window_summary.active_quizzes])
            writer.writerow(["summary", "avg_score_pct", snapshot.window_summary.avg_score_pct])
            writer.writerow(["summary", "best_score_pct", snapshot.window_summary.best_score_pct])
            writer.writerow(["mode_breakdown", "exam_count", snapshot.mode_breakdown.exam_count])
            writer.writerow(["mode_breakdown", "practice_count", snapshot.mode_breakdown.practice_count])
            writer.writerow(["mode_breakdown", "study_count", snapshot.mode_breakdown.study_count])
            writer.writerow([])
            writer.writerow(["recent_activity", "date", "attempts", "avg_score_pct"])
            for point in snapshot.recent_activity:
                writer.writerow(["recent_activity", point.date_label, point.attempts, point.avg_score_pct])
            writer.writerow([])
            writer.writerow(
                ["bank_breakdown", "bank_name", "attempt_count", "quiz_count", "avg_score_pct", "best_score_pct", "last_activity_at"]
            )
            for row in snapshot.bank_breakdown:
                writer.writerow(
                    [
                        "bank_breakdown",
                        row.bank_name,
                        row.attempt_count,
                        row.quiz_count,
                        row.avg_score_pct,
                        row.best_score_pct,
                        row.last_activity_at,
                    ]
                )
        return output_path

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

    def load_warning_summary(self) -> TelemetryWarningSummary:
        return self._telemetry.load_warning_summary(LOGS_DIR)
