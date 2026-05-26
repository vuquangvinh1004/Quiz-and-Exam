from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from core.domain.services.quiz_service import QuizQuestionSnapshot
from modules.quiz_runner.submit_handler import build_graded_result, payload_display


def _mc_question() -> QuizQuestionSnapshot:
    return QuizQuestionSnapshot(
        quiz_question_id=1,
        order=1,
        content="2 + 2 = ?",
        type="MC",
        point_value=1.0,
        options=[
            {"key": "A", "text": "4", "is_correct": True},
            {"key": "B", "text": "5", "is_correct": False},
        ],
        accepted_answers=[],
    )


def _sa_question() -> QuizQuestionSnapshot:
    return QuizQuestionSnapshot(
        quiz_question_id=2,
        order=2,
        content="Hành tinh gần Mặt Trời nhất?",
        type="SA",
        point_value=2.0,
        options=[],
        accepted_answers=["Mercury"],
        case_sensitive=False,
        trim_whitespace=True,
    )


def test_payload_display_variants() -> None:
    assert payload_display("MC", {"selected": "A"}) == "A"
    assert payload_display("MA", {"selected": ["A", "B"]}) == "A, B"
    assert payload_display("BLANK", {"text": "Paris"}) == "Paris"
    assert payload_display("MC", {}) == "Bỏ qua"


def test_build_graded_result_returns_rows_and_summary() -> None:
    started_at = datetime.now(timezone.utc) - timedelta(seconds=12)
    questions = [_mc_question(), _sa_question()]
    answers = {
        1: {"selected": "A"},
        2: {},
    }

    graded_rows, result = build_graded_result(
        quiz_questions=questions,
        answers=answers,
        started_at=started_at,
        submitter_name="Nguyen Van A",
        submitter_id="S001",
        quiz_title="Đề kiểm tra số 1",
        mode="EXAM",
    )

    assert len(graded_rows) == 2
    assert graded_rows[0].quiz_question_id == 1
    assert graded_rows[0].is_correct is True
    assert graded_rows[1].quiz_question_id == 2
    assert graded_rows[1].is_correct is None

    assert result.correct_count == 1
    assert result.incorrect_count == 0
    assert result.skipped_count == 1
    assert result.score == pytest.approx(1.0)
    assert result.max_score == pytest.approx(3.0)
    assert result.duration_seconds >= 12
    assert len(result.questions) == 2
    assert result.questions[0].answer_text == "A"
    assert result.questions[1].answer_text == "Bỏ qua"
