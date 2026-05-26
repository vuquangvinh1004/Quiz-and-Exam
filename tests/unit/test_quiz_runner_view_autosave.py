"""Unit tests for autosave paths in QuizRunnerView.

PR-10 hardening: cover skip conditions and failure logging branch.
"""
from __future__ import annotations

from ui.views import quiz_runner_view as runner_module
from ui.views.quiz_runner_view import QuizRunnerView


class _ControllerOK:
    def __init__(self) -> None:
        self.calls: list[tuple[int, dict[int, dict]]] = []

    def autosave_answers(self, attempt_id: int, answers: dict[int, dict]) -> None:
        self.calls.append((attempt_id, answers))


class _ControllerFail:
    def autosave_answers(self, attempt_id: int, answers: dict[int, dict]) -> None:
        raise RuntimeError("db unavailable")


class _LoggerSpy:
    def __init__(self) -> None:
        self.debug_messages: list[str] = []
        self.warning_messages: list[str] = []

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


def test_autosave_skips_when_answers_empty(qtbot) -> None:
    view = QuizRunnerView()
    qtbot.addWidget(view)

    controller = _ControllerOK()
    view._runner_controller = controller
    view._attempt_id = 123
    view._answers = {}

    view._autosave()

    assert controller.calls == []


def test_autosave_logs_warning_on_failure(qtbot, monkeypatch) -> None:
    view = QuizRunnerView()
    qtbot.addWidget(view)

    logger_spy = _LoggerSpy()
    monkeypatch.setattr(runner_module, "logger", logger_spy)

    view._runner_controller = _ControllerFail()
    view._attempt_id = 456
    view._answers = {10: {"selected": "A"}}

    view._autosave()

    assert any("Autosave failed" in msg for msg in logger_spy.warning_messages)
