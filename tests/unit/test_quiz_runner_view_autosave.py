"""Unit tests for autosave paths in QuizRunnerView.

PR-10 hardening: cover skip conditions and failure logging branch.
"""
from __future__ import annotations

from ui.views import quiz_runner_view as runner_module
from ui.views.quiz_runner_view import QuizRunnerView


class _ControllerOK:
    def __init__(self) -> None:
        self.calls: list[tuple[int, dict[int, dict], int | None]] = []

    def autosave_progress(
        self,
        attempt_id: int,
        answers: dict[int, dict],
        remaining_seconds: int | None,
    ) -> None:
        self.calls.append((attempt_id, answers, remaining_seconds))


class _ControllerFail:
    def autosave_progress(
        self,
        attempt_id: int,
        answers: dict[int, dict],
        remaining_seconds: int | None,
    ) -> None:
        raise RuntimeError("db unavailable")


class _LoggerSpy:
    def __init__(self) -> None:
        self.info_messages: list[str] = []
        self.debug_messages: list[str] = []
        self.warning_messages: list[str] = []

    def info(self, msg: str) -> None:
        self.info_messages.append(msg)

    def debug(self, msg: str) -> None:
        self.debug_messages.append(msg)

    def warning(self, msg: str) -> None:
        self.warning_messages.append(msg)


def test_autosave_skips_when_attempt_missing(qtbot) -> None:
    view = QuizRunnerView()
    qtbot.addWidget(view)

    controller = _ControllerOK()
    view._runner_controller = controller
    view._attempt_id = None
    view._answers = {10: {"selected": "A"}}

    view._autosave()

    assert controller.calls == []


def test_autosave_persists_timer_state_without_answers(qtbot) -> None:
    view = QuizRunnerView()
    qtbot.addWidget(view)

    controller = _ControllerOK()
    view._runner_controller = controller
    view._attempt_id = 123
    view._answers = {}
    view._remaining_seconds = 410

    view._autosave()

    assert controller.calls == [(123, {}, 410)]


def test_autosave_saves_current_answer_before_persist(qtbot, monkeypatch) -> None:
    view = QuizRunnerView()
    qtbot.addWidget(view)

    controller = _ControllerOK()
    view._runner_controller = controller
    view._attempt_id = 222
    view._remaining_seconds = 300
    view._quiz_questions = [
        runner_module.QuizQuestionSnapshot(quiz_question_id=10, order=1, content="Q1", type="MC")
    ]
    monkeypatch.setattr(view, "_get_current_payload", lambda: {"selected": "B"})

    view._autosave()

    assert view._answers == {10: {"selected": "B"}}
    assert controller.calls == [(222, {10: {"selected": "B"}}, 300)]


def test_autosave_logs_warning_on_failure(qtbot, monkeypatch) -> None:
    view = QuizRunnerView()
    qtbot.addWidget(view)

    logger_spy = _LoggerSpy()
    monkeypatch.setattr(runner_module, "logger", logger_spy)

    view._runner_controller = _ControllerFail()
    view._attempt_id = 456
    view._answers = {10: {"selected": "A"}}

    view._autosave()

    assert any("event=autosave_failed" in msg for msg in logger_spy.info_messages)
    assert any("event=autosave_error_detail" in msg for msg in logger_spy.info_messages)
