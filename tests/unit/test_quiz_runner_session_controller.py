"""Unit tests for QuizRunnerSessionController.

Focuses on persistence orchestration behavior and fallback paths.
"""
from __future__ import annotations

from dataclasses import dataclass

from core.domain.services.quiz_service import GradedRow, QuizInfoDTO, QuizQuestionSnapshot
from core.domain.services.submission_service import SubmissionSettings
from modules.quiz_runner import session_controller as controller_module
from modules.quiz_runner.session_controller import QuizRunnerSessionController


class _Ctx:
    def __init__(self, session):
        self._session = session

    def __enter__(self):
        return self._session

    def __exit__(self, exc_type, exc, tb):
        return False


@dataclass
class _Question:
    id: int
    question_code: str | None


class _QQ:
    def __init__(self, qid: int, question_id: int) -> None:
        self.id = qid
        self.question_id = question_id
        self.question_order = 1
        self.snapshot_content = "Question content"
        self.snapshot_type = "MC"
        self.snapshot_hint = None
        self.snapshot_explanation = None
        self.snapshot_point_value = 1.0

    def get_snapshot_options(self):
        return [{"key": "A", "text": "Option A", "is_correct": True}]

    def get_snapshot_accepted_answers(self):
        return []

    def get_snapshot_answer_config(self):
        return {"case_sensitive": False, "trim_whitespace": True}


@dataclass
class _Attempt:
    id: int


class _Session:
    def __init__(self, code_map: dict[int, str | None] | None = None):
        self._code_map = code_map or {}

    def get(self, _model, question_id: int):
        if question_id not in self._code_map:
            return None
        return _Question(question_id, self._code_map[question_id])


class _QuizServiceSpy:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def get_quiz_info(self, session, quiz_id):
        self.calls.append(("get_quiz_info", session, quiz_id))
        return QuizInfoDTO(title="Quiz 1", mode="EXAM", time_limit=30, total=20)

    def get_quiz_questions(self, session, quiz_id):
        self.calls.append(("get_quiz_questions", session, quiz_id))
        return [_QQ(10, 100)]

    def create_attempt(self, session, quiz_id):
        self.calls.append(("create_attempt", session, quiz_id))
        return _Attempt(999)

    def autosave_answers(self, session, attempt_id, answers):
        self.calls.append(("autosave_answers", session, attempt_id, answers))

    def finalize_attempt(self, session, attempt_id, status, graded_rows, duration_seconds):
        self.calls.append(
            ("finalize_attempt", session, attempt_id, status, graded_rows, duration_seconds)
        )


def test_load_quiz_info_success(monkeypatch):
    svc = _QuizServiceSpy()
    ctl = QuizRunnerSessionController(svc)

    monkeypatch.setattr(controller_module, "get_session", lambda: _Ctx(_Session()))

    info = ctl.load_quiz_info(42)

    assert isinstance(info, QuizInfoDTO)
    assert info.title == "Quiz 1"
    assert info.mode == "EXAM"
    assert info.time_limit == 30
    assert info.total == 20


def test_load_quiz_info_returns_none_on_error(monkeypatch):
    svc = _QuizServiceSpy()
    ctl = QuizRunnerSessionController(svc)

    def _boom():
        raise RuntimeError("db down")

    monkeypatch.setattr(controller_module, "get_session", _boom)

    assert ctl.load_quiz_info(1) is None


def test_prepare_attempt_builds_snapshot_and_attempt(monkeypatch):
    svc = _QuizServiceSpy()
    ctl = QuizRunnerSessionController(svc)

    monkeypatch.setattr(
        controller_module,
        "get_session",
        lambda: _Ctx(_Session({100: "Q100"})),
    )

    questions, attempt_id = ctl.prepare_attempt(12)

    assert attempt_id == 999
    assert len(questions) == 1
    q = questions[0]
    assert isinstance(q, QuizQuestionSnapshot)
    assert q.quiz_question_id == 10
    assert q.question_code == "Q100"
    assert q.type == "MC"
    assert q.order == 1


def test_autosave_answers_skips_empty_payload(monkeypatch):
    svc = _QuizServiceSpy()
    ctl = QuizRunnerSessionController(svc)

    monkeypatch.setattr(controller_module, "get_session", lambda: _Ctx(_Session()))

    ctl.autosave_answers(1, {})

    assert all(call[0] != "autosave_answers" for call in svc.calls)


def test_autosave_answers_calls_service(monkeypatch):
    svc = _QuizServiceSpy()
    ctl = QuizRunnerSessionController(svc)

    monkeypatch.setattr(controller_module, "get_session", lambda: _Ctx(_Session()))

    answers = {10: {"selected": "A"}}
    ctl.autosave_answers(5, answers)

    autosave_calls = [c for c in svc.calls if c[0] == "autosave_answers"]
    assert len(autosave_calls) == 1
    assert autosave_calls[0][2] == 5
    assert autosave_calls[0][3] == answers


def test_finalize_attempt_calls_service(monkeypatch):
    svc = _QuizServiceSpy()
    ctl = QuizRunnerSessionController(svc)

    monkeypatch.setattr(controller_module, "get_session", lambda: _Ctx(_Session()))

    rows = [
        GradedRow(
            quiz_question_id=10,
            answer_payload={"selected": "A"},
            is_correct=True,
            score_awarded=1.0,
            feedback_state="correct",
        )
    ]
    ctl.finalize_attempt(7, "SUBMITTED", rows, 55)

    calls = [c for c in svc.calls if c[0] == "finalize_attempt"]
    assert len(calls) == 1
    assert calls[0][2] == 7
    assert calls[0][3] == "SUBMITTED"
    assert calls[0][5] == 55


def test_load_submission_settings_success(monkeypatch):
    class _SubmissionService:
        def load_settings(self, _session):
            return SubmissionSettings(mode="both", default_email="teacher@example.com")

    monkeypatch.setattr(controller_module, "get_session", lambda: _Ctx(_Session()))

    cfg = QuizRunnerSessionController.load_submission_settings(_SubmissionService())

    assert cfg.mode == "both"
    assert cfg.default_email == "teacher@example.com"


def test_load_submission_settings_fallback(monkeypatch):
    class _SubmissionService:
        def load_settings(self, _session):
            raise RuntimeError("broken")

    monkeypatch.setattr(controller_module, "get_session", lambda: _Ctx(_Session()))

    cfg = QuizRunnerSessionController.load_submission_settings(_SubmissionService())

    assert isinstance(cfg, SubmissionSettings)
    assert cfg.mode == "none"
