"""Basic analytics: attempt statistics.

Provides a simple aggregation over completed attempts for display
on the Dashboard or Analytics view.

Only SUBMITTED, TIME_UP and COMPLETED attempts are included in
statistics.  IN_PROGRESS attempts are excluded because they have
incomplete data.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import Float, case, cast, func
from sqlalchemy.orm import Query
from sqlalchemy.orm import Session

from core.database.models import Attempt, Quiz
from core.utils.constants import AttemptStatus


@dataclass
class AttemptStats:
    """Aggregated statistics across all completed quiz attempts.

    Attributes
    ----------
    total_attempts:
        Number of completed/submitted attempts.
    avg_score_pct:
        Average score as a percentage (0–100), rounded to 1 decimal.
    best_score_pct:
        Best (highest) score percentage across all attempts.
    total_correct:
        Total number of correct answers across all attempts.
    total_incorrect:
        Total number of incorrect answers across all attempts.
    total_skipped:
        Total number of skipped answers across all attempts.
    """

    total_attempts: int
    avg_score_pct: float
    best_score_pct: float
    total_correct: int
    total_incorrect: int
    total_skipped: int


@dataclass
class AttemptModeBreakdown:
    exam_count: int
    practice_count: int
    study_count: int


@dataclass
class AttemptTrendPoint:
    date_label: str
    attempts: int
    avg_score_pct: float


@dataclass
class AttemptWindowSummary:
    total_attempts: int
    active_banks: int
    active_quizzes: int
    avg_score_pct: float
    best_score_pct: float


@dataclass
class AttemptBankBreakdownRow:
    bank_id: int
    bank_name: str
    attempt_count: int
    quiz_count: int
    avg_score_pct: float
    best_score_pct: float
    last_activity_at: str


class AttemptStatistics:
    """Computes summary statistics from the attempts table."""

    _COMPLETED_STATUSES: frozenset[str] = frozenset({
        AttemptStatus.SUBMITTED.value,
        AttemptStatus.TIME_UP.value,
        AttemptStatus.COMPLETED.value,
    })

    @staticmethod
    def get_overall_stats(session: Session) -> AttemptStats:
        """Return aggregated stats for all non-in-progress attempts.

        Uses a single SQL aggregate query instead of loading all rows into
        memory.  Returns zero-filled stats when no attempts are found.
        """
        # Percentage expression: NULL when max_score == 0 (excluded from
        # AVG/MAX automatically by SQL aggregate functions).
        pct_col = case(
            (Attempt.max_score > 0,
             cast(Attempt.score, Float) / cast(Attempt.max_score, Float) * 100),
            else_=None,
        )

        result = (
            session.query(
                func.count(Attempt.id).label("total"),
                func.coalesce(func.sum(Attempt.correct_count), 0).label("total_correct"),
                func.coalesce(func.sum(Attempt.incorrect_count), 0).label("total_incorrect"),
                func.coalesce(func.sum(Attempt.skipped_count), 0).label("total_skipped"),
                func.avg(pct_col).label("avg_pct"),
                func.max(pct_col).label("best_pct"),
            )
            .filter(Attempt.status.in_(AttemptStatistics._COMPLETED_STATUSES))
            .one()
        )

        if not result.total:
            return AttemptStats(
                total_attempts=0,
                avg_score_pct=0.0,
                best_score_pct=0.0,
                total_correct=0,
                total_incorrect=0,
                total_skipped=0,
            )

        return AttemptStats(
            total_attempts=result.total,
            avg_score_pct=round(result.avg_pct or 0.0, 1),
            best_score_pct=round(result.best_pct or 0.0, 1),
            total_correct=result.total_correct or 0,
            total_incorrect=result.total_incorrect or 0,
            total_skipped=result.total_skipped or 0,
        )

    @staticmethod
    def get_mode_breakdown(session: Session) -> AttemptModeBreakdown:
        """Return completed-attempt counts split by mode."""
        rows = (
            session.query(Attempt.mode, func.count(Attempt.id).label("cnt"))
            .filter(Attempt.status.in_(AttemptStatistics._COMPLETED_STATUSES))
            .group_by(Attempt.mode)
            .all()
        )
        counts = {str(row.mode): int(row.cnt) for row in rows}
        return AttemptModeBreakdown(
            exam_count=counts.get("EXAM", 0),
            practice_count=counts.get("PRACTICE", 0),
            study_count=counts.get("STUDY", 0),
        )

    @staticmethod
    def get_recent_activity(session: Session, days: int = 7) -> list[AttemptTrendPoint]:
        """Return recent completed-attempt counts and average score by day."""
        if days <= 0:
            return []

        pct_col = case(
            (Attempt.max_score > 0,
             cast(Attempt.score, Float) / cast(Attempt.max_score, Float) * 100),
            else_=None,
        )
        day_col = func.date(func.coalesce(Attempt.submitted_at, Attempt.started_at))

        rows = (
            session.query(
                day_col.label("day"),
                func.count(Attempt.id).label("attempts"),
                func.avg(pct_col).label("avg_pct"),
            )
            .filter(Attempt.status.in_(AttemptStatistics._COMPLETED_STATUSES))
            .group_by(day_col)
            .all()
        )
        by_day = {
            str(row.day): AttemptTrendPoint(
                date_label=str(row.day),
                attempts=int(row.attempts),
                avg_score_pct=round(row.avg_pct or 0.0, 1),
            )
            for row in rows
            if row.day is not None
        }

        today = datetime.now(timezone.utc).date()
        points: list[AttemptTrendPoint] = []
        for offset in range(days - 1, -1, -1):
            day = today - timedelta(days=offset)
            key = day.isoformat()
            point = by_day.get(key)
            if point is None:
                points.append(
                    AttemptTrendPoint(
                        date_label=key,
                        attempts=0,
                        avg_score_pct=0.0,
                    )
                )
            else:
                points.append(point)
        return points

    @staticmethod
    def get_filtered_mode_breakdown(
        session: Session,
        *,
        bank_id: int | None = None,
        quiz_id: int | None = None,
        days: int = 7,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> AttemptModeBreakdown:
        query = AttemptStatistics._filtered_attempt_query(
            session,
            bank_id=bank_id,
            quiz_id=quiz_id,
            days=days,
            start_date=start_date,
            end_date=end_date,
        )
        rows = (
            query.with_entities(Attempt.mode, func.count(Attempt.id).label("cnt"))
            .group_by(Attempt.mode)
            .all()
        )
        counts = {str(row.mode): int(row.cnt) for row in rows}
        return AttemptModeBreakdown(
            exam_count=counts.get("EXAM", 0),
            practice_count=counts.get("PRACTICE", 0),
            study_count=counts.get("STUDY", 0),
        )

    @staticmethod
    def get_filtered_recent_activity(
        session: Session,
        *,
        bank_id: int | None = None,
        quiz_id: int | None = None,
        days: int = 7,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[AttemptTrendPoint]:
        range_start, range_end = AttemptStatistics._resolve_date_range(
            days=days,
            start_date=start_date,
            end_date=end_date,
        )
        if range_start is None or range_end is None:
            return []
        pct_col = case(
            (Attempt.max_score > 0,
             cast(Attempt.score, Float) / cast(Attempt.max_score, Float) * 100),
            else_=None,
        )
        day_col = func.date(func.coalesce(Attempt.submitted_at, Attempt.started_at))
        query = AttemptStatistics._filtered_attempt_query(
            session,
            bank_id=bank_id,
            quiz_id=quiz_id,
            days=days,
            start_date=start_date,
            end_date=end_date,
        )
        rows = (
            query.with_entities(
                day_col.label("day"),
                func.count(Attempt.id).label("attempts"),
                func.avg(pct_col).label("avg_pct"),
            )
            .group_by(day_col)
            .all()
        )
        by_day = {
            str(row.day): AttemptTrendPoint(
                date_label=str(row.day),
                attempts=int(row.attempts),
                avg_score_pct=round(row.avg_pct or 0.0, 1),
            )
            for row in rows
            if row.day is not None
        }
        points: list[AttemptTrendPoint] = []
        total_days = (range_end - range_start).days + 1
        for offset in range(total_days):
            day = range_start + timedelta(days=offset)
            key = day.isoformat()
            points.append(
                by_day.get(
                    key,
                    AttemptTrendPoint(date_label=key, attempts=0, avg_score_pct=0.0),
                )
            )
        return points

    @staticmethod
    def list_reporting_quizzes(
        session: Session,
        *,
        bank_id: int | None = None,
    ) -> list[tuple[int, str]]:
        query = session.query(Quiz.id, Quiz.title)
        if bank_id is not None:
            query = query.filter(Quiz.bank_id == bank_id)
        rows = query.order_by(Quiz.title, Quiz.id).all()
        return [(int(row.id), str(row.title)) for row in rows]

    @staticmethod
    def get_filtered_window_summary(
        session: Session,
        *,
        bank_id: int | None = None,
        quiz_id: int | None = None,
        days: int = 7,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> AttemptWindowSummary:
        pct_col = case(
            (Attempt.max_score > 0,
             cast(Attempt.score, Float) / cast(Attempt.max_score, Float) * 100),
            else_=None,
        )
        query = AttemptStatistics._filtered_attempt_query(
            session,
            bank_id=bank_id,
            quiz_id=quiz_id,
            days=days,
            start_date=start_date,
            end_date=end_date,
        )
        result = query.with_entities(
            func.count(Attempt.id).label("total_attempts"),
            func.count(func.distinct(Quiz.bank_id)).label("active_banks"),
            func.count(func.distinct(Attempt.quiz_id)).label("active_quizzes"),
            func.avg(pct_col).label("avg_pct"),
            func.max(pct_col).label("best_pct"),
        ).one()
        return AttemptWindowSummary(
            total_attempts=int(result.total_attempts or 0),
            active_banks=int(result.active_banks or 0),
            active_quizzes=int(result.active_quizzes or 0),
            avg_score_pct=round(result.avg_pct or 0.0, 1),
            best_score_pct=round(result.best_pct or 0.0, 1),
        )

    @staticmethod
    def get_filtered_bank_breakdown(
        session: Session,
        *,
        bank_id: int | None = None,
        quiz_id: int | None = None,
        days: int = 7,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 10,
    ) -> list[AttemptBankBreakdownRow]:
        pct_col = case(
            (Attempt.max_score > 0,
             cast(Attempt.score, Float) / cast(Attempt.max_score, Float) * 100),
            else_=None,
        )
        activity_col = func.max(func.coalesce(Attempt.submitted_at, Attempt.started_at))
        query = AttemptStatistics._filtered_attempt_query(
            session,
            bank_id=bank_id,
            quiz_id=quiz_id,
            days=days,
            start_date=start_date,
            end_date=end_date,
        )
        rows = (
            query.with_entities(
                Quiz.bank_id.label("bank_id"),
                func.min(Quiz.title).label("sample_quiz_title"),
                func.count(Attempt.id).label("attempt_count"),
                func.count(func.distinct(Attempt.quiz_id)).label("quiz_count"),
                func.avg(pct_col).label("avg_pct"),
                func.max(pct_col).label("best_pct"),
                activity_col.label("last_activity_at"),
            )
            .group_by(Quiz.bank_id)
            .order_by(
                func.count(Attempt.id).desc(),
                activity_col.desc(),
                Quiz.bank_id.asc(),
            )
            .limit(max(limit, 1))
            .all()
        )

        bank_names = {
            int(row.bank_id): AttemptStatistics._resolve_bank_name(session, int(row.bank_id))
            for row in rows
        }
        items: list[AttemptBankBreakdownRow] = []
        for row in rows:
            last_at = row.last_activity_at
            last_label = ""
            if isinstance(last_at, datetime):
                last_label = last_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M")
            elif last_at is not None:
                last_label = str(last_at)
            items.append(
                AttemptBankBreakdownRow(
                    bank_id=int(row.bank_id),
                    bank_name=bank_names.get(int(row.bank_id), f"Bank #{int(row.bank_id)}"),
                    attempt_count=int(row.attempt_count or 0),
                    quiz_count=int(row.quiz_count or 0),
                    avg_score_pct=round(row.avg_pct or 0.0, 1),
                    best_score_pct=round(row.best_pct or 0.0, 1),
                    last_activity_at=last_label,
                )
            )
        return items

    @staticmethod
    def _resolve_bank_name(session: Session, bank_id: int) -> str:
        from core.database.models import QuestionBank

        name = (
            session.query(QuestionBank.name)
            .filter(QuestionBank.id == bank_id)
            .scalar()
        )
        return str(name) if name else f"Bank #{bank_id}"

    @staticmethod
    def _filtered_attempt_query(
        session: Session,
        *,
        bank_id: int | None,
        quiz_id: int | None,
        days: int,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> Query:
        query = (
            session.query(Attempt)
            .join(Quiz, Quiz.id == Attempt.quiz_id)
            .filter(Attempt.status.in_(AttemptStatistics._COMPLETED_STATUSES))
        )
        if bank_id is not None:
            query = query.filter(Quiz.bank_id == bank_id)
        if quiz_id is not None:
            query = query.filter(Attempt.quiz_id == quiz_id)
        range_start, range_end = AttemptStatistics._resolve_date_range(
            days=days,
            start_date=start_date,
            end_date=end_date,
        )
        if range_start is not None and range_end is not None:
            since = datetime.combine(range_start, time.min, tzinfo=timezone.utc)
            until = datetime.combine(range_end, time.max, tzinfo=timezone.utc)
            activity_col = func.coalesce(Attempt.submitted_at, Attempt.started_at)
            query = query.filter(activity_col >= since)
            query = query.filter(activity_col <= until)
        return query

    @staticmethod
    def _resolve_date_range(
        *,
        days: int,
        start_date: date | None,
        end_date: date | None,
    ) -> tuple[date | None, date | None]:
        if start_date is not None and end_date is not None:
            if start_date > end_date:
                start_date, end_date = end_date, start_date
            return start_date, end_date
        if days <= 0:
            return None, None
        today = datetime.now(timezone.utc).date()
        return today - timedelta(days=days - 1), today
