"""Unit tests for modules/analytics/statistics.py (Phase 6).

Tests:
  - get_overall_stats: zero stats on empty DB
  - counts only completed/submitted/time_up attempts
  - aggregate totals (correct, incorrect, skipped)
  - avg_score_pct calculation
  - best_score_pct detection
  - handles attempts with max_score=0 gracefully
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from core.database.models import Attempt, QuestionBank, Quiz
from modules.analytics.statistics import AttemptStatistics, AttemptStats


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_bank(session, name="Bank"):
    bank = QuestionBank(name=name)
    session.add(bank)
    session.flush()
    return bank


def _make_quiz(session, bank_id):
    quiz = Quiz(
        title="Quiz",
        bank_id=bank_id,
        mode="EXAM",
        time_limit_minutes=30,
        total_questions=5,
    )
    session.add(quiz)
    session.flush()
    return quiz


def _make_attempt(
    session, quiz_id,
    status="SUBMITTED",
    mode="EXAM",
    score=5.0, max_score=10.0,
    correct=5, incorrect=3, skipped=2,
    submitted_at=None,
):
    a = Attempt(
        quiz_id=quiz_id,
        mode=mode,
        status=status,
        score=score,
        max_score=max_score,
        answered_count=correct + incorrect,
        correct_count=correct,
        incorrect_count=incorrect,
        skipped_count=skipped,
        submitted_at=submitted_at,
    )
    session.add(a)
    session.flush()
    return a


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestGetOverallStats:

    def test_empty_db_returns_zero_stats(self, db_session):
        stats = AttemptStatistics.get_overall_stats(db_session)
        assert isinstance(stats, AttemptStats)
        assert stats.total_attempts == 0
        assert stats.avg_score_pct == pytest.approx(0.0)
        assert stats.best_score_pct == pytest.approx(0.0)
        assert stats.total_correct == 0
        assert stats.total_incorrect == 0
        assert stats.total_skipped == 0

    def test_counts_submitted_attempts(self, db_session):
        bank = _make_bank(db_session)
        quiz = _make_quiz(db_session, bank.id)
        _make_attempt(db_session, quiz.id, status="SUBMITTED")
        _make_attempt(db_session, quiz.id, status="SUBMITTED")
        stats = AttemptStatistics.get_overall_stats(db_session)
        assert stats.total_attempts == 2

    def test_counts_time_up_attempts(self, db_session):
        bank = _make_bank(db_session)
        quiz = _make_quiz(db_session, bank.id)
        _make_attempt(db_session, quiz.id, status="TIME_UP")
        stats = AttemptStatistics.get_overall_stats(db_session)
        assert stats.total_attempts == 1

    def test_counts_completed_attempts(self, db_session):
        bank = _make_bank(db_session)
        quiz = _make_quiz(db_session, bank.id)
        _make_attempt(db_session, quiz.id, status="COMPLETED")
        stats = AttemptStatistics.get_overall_stats(db_session)
        assert stats.total_attempts == 1

    def test_excludes_in_progress_attempts(self, db_session):
        bank = _make_bank(db_session)
        quiz = _make_quiz(db_session, bank.id)
        _make_attempt(db_session, quiz.id, status="IN_PROGRESS")
        stats = AttemptStatistics.get_overall_stats(db_session)
        assert stats.total_attempts == 0

    def test_totals_correct_incorrect_skipped(self, db_session):
        bank = _make_bank(db_session)
        quiz = _make_quiz(db_session, bank.id)
        _make_attempt(db_session, quiz.id, correct=3, incorrect=2, skipped=1)
        _make_attempt(db_session, quiz.id, correct=7, incorrect=1, skipped=0)
        stats = AttemptStatistics.get_overall_stats(db_session)
        assert stats.total_correct == 10
        assert stats.total_incorrect == 3
        assert stats.total_skipped == 1

    def test_avg_score_pct_single_attempt(self, db_session):
        bank = _make_bank(db_session)
        quiz = _make_quiz(db_session, bank.id)
        _make_attempt(db_session, quiz.id, score=6.0, max_score=10.0)
        stats = AttemptStatistics.get_overall_stats(db_session)
        assert stats.avg_score_pct == pytest.approx(60.0)

    def test_avg_score_pct_multiple_attempts(self, db_session):
        bank = _make_bank(db_session)
        quiz = _make_quiz(db_session, bank.id)
        _make_attempt(db_session, quiz.id, score=4.0, max_score=10.0)   # 40%
        _make_attempt(db_session, quiz.id, score=8.0, max_score=10.0)   # 80%
        stats = AttemptStatistics.get_overall_stats(db_session)
        assert stats.avg_score_pct == pytest.approx(60.0)

    def test_best_score_pct(self, db_session):
        bank = _make_bank(db_session)
        quiz = _make_quiz(db_session, bank.id)
        _make_attempt(db_session, quiz.id, score=4.0, max_score=10.0)   # 40%
        _make_attempt(db_session, quiz.id, score=9.0, max_score=10.0)   # 90%
        _make_attempt(db_session, quiz.id, score=7.0, max_score=10.0)   # 70%
        stats = AttemptStatistics.get_overall_stats(db_session)
        assert stats.best_score_pct == pytest.approx(90.0)

    def test_attempts_with_zero_max_score_excluded_from_pct(self, db_session):
        bank = _make_bank(db_session)
        quiz = _make_quiz(db_session, bank.id)
        _make_attempt(db_session, quiz.id, score=0.0, max_score=0.0)
        # Should not crash; counts as 1 total, 0.0 avg/best (no valid pct)
        stats = AttemptStatistics.get_overall_stats(db_session)
        assert stats.total_attempts == 1
        assert stats.avg_score_pct == pytest.approx(0.0)
        assert stats.best_score_pct == pytest.approx(0.0)

    def test_all_three_statuses_counted_together(self, db_session):
        """SUBMITTED + TIME_UP + COMPLETED are all included in total."""
        bank = _make_bank(db_session)
        quiz = _make_quiz(db_session, bank.id)
        _make_attempt(db_session, quiz.id, status="SUBMITTED")
        _make_attempt(db_session, quiz.id, status="TIME_UP")
        _make_attempt(db_session, quiz.id, status="COMPLETED")
        _make_attempt(db_session, quiz.id, status="IN_PROGRESS")  # excluded
        stats = AttemptStatistics.get_overall_stats(db_session)
        assert stats.total_attempts == 3

    def test_avg_score_pct_mixed_percentages(self, db_session):
        """avg_score_pct is the mean of per-attempt percentages."""
        bank = _make_bank(db_session)
        quiz = _make_quiz(db_session, bank.id)
        # 25%, 75%, 100% → avg = 66.666...
        _make_attempt(db_session, quiz.id, score=2.5, max_score=10.0)
        _make_attempt(db_session, quiz.id, score=7.5, max_score=10.0)
        _make_attempt(db_session, quiz.id, score=10.0, max_score=10.0)
        stats = AttemptStatistics.get_overall_stats(db_session)
        assert stats.avg_score_pct == pytest.approx(200 / 3, abs=0.1)

    def test_best_score_pct_uses_max_not_last(self, db_session):
        """best_score_pct is the maximum percentage across all attempts."""
        bank = _make_bank(db_session)
        quiz = _make_quiz(db_session, bank.id)
        _make_attempt(db_session, quiz.id, score=10.0, max_score=10.0)  # 100%
        _make_attempt(db_session, quiz.id, score=5.0, max_score=10.0)   # 50%
        _make_attempt(db_session, quiz.id, score=3.0, max_score=10.0)   # 30%
        stats = AttemptStatistics.get_overall_stats(db_session)
        assert stats.best_score_pct == pytest.approx(100.0)

    def test_mode_breakdown_counts_completed_attempts_only(self, db_session):
        bank = _make_bank(db_session)
        quiz = _make_quiz(db_session, bank.id)
        _make_attempt(db_session, quiz.id, mode="EXAM", status="SUBMITTED")
        _make_attempt(db_session, quiz.id, mode="PRACTICE", status="TIME_UP")
        _make_attempt(db_session, quiz.id, mode="STUDY", status="COMPLETED")
        _make_attempt(db_session, quiz.id, mode="EXAM", status="IN_PROGRESS")

        breakdown = AttemptStatistics.get_mode_breakdown(db_session)

        assert breakdown.exam_count == 1
        assert breakdown.practice_count == 1
        assert breakdown.study_count == 1

    def test_recent_activity_returns_points_for_requested_window(self, db_session):
        bank = _make_bank(db_session)
        quiz = _make_quiz(db_session, bank.id)
        now = datetime.now(timezone.utc)
        _make_attempt(
            db_session,
            quiz.id,
            status="SUBMITTED",
            score=8.0,
            max_score=10.0,
            submitted_at=now - timedelta(days=1),
        )
        _make_attempt(
            db_session,
            quiz.id,
            status="TIME_UP",
            score=6.0,
            max_score=10.0,
            submitted_at=now - timedelta(days=3),
        )

        points = AttemptStatistics.get_recent_activity(db_session, days=5)

        assert len(points) == 5
        assert sum(point.attempts for point in points) == 2
        assert any(point.avg_score_pct == pytest.approx(80.0) for point in points)
        assert any(point.avg_score_pct == pytest.approx(60.0) for point in points)

    def test_filtered_breakdown_supports_bank_quiz_and_days(self, db_session):
        bank1 = _make_bank(db_session, "Bank1")
        bank2 = _make_bank(db_session, "Bank2")
        quiz1 = _make_quiz(db_session, bank1.id)
        quiz2 = _make_quiz(db_session, bank2.id)
        now = datetime.now(timezone.utc)
        _make_attempt(
            db_session,
            quiz1.id,
            mode="EXAM",
            status="SUBMITTED",
            submitted_at=now - timedelta(days=1),
        )
        _make_attempt(
            db_session,
            quiz1.id,
            mode="PRACTICE",
            status="SUBMITTED",
            submitted_at=now - timedelta(days=10),
        )
        _make_attempt(
            db_session,
            quiz2.id,
            mode="STUDY",
            status="SUBMITTED",
            submitted_at=now - timedelta(days=1),
        )

        breakdown = AttemptStatistics.get_filtered_mode_breakdown(
            db_session,
            bank_id=bank1.id,
            quiz_id=quiz1.id,
            days=7,
        )
        recent = AttemptStatistics.get_filtered_recent_activity(
            db_session,
            bank_id=bank1.id,
            quiz_id=quiz1.id,
            days=7,
        )

        assert breakdown.exam_count == 1
        assert breakdown.practice_count == 0
        assert breakdown.study_count == 0
        assert sum(point.attempts for point in recent) == 1

    def test_filtered_window_summary_and_bank_breakdown(self, db_session):
        bank1 = _make_bank(db_session, "Bank Alpha")
        bank2 = _make_bank(db_session, "Bank Beta")
        quiz1 = _make_quiz(db_session, bank1.id)
        quiz2 = _make_quiz(db_session, bank1.id)
        quiz3 = _make_quiz(db_session, bank2.id)
        now = datetime.now(timezone.utc)
        _make_attempt(
            db_session,
            quiz1.id,
            mode="EXAM",
            score=8.0,
            max_score=10.0,
            submitted_at=now - timedelta(days=1),
        )
        _make_attempt(
            db_session,
            quiz2.id,
            mode="PRACTICE",
            score=6.0,
            max_score=10.0,
            submitted_at=now - timedelta(days=2),
        )
        _make_attempt(
            db_session,
            quiz3.id,
            mode="STUDY",
            score=9.0,
            max_score=10.0,
            submitted_at=now - timedelta(days=1),
        )

        summary = AttemptStatistics.get_filtered_window_summary(db_session, days=7)
        breakdown = AttemptStatistics.get_filtered_bank_breakdown(db_session, days=7)

        assert summary.total_attempts == 3
        assert summary.active_banks == 2
        assert summary.active_quizzes == 3
        assert summary.avg_score_pct == pytest.approx(76.7, abs=0.1)
        assert summary.best_score_pct == pytest.approx(90.0)
        assert [row.bank_name for row in breakdown] == ["Bank Alpha", "Bank Beta"]
        assert breakdown[0].attempt_count == 2
        assert breakdown[0].quiz_count == 2
        assert breakdown[0].avg_score_pct == pytest.approx(70.0)
        assert breakdown[1].attempt_count == 1

    def test_filtered_reporting_supports_custom_date_range(self, db_session):
        bank = _make_bank(db_session, "Bank Date")
        quiz = _make_quiz(db_session, bank.id)
        now = datetime.now(timezone.utc)
        _make_attempt(
            db_session,
            quiz.id,
            status="SUBMITTED",
            score=8.0,
            max_score=10.0,
            submitted_at=now - timedelta(days=1),
        )
        _make_attempt(
            db_session,
            quiz.id,
            status="SUBMITTED",
            score=5.0,
            max_score=10.0,
            submitted_at=now - timedelta(days=8),
        )

        start_date = (now - timedelta(days=2)).date()
        end_date = now.date()
        summary = AttemptStatistics.get_filtered_window_summary(
            db_session,
            bank_id=bank.id,
            start_date=start_date,
            end_date=end_date,
            days=0,
        )
        recent = AttemptStatistics.get_filtered_recent_activity(
            db_session,
            bank_id=bank.id,
            start_date=start_date,
            end_date=end_date,
            days=0,
        )

        assert summary.total_attempts == 1
        assert summary.avg_score_pct == pytest.approx(80.0)
        assert len(recent) == 3
        assert sum(point.attempts for point in recent) == 1
