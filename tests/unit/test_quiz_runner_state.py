"""Unit tests for modules/quiz_runner/session_state.py.

PR-10 hardening coverage for state reset behavior.
"""
from __future__ import annotations

from datetime import datetime, timezone

from core.domain.services.quiz_service import QuizInfoDTO, QuizQuestionSnapshot
from modules.quiz_runner.session_state import QuizRunnerState


def test_reset_runtime_keeps_pending_quiz_info() -> None:
    state = QuizRunnerState(
        pending_quiz_id=10,
        quiz_info=QuizInfoDTO(title="Quiz", mode="EXAM", time_limit=30, total=5),
        quiz_title="Quiz",
        mode="EXAM",
        attempt_id=99,
        quiz_questions=[
            QuizQuestionSnapshot(quiz_question_id=1, order=1, content="Q", type="MC")
        ],
        current_index=1,
        answers={1: {"selected": "A"}},
        confirmed={1},
        submitter_name="A",
        submitter_id="B",
        started_at=datetime.now(timezone.utc),
    )

    state.reset_runtime()

    assert state.pending_quiz_id == 10
    assert state.quiz_info is not None
    assert state.attempt_id is None
    assert state.quiz_questions == []
    assert state.answers == {}
    assert state.confirmed == set()
    assert state.started_at is None


def test_reset_all_clears_everything() -> None:
    state = QuizRunnerState(
        pending_quiz_id=20,
        quiz_info=QuizInfoDTO(title="Quiz 2", mode="STUDY", time_limit=None, total=2),
        quiz_title="Quiz 2",
        mode="STUDY",
        attempt_id=7,
        answers={1: {"text": "Paris"}},
    )

    state.reset_all()

    assert state.pending_quiz_id is None
    assert state.quiz_info is None
    assert state.quiz_title == ""
    assert state.mode == ""
    assert state.attempt_id is None
    assert state.answers == {}
