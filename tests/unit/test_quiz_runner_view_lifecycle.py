from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from PySide6.QtWidgets import QMessageBox

from core.domain.services.quiz_service import QuizQuestionSnapshot
from core.utils.constants import QuizMode
from ui.views import quiz_runner_view as runner_module
from ui.views.quiz_runner_view import QuizRunnerView


def test_on_time_up_triggers_finalize(qtbot, monkeypatch) -> None:
    view = QuizRunnerView()
    qtbot.addWidget(view)

    calls: list[bool] = []

    def _fake_finalize(*, time_up: bool) -> None:
        calls.append(time_up)

    monkeypatch.setattr(view, "_finalize_session", _fake_finalize)
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)

    view._on_time_up()

    assert calls == [True]


def test_submit_incomplete_cancel_does_not_finalize(qtbot, monkeypatch) -> None:
    view = QuizRunnerView()
    qtbot.addWidget(view)

    view._quiz_questions = [
        QuizQuestionSnapshot(quiz_question_id=1, order=1, content="Q1", type="MC"),
        QuizQuestionSnapshot(quiz_question_id=2, order=2, content="Q2", type="MC"),
    ]
    view._answers = {1: {"selected": "A"}}

    finalized: list[bool] = []
    monkeypatch.setattr(view, "_finalize_session", lambda *, time_up: finalized.append(time_up))
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.StandardButton.No)

    view._on_submit_clicked()

    assert finalized == []


def test_submit_incomplete_confirm_finalizes(qtbot, monkeypatch) -> None:
    view = QuizRunnerView()
    qtbot.addWidget(view)

    view._quiz_questions = [
        QuizQuestionSnapshot(quiz_question_id=1, order=1, content="Q1", type="MC"),
        QuizQuestionSnapshot(quiz_question_id=2, order=2, content="Q2", type="MC"),
    ]
    view._answers = {1: {"selected": "A"}}

    finalized: list[bool] = []
    monkeypatch.setattr(view, "_finalize_session", lambda *, time_up: finalized.append(time_up))
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.StandardButton.Yes)

    view._on_submit_clicked()

    assert finalized == [False]


def test_finalize_session_sets_time_up_status(qtbot, monkeypatch) -> None:
    view = QuizRunnerView()
    qtbot.addWidget(view)

    view._mode = QuizMode.PRACTICE.value
    view._attempt_id = 77
    view._quiz_title = "Quiz"
    view._submitter_name = ""
    view._submitter_id = ""
    view._started_at = datetime.now(timezone.utc)
    view._quiz_questions = [
        QuizQuestionSnapshot(quiz_question_id=1, order=1, content="Q1", type="MC")
    ]
    view._answers = {1: {"selected": "A"}}

    statuses: list[str] = []

    class _ControllerStub:
        def finalize_attempt(self, attempt_id, status, graded_rows, duration_seconds):
            statuses.append(status)

    view._runner_controller = _ControllerStub()
    monkeypatch.setattr(
        runner_module,
        "build_graded_result",
        lambda *args, **kwargs: ([], SimpleNamespace(duration_seconds=12)),
    )
    monkeypatch.setattr(view, "_show_non_exam_summary", lambda data: None)

    view._finalize_session(time_up=True)

    assert statuses == ["TIME_UP"]


def test_finalize_session_sets_submitted_status(qtbot, monkeypatch) -> None:
    view = QuizRunnerView()
    qtbot.addWidget(view)

    view._mode = QuizMode.PRACTICE.value
    view._attempt_id = 88
    view._quiz_title = "Quiz"
    view._submitter_name = ""
    view._submitter_id = ""
    view._started_at = datetime.now(timezone.utc)
    view._quiz_questions = [
        QuizQuestionSnapshot(quiz_question_id=1, order=1, content="Q1", type="MC")
    ]
    view._answers = {1: {"selected": "A"}}

    statuses: list[str] = []

    class _ControllerStub:
        def finalize_attempt(self, attempt_id, status, graded_rows, duration_seconds):
            statuses.append(status)

    view._runner_controller = _ControllerStub()
    monkeypatch.setattr(
        runner_module,
        "build_graded_result",
        lambda *args, **kwargs: ([], SimpleNamespace(duration_seconds=9)),
    )
    monkeypatch.setattr(view, "_show_non_exam_summary", lambda data: None)

    view._finalize_session(time_up=False)

    assert statuses == ["SUBMITTED"]
