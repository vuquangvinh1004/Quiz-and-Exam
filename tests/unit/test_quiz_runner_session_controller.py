"""Unit tests for QuizRunnerSessionController.

Focuses on persistence orchestration behavior and fallback paths.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from core.domain.services.quiz_service import (
    AttemptResumeDTO,
    GradedRow,
    QuizInfoDTO,
    QuizQuestionSnapshot,
)
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

    def create_attempt(self, session, quiz_id, **kwargs):
        self.calls.append(("create_attempt", session, quiz_id, kwargs))
        attempt = _Attempt(999)
        attempt.started_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
        return attempt

    def get_resumable_attempt(self, session, quiz_id):
        self.calls.append(("get_resumable_attempt", session, quiz_id))
        return None

    def autosave_progress(self, session, attempt_id, answers, remaining_seconds):
        self.calls.append(
            ("autosave_progress", session, attempt_id, answers, remaining_seconds)
        )

    def finalize_attempt(self, session, attempt_id, status, graded_rows, duration_seconds):
        self.calls.append(
            ("finalize_attempt", session, attempt_id, status, graded_rows, duration_seconds)
        )

    def delete_attempt(self, session, attempt_id):
        self.calls.append(("delete_attempt", session, attempt_id))
        return True


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

    prepared = ctl.prepare_attempt(12, submitter_name="A", submitter_id="B", remaining_seconds=600)

    assert prepared.attempt_id == 999
    assert prepared.remaining_seconds == 600
    assert prepared.submitter_name == "A"
    assert prepared.submitter_id == "B"
    assert len(prepared.snapshots) == 1
    q = prepared.snapshots[0]
    assert isinstance(q, QuizQuestionSnapshot)
    assert q.quiz_question_id == 10
    assert q.question_code == "Q100"
    assert q.type == "MC"
    assert q.order == 1


def test_load_resumable_attempt_returns_runtime_bundle(monkeypatch):
    svc = _QuizServiceSpy()
    ctl = QuizRunnerSessionController(svc)

    svc.get_resumable_attempt = lambda session, quiz_id: AttemptResumeDTO(
        attempt_id=321,
        quiz_id=quiz_id,
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        remaining_seconds=455,
        submitter_name="Tran Van C",
        submitter_id="HS009",
        answers={10: {"selected": "A"}},
    )

    monkeypatch.setattr(
        controller_module,
        "get_session",
        lambda: _Ctx(_Session({100: "Q100"})),
    )

    prepared = ctl.load_resumable_attempt(12)

    assert prepared is not None
    assert prepared.resumed is True
    assert prepared.attempt_id == 321
    assert prepared.remaining_seconds == 455
    assert prepared.submitter_name == "Tran Van C"
    assert prepared.answers == {10: {"selected": "A"}}


def test_autosave_progress_skips_when_nothing_to_save(monkeypatch):
    svc = _QuizServiceSpy()
    ctl = QuizRunnerSessionController(svc)

    monkeypatch.setattr(controller_module, "get_session", lambda: _Ctx(_Session()))

    ctl.autosave_progress(1, {}, None)

    assert all(call[0] != "autosave_progress" for call in svc.calls)


def test_autosave_progress_calls_service(monkeypatch):
    svc = _QuizServiceSpy()
    ctl = QuizRunnerSessionController(svc)

    monkeypatch.setattr(controller_module, "get_session", lambda: _Ctx(_Session()))

    answers = {10: {"selected": "A"}}
    ctl.autosave_progress(5, answers, 123)

    autosave_calls = [c for c in svc.calls if c[0] == "autosave_progress"]
    assert len(autosave_calls) == 1
    assert autosave_calls[0][2] == 5
    assert autosave_calls[0][3] == answers
    assert autosave_calls[0][4] == 123


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


def test_delete_attempt_calls_service(monkeypatch):
    svc = _QuizServiceSpy()
    ctl = QuizRunnerSessionController(svc)

    monkeypatch.setattr(controller_module, "get_session", lambda: _Ctx(_Session()))

    deleted = ctl.delete_attempt(77)

    assert deleted is True
    calls = [c for c in svc.calls if c[0] == "delete_attempt"]
    assert calls == [("delete_attempt", calls[0][1], 77)]


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
