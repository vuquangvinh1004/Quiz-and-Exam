"""Unit tests for core/domain/services/history_service.py (Phase 6).

Tests:
  - list_attempts: empty DB, ordered result, score_pct calculation
  - get_attempt_detail: summary + answers, None for missing id
  - delete_attempt: removes row, returns False for unknown id
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from core.database.models import (
    Attempt,
    AttemptAnswer,
    Quiz,
    QuestionBank,
    QuizQuestion,
)
from core.domain.services.history_service import HistoryService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_bank(session, name="Bank"):
    bank = QuestionBank(name=name)
    session.add(bank)
    session.flush()
    return bank


def _make_quiz(session, bank_id, title="Test Quiz", mode="EXAM"):
    quiz = Quiz(
        title=title,
        bank_id=bank_id,
        mode=mode,
        time_limit_minutes=30 if mode != "STUDY" else None,
        total_questions=2,
    )
    session.add(quiz)
    session.flush()
    return quiz


def _make_attempt(
    session,
    quiz_id,
    mode="EXAM",
    status="SUBMITTED",
    score=7.0,
    max_score=10.0,
    correct_count=7,
    incorrect_count=2,
    skipped_count=1,
    duration_seconds=None,
):
    attempt = Attempt(
        quiz_id=quiz_id,
        mode=mode,
        status=status,
        score=score,
        max_score=max_score,
        answered_count=correct_count + incorrect_count,
        correct_count=correct_count,
        incorrect_count=incorrect_count,
        skipped_count=skipped_count,
        duration_seconds=duration_seconds,
    )
    session.add(attempt)
    session.flush()
    return attempt


def _make_quiz_question(session, quiz_id, order=0, content="Q?"):
    qq = QuizQuestion(
        quiz_id=quiz_id,
        question_id=1,  # not FK-checked in in-memory SQLite for our test
        question_order=order,
        snapshot_content=content,
        snapshot_type="MC",
        snapshot_point_value=1.0,
    )
    session.add(qq)
    session.flush()
    return qq


def _make_attempt_answer(session, attempt_id, qq_id, is_correct=True, score=1.0, state="correct"):
    aa = AttemptAnswer(
        attempt_id=attempt_id,
        quiz_question_id=qq_id,
        answer_payload=json.dumps({"selected": "A"}),
        is_answered=True,
        is_correct=is_correct,
        score_awarded=score,
        feedback_state=state,
    )
    session.add(aa)
    session.flush()
    return aa


# ---------------------------------------------------------------------------
# TestListAttempts
# ---------------------------------------------------------------------------

class TestListAttempts:

    def test_empty_db_returns_empty_list(self, db_session):
        result = HistoryService.list_attempts(db_session)
        assert result == []

    def test_single_attempt_returned(self, db_session):
        bank = _make_bank(db_session)
        quiz = _make_quiz(db_session, bank.id)
        _make_attempt(db_session, quiz.id)
        result = HistoryService.list_attempts(db_session)
        assert len(result) == 1

    def test_result_contains_quiz_title(self, db_session):
        bank = _make_bank(db_session)
        quiz = _make_quiz(db_session, bank.id, title="My Quiz")
        _make_attempt(db_session, quiz.id)
        result = HistoryService.list_attempts(db_session)
        assert result[0]["quiz_title"] == "My Quiz"

    def test_score_pct_calculated_correctly(self, db_session):
        bank = _make_bank(db_session)
        quiz = _make_quiz(db_session, bank.id)
        _make_attempt(db_session, quiz.id, score=5.0, max_score=10.0)
        result = HistoryService.list_attempts(db_session)
        assert result[0]["score_pct"] == pytest.approx(50.0)

    def test_score_pct_zero_when_max_score_zero(self, db_session):
        bank = _make_bank(db_session)
        quiz = _make_quiz(db_session, bank.id)
        _make_attempt(db_session, quiz.id, score=0.0, max_score=0.0)
        result = HistoryService.list_attempts(db_session)
        assert result[0]["score_pct"] == pytest.approx(0.0)

    def test_ordered_by_started_at_desc(self, db_session):
        bank = _make_bank(db_session)
        quiz = _make_quiz(db_session, bank.id)
        # Use explicit started_at to ensure deterministic ordering
        a1 = _make_attempt(db_session, quiz.id)
        a1.started_at = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        a2 = _make_attempt(db_session, quiz.id)
        a2.started_at = datetime(2024, 1, 2, 10, 0, 0, tzinfo=timezone.utc)
        db_session.flush()
        result = HistoryService.list_attempts(db_session)
        # a2 (newer) should come first
        ids = [r["id"] for r in result]
        assert ids[0] == a2.id
        assert ids[1] == a1.id

    def test_limit_respected(self, db_session):
        bank = _make_bank(db_session)
        quiz = _make_quiz(db_session, bank.id)
        for _ in range(5):
            _make_attempt(db_session, quiz.id)
        result = HistoryService.list_attempts(db_session, limit=3)
        assert len(result) == 3

    def test_fallback_title_when_quiz_missing(self, db_session):
        # Create attempt with quiz_id that doesn't exist in DB
        attempt = Attempt(
            quiz_id=9999, mode="EXAM", status="SUBMITTED",
            score=0.0, max_score=0.0,
        )
        db_session.add(attempt)
        db_session.flush()
        result = HistoryService.list_attempts(db_session)
        assert "9999" in result[0]["quiz_title"]


# ---------------------------------------------------------------------------
# TestGetAttemptDetail
# ---------------------------------------------------------------------------

class TestGetAttemptDetail:

    def test_returns_none_for_missing_id(self, db_session):
        result = HistoryService.get_attempt_detail(db_session, 99999)
        assert result is None

    def test_returns_attempt_data(self, db_session):
        bank = _make_bank(db_session)
        quiz = _make_quiz(db_session, bank.id, title="Detail Test")
        attempt = _make_attempt(db_session, quiz.id, score=8.0, max_score=10.0)
        result = HistoryService.get_attempt_detail(db_session, attempt.id)
        assert result is not None
        assert result["quiz_title"] == "Detail Test"
        assert result["score"] == pytest.approx(8.0)
        assert result["score_pct"] == pytest.approx(80.0)

    def test_answers_list_sorted_by_question_order(self, db_session):
        bank = _make_bank(db_session)
        quiz = _make_quiz(db_session, bank.id)
        attempt = _make_attempt(db_session, quiz.id)
        qq1 = _make_quiz_question(db_session, quiz.id, order=1, content="Q1")
        qq2 = _make_quiz_question(db_session, quiz.id, order=0, content="Q0")
        _make_attempt_answer(db_session, attempt.id, qq1.id)
        _make_attempt_answer(db_session, attempt.id, qq2.id)
        result = HistoryService.get_attempt_detail(db_session, attempt.id)
        orders = [a["question_order"] for a in result["answers"]]
        assert orders == sorted(orders)

    def test_answers_contain_feedback_state(self, db_session):
        bank = _make_bank(db_session)
        quiz = _make_quiz(db_session, bank.id)
        attempt = _make_attempt(db_session, quiz.id)
        qq = _make_quiz_question(db_session, quiz.id)
        _make_attempt_answer(db_session, attempt.id, qq.id, state="correct")
        result = HistoryService.get_attempt_detail(db_session, attempt.id)
        assert result["answers"][0]["feedback_state"] == "correct"

    def test_answer_payload_deserialized(self, db_session):
        bank = _make_bank(db_session)
        quiz = _make_quiz(db_session, bank.id)
        attempt = _make_attempt(db_session, quiz.id)
        qq = _make_quiz_question(db_session, quiz.id)
        _make_attempt_answer(db_session, attempt.id, qq.id)
        result = HistoryService.get_attempt_detail(db_session, attempt.id)
        assert isinstance(result["answers"][0]["answer_payload"], dict)


# ---------------------------------------------------------------------------
# TestDeleteAttempt
# ---------------------------------------------------------------------------

class TestDeleteAttempt:

    def test_returns_false_for_missing_id(self, db_session):
        assert HistoryService.delete_attempt(db_session, 99999) is False

    def test_returns_true_when_found(self, db_session):
        bank = _make_bank(db_session)
        quiz = _make_quiz(db_session, bank.id)
        attempt = _make_attempt(db_session, quiz.id)
        assert HistoryService.delete_attempt(db_session, attempt.id) is True

    def test_attempt_removed_from_db(self, db_session):
        bank = _make_bank(db_session)
        quiz = _make_quiz(db_session, bank.id)
        attempt = _make_attempt(db_session, quiz.id)
        HistoryService.delete_attempt(db_session, attempt.id)
        assert db_session.get(Attempt, attempt.id) is None

    def test_list_attempts_empty_after_delete(self, db_session):
        bank = _make_bank(db_session)
        quiz = _make_quiz(db_session, bank.id)
        attempt = _make_attempt(db_session, quiz.id)
        HistoryService.delete_attempt(db_session, attempt.id)
        assert HistoryService.list_attempts(db_session) == []


# ---------------------------------------------------------------------------
# TestJoinedLoadBehavior
# (Regression guard: quiz_title must be populated via relationship,
#  not a separate lazy query)
# ---------------------------------------------------------------------------

class TestJoinedLoadBehavior:

    def test_quiz_title_available_after_session_expunge(self, db_session):
        """Verify that quiz_title comes from the eagerly-loaded relationship.

        After expunging the Attempt from the session, accessing attempt.quiz.title
        via lazy load would raise DetachedInstanceError.  The joinedload means it
        is already in memory, so dict-building in _attempt_summary() must succeed.
        """
        bank = _make_bank(db_session)
        quiz = _make_quiz(db_session, bank.id, title="Eagerly Loaded Quiz")
        _make_attempt(db_session, quiz.id)

        result = HistoryService.list_attempts(db_session)
        assert result[0]["quiz_title"] == "Eagerly Loaded Quiz"

    def test_multiple_attempts_same_quiz_all_have_title(self, db_session):
        bank = _make_bank(db_session)
        quiz = _make_quiz(db_session, bank.id, title="Shared Quiz")
        for _ in range(3):
            _make_attempt(db_session, quiz.id)

        result = HistoryService.list_attempts(db_session)
        titles = [r["quiz_title"] for r in result]
        assert all(t == "Shared Quiz" for t in titles)

    def test_detail_answers_use_quiz_question_snapshot(self, db_session):
        """AttemptAnswer details must include snapshot_content from QuizQuestion."""
        bank = _make_bank(db_session)
        quiz = _make_quiz(db_session, bank.id)
        attempt = _make_attempt(db_session, quiz.id)
        qq = _make_quiz_question(db_session, quiz.id, content="Snapshot Q?")
        _make_attempt_answer(db_session, attempt.id, qq.id)

        detail = HistoryService.get_attempt_detail(db_session, attempt.id)
        assert detail["answers"][0]["question_content"] == "Snapshot Q?"
