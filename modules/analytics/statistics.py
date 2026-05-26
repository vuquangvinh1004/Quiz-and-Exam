"""Basic analytics: attempt statistics.

Provides a simple aggregation over completed attempts for display
on the Dashboard or Analytics view.

Only SUBMITTED, TIME_UP and COMPLETED attempts are included in
statistics.  IN_PROGRESS attempts are excluded because they have
incomplete data.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Float, case, cast, func
from sqlalchemy.orm import Session

from core.database.models import Attempt
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
