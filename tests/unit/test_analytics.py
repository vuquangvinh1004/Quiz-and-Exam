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
    score=5.0, max_score=10.0,
    correct=5, incorrect=3, skipped=2,
):
    a = Attempt(
        quiz_id=quiz_id,
        mode="EXAM",
        status=status,
        score=score,
        max_score=max_score,
        answered_count=correct + incorrect,
        correct_count=correct,
        incorrect_count=incorrect,
        skipped_count=skipped,
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
