from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from PySide6.QtWidgets import QMessageBox

from core.domain.services.quiz_service import QuizInfoDTO, QuizQuestionSnapshot
from core.utils.constants import QuizMode
from modules.quiz_runner.session_controller import PreparedAttemptSession
from ui.views import quiz_runner_view as runner_module
from ui.views.quiz_runner_view import QuizRunnerView


class _LoggerSpy:
    def __init__(self) -> None:
        self.info_messages: list[str] = []
        self.error_messages: list[str] = []

    def info(self, msg: str) -> None:
        self.info_messages.append(msg)

    def error(self, msg: str) -> None:
        self.error_messages.append(msg)


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
    view._started_at = datetime.now(UTC)
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
    view._started_at = datetime.now(UTC)
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


def test_finalize_session_failure_keeps_attempt_recoverable(qtbot, monkeypatch) -> None:
    view = QuizRunnerView()
    qtbot.addWidget(view)

    view._mode = QuizMode.PRACTICE.value
    view._attempt_id = 91
    view._quiz_title = "Quiz"
    view._submitter_name = ""
    view._submitter_id = ""
    view._started_at = datetime.now(UTC)
    view._remaining_seconds = 180
    view._quiz_questions = [
        QuizQuestionSnapshot(quiz_question_id=1, order=1, content="Q1", type="MC")
    ]
    view._answers = {1: {"selected": "A"}}

    events: list[tuple] = []

    class _ControllerStub:
        def autosave_progress(self, attempt_id, answers, remaining_seconds):
            events.append(("autosave", attempt_id, answers, remaining_seconds))

        def finalize_attempt(self, attempt_id, status, graded_rows, duration_seconds):
            raise RuntimeError("db locked")

    view._runner_controller = _ControllerStub()
    monkeypatch.setattr(view, "_save_current_answer", lambda: None)
    monkeypatch.setattr(
        runner_module,
        "build_graded_result",
        lambda *args, **kwargs: ([], SimpleNamespace(duration_seconds=9)),
    )
    critical_calls: list[str] = []
    monkeypatch.setattr(
        QMessageBox,
        "critical",
        lambda *args, **kwargs: critical_calls.append("critical"),
    )

    view._finalize_session(time_up=False)

    assert events == [("autosave", 91, {1: {"selected": "A"}}, 180)]
    assert critical_calls == ["critical"]
    assert view._finalizing is False
    assert view._autosave_timer.isActive() is True
    assert view._stack.currentIndex() == 0


def test_exam_time_up_finalize_failure_locks_answers_and_allows_retry(qtbot, monkeypatch) -> None:
    view = QuizRunnerView()
    qtbot.addWidget(view)

    view._mode = QuizMode.EXAM.value
    view._attempt_id = 92
    view._quiz_title = "Quiz Exam"
    view._submitter_name = "Nguyen Van A"
    view._submitter_id = "SV001"
    view._started_at = datetime.now(UTC)
    view._remaining_seconds = 0
    view._quiz_questions = [
        QuizQuestionSnapshot(quiz_question_id=1, order=1, content="Q1", type="MC")
    ]
    view._answers = {1: {"selected": "A"}}

    class _ControllerStub:
        def autosave_progress(self, attempt_id, answers, remaining_seconds):
            return None

        def finalize_attempt(self, attempt_id, status, graded_rows, duration_seconds):
            raise RuntimeError("db locked")

    view._runner_controller = _ControllerStub()
    monkeypatch.setattr(view, "_save_current_answer", lambda: None)
    monkeypatch.setattr(
        runner_module,
        "build_graded_result",
        lambda *args, **kwargs: ([], SimpleNamespace(duration_seconds=60)),
    )
    critical_calls: list[str] = []
    monkeypatch.setattr(
        QMessageBox,
        "critical",
        lambda *args, **kwargs: critical_calls.append("critical"),
    )

    view._finalize_session(time_up=True)

    assert critical_calls == ["critical"]
    assert view._retry_submit_only is True
    assert view._submit_btn.text() == "Thử nộp lại"
    assert view._autosave_timer.isActive() is False
    assert view._next_btn.isEnabled() is False
    assert view._prev_btn.isEnabled() is False


def test_update_running_header_shows_resume_badge(qtbot) -> None:
    view = QuizRunnerView()
    qtbot.addWidget(view)

    view._mode = QuizMode.PRACTICE.value
    view._quiz_title = "Quiz Resume"
    view._resumed_from_autosave = True

    view._update_running_header()

    assert view._resume_badge.isHidden() is False
    assert "Quiz Resume" in view._header_title.text()


def test_resolve_runtime_session_prefers_resumable_attempt(qtbot, monkeypatch) -> None:
    view = QuizRunnerView()
    qtbot.addWidget(view)

    resumed = PreparedAttemptSession(
        snapshots=[QuizQuestionSnapshot(quiz_question_id=1, order=1, content="Q1", type="MC")],
        attempt_id=222,
        answers={1: {"selected": "A"}},
        started_at=datetime.now(UTC),
        remaining_seconds=480,
        submitter_name="Nguyen Van A",
        submitter_id="SV001",
        resumed=True,
    )
    view._pending_quiz_id = 10
    view._mode = QuizMode.EXAM.value

    class _ControllerStub:
        def load_resumable_attempt(self, quiz_id):
            assert quiz_id == 10
            return resumed

    view._runner_controller = _ControllerStub()
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.StandardButton.Yes)

    runtime = view._resolve_runtime_session("Quiz")

    assert runtime is resumed


def test_resolve_runtime_session_rejects_invalid_exam_resume(qtbot, monkeypatch) -> None:
    view = QuizRunnerView()
    qtbot.addWidget(view)

    resumed = PreparedAttemptSession(
        snapshots=[],
        attempt_id=223,
        answers={1: {"selected": "A"}},
        started_at=datetime.now(UTC),
        remaining_seconds=480,
        submitter_name="",
        submitter_id="",
        resumed=True,
    )
    prepared = PreparedAttemptSession(
        snapshots=[QuizQuestionSnapshot(quiz_question_id=3, order=1, content="Q3", type="MC")],
        attempt_id=224,
        answers={},
        started_at=datetime.now(UTC),
        remaining_seconds=600,
        resumed=False,
    )
    view._pending_quiz_id = 11
    view._mode = QuizMode.EXAM.value
    view._quiz_info = QuizInfoDTO(title="Quiz", mode=QuizMode.EXAM.value, time_limit=10, total=1)

    deleted_ids: list[int] = []

    class _DialogStub:
        submitter_name = "Nguyen Van A"
        submitter_id = "SV001"

        def __init__(self, *args, **kwargs) -> None:
            pass

        def exec(self):
            return runner_module.QDialog.DialogCode.Accepted

    class _ControllerStub:
        def load_resumable_attempt(self, quiz_id):
            return resumed

        def delete_attempt(self, attempt_id):
            deleted_ids.append(attempt_id)
            return True

        def prepare_attempt(self, quiz_id, **kwargs):
            return prepared

    view._runner_controller = _ControllerStub()
    monkeypatch.setattr(runner_module, "SubmitterInfoDialog", _DialogStub)
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)

    runtime = view._resolve_runtime_session("Quiz")

    assert deleted_ids == [223]
    assert runtime is prepared


def test_resolve_runtime_session_discards_old_attempt_before_restart(qtbot, monkeypatch) -> None:
    view = QuizRunnerView()
    qtbot.addWidget(view)

    resumed = PreparedAttemptSession(
        snapshots=[],
        attempt_id=333,
        answers={},
        started_at=datetime.now(UTC),
        remaining_seconds=300,
        resumed=True,
    )
    prepared = PreparedAttemptSession(
        snapshots=[QuizQuestionSnapshot(quiz_question_id=2, order=1, content="Q2", type="MC")],
        attempt_id=444,
        answers={},
        started_at=datetime.now(UTC),
        remaining_seconds=600,
        resumed=False,
    )
    view._pending_quiz_id = 12
    view._mode = QuizMode.PRACTICE.value
    view._quiz_info = QuizInfoDTO(title="Quiz", mode=QuizMode.PRACTICE.value, time_limit=10, total=1)

    deleted_ids: list[int] = []

    class _ControllerStub:
        def load_resumable_attempt(self, quiz_id):
            assert quiz_id == 12
            return resumed

        def delete_attempt(self, attempt_id):
            deleted_ids.append(attempt_id)
            return True

        def prepare_attempt(self, quiz_id, **kwargs):
            assert quiz_id == 12
            assert kwargs["submitter_name"] == ""
            assert kwargs["submitter_id"] == ""
            return prepared

    view._runner_controller = _ControllerStub()
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.StandardButton.No)

    runtime = view._resolve_runtime_session("Quiz")

    assert deleted_ids == [333]
    assert runtime is prepared


def test_runtime_logs_resume_accept_and_finalize_retry(qtbot, monkeypatch) -> None:
    view = QuizRunnerView()
    qtbot.addWidget(view)

    logger_spy = _LoggerSpy()
    monkeypatch.setattr(runner_module, "logger", logger_spy)

    resumed = PreparedAttemptSession(
        snapshots=[QuizQuestionSnapshot(quiz_question_id=1, order=1, content="Q1", type="MC")],
        attempt_id=555,
        answers={1: {"selected": "A"}},
        started_at=datetime.now(UTC),
        remaining_seconds=300,
        submitter_name="Nguyen Van A",
        submitter_id="SV001",
        resumed=True,
    )
    view._pending_quiz_id = 10
    view._mode = QuizMode.EXAM.value

    class _ControllerStub:
        def load_resumable_attempt(self, quiz_id):
            return resumed

    view._runner_controller = _ControllerStub()
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.StandardButton.Yes)

    runtime = view._resolve_runtime_session("Quiz")
    view._attempt_id = runtime.attempt_id
    view._mode = QuizMode.EXAM.value
    view._remaining_seconds = 0
    view._quiz_questions = runtime.snapshots
    view._answers = runtime.answers

    view._recover_after_finalize_failure(time_up=True)

    assert any("event=resume_accepted" in msg for msg in logger_spy.info_messages)
    assert any("event=finalize_retry_ready" in msg for msg in logger_spy.info_messages)
