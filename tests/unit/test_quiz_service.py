"""Tests for QuizService and QuestionSelector (Phase 4).

Covers:
  - QuizConfig validation (EXAM/PRACTICE/STUDY rules)
  - create_quiz: Quiz + QuizQuestion rows, BLANK/SA snapshot encoding
  - create_attempt: Attempt created + AttemptAnswer pre-populated
  - save_answer: upsert new + update existing
  - autosave_answers: batch upsert
  - finalize_attempt: result stats, status update
  - grade_answer_from_dict: MC, MA, BLANK, SA grading (correct / wrong / case)
  - QuestionSelector.select: filters, count cap, deterministic when shuffle=False
  - QuestionSelector.available_count: matches filter logic
  - QuestionSelector.build_snapshots: option + accepted_answers structure
"""
from __future__ import annotations

import json
import pytest

from core.database.models import (
    Attempt,
    AttemptAnswer,
    Question,
    QuestionBank,
    QuestionOption,
    Quiz,
    QuizQuestion,
)
from core.domain.services.quiz_service import (
    GradedRow,
    QuizConfig,
    QuizCreationSnapshot,
    QuizInfoDTO,
    QuizService,
)
from core.utils.constants import AttemptStatus, QuizMode
from modules.quiz_builder.selector import QuestionSelector

# ---------------------------------------------------------------------------
# Helpers / shared data
# ---------------------------------------------------------------------------

def _make_bank(session, name="Test Bank"):
    bank = QuestionBank(name=name)
    session.add(bank)
    session.flush()
    return bank


def _make_mc_question(session, bank_id, content="Q?", code=None):
    q = Question(
        bank_id=bank_id,
        question_type="MC",
        content=content,
        question_code=code,
        point_value=1.0,
        is_active=True,
    )
    session.add(q)
    session.flush()
    opts = [
        QuestionOption(question_id=q.id, option_key="A", option_text="Opt A", is_correct=True, sort_order=1),
        QuestionOption(question_id=q.id, option_key="B", option_text="Opt B", is_correct=False, sort_order=2),
        QuestionOption(question_id=q.id, option_key="C", option_text="Opt C", is_correct=False, sort_order=3),
    ]
    session.add_all(opts)
    session.flush()
    return q


def _make_ma_question(session, bank_id, content="Choose all correct.", code=None):
    q = Question(
        bank_id=bank_id,
        question_type="MA",
        content=content,
        question_code=code,
        point_value=2.0,
        is_active=True,
    )
    session.add(q)
    session.flush()
    opts = [
        QuestionOption(question_id=q.id, option_key="A", option_text="Aa", is_correct=True, sort_order=1),
        QuestionOption(question_id=q.id, option_key="B", option_text="Bb", is_correct=True, sort_order=2),
        QuestionOption(question_id=q.id, option_key="C", option_text="Cc", is_correct=False, sort_order=3),
    ]
    session.add_all(opts)
    session.flush()
    return q


def _make_blank_question(session, bank_id, answers=None, case_sensitive=False, code=None):
    q = Question(
        bank_id=bank_id,
        question_type="BLANK",
        content="The capital of France is [[blank]].",
        question_code=code,
        point_value=1.0,
        is_active=True,
        case_sensitive=case_sensitive,
        trim_whitespace=True,
    )
    q.set_accepted_answers(answers or ["Paris", "paris"])
    session.add(q)
    session.flush()
    return q


def _make_sa_question(session, bank_id, answers=None, code=None):
    q = Question(
        bank_id=bank_id,
        question_type="SA",
        content="Name the planet closest to the Sun.",
        question_code=code,
        point_value=1.0,
        is_active=True,
        case_sensitive=False,
        trim_whitespace=True,
    )
    q.set_accepted_answers(answers or ["Mercury"])
    session.add(q)
    session.flush()
    return q


def _mc_snapshot(question_id: int = 1):
    return {
        "question_id": question_id,
        "content": "Sample question?",
        "type": "MC",
        "hint": "",
        "explanation": "",
        "point_value": 1.0,
        "options": [
            {"key": "A", "text": "Paris", "is_correct": True},
            {"key": "B", "text": "London", "is_correct": False},
        ],
        "accepted_answers": [],
        "case_sensitive": False,
        "trim_whitespace": True,
    }


def _blank_snapshot(case_sensitive=False, question_id: int = 1):
    return {
        "question_id": question_id,
        "content": "The capital is [[blank]].",
        "type": "BLANK",
        "hint": "",
        "explanation": "",
        "point_value": 1.0,
        "options": [],
        "accepted_answers": ["Paris", "paris"],
        "case_sensitive": case_sensitive,
        "trim_whitespace": True,
    }


def _full_snapshots_for_quiz(session, bank_id):
    """Return two snapshot dicts (1 MC + 1 BLANK) for create_quiz tests."""
    mc = _make_mc_question(session, bank_id)
    bl = _make_blank_question(session, bank_id)
    sel = QuestionSelector()
    mc_snap = sel.build_snapshots([mc], shuffle_options=False)[0]
    bl_snap = sel.build_snapshots([bl], shuffle_options=False)[0]
    return [mc_snap, bl_snap]


# ---------------------------------------------------------------------------
# QuizConfig validation
# ---------------------------------------------------------------------------

class TestValidateConfig:
    """_validate_config is called inside create_quiz; test via create_quiz."""

    def test_empty_title_raises(self, db_session):
        bank = _make_bank(db_session)
        cfg = QuizConfig(title="  ", bank_id=bank.id, mode="EXAM", time_limit_minutes=30, question_count=1)
        with pytest.raises(ValueError, match="Tên bài kiểm tra"):
            QuizService().create_quiz(db_session, cfg, [_mc_snapshot()])

    def test_exam_without_time_limit_raises(self, db_session):
        bank = _make_bank(db_session)
        cfg = QuizConfig(title="T", bank_id=bank.id, mode="EXAM", time_limit_minutes=None, question_count=1)
        with pytest.raises(ValueError, match="Kiểm tra"):
            QuizService().create_quiz(db_session, cfg, [_mc_snapshot()])

    def test_practice_without_time_limit_raises(self, db_session):
        bank = _make_bank(db_session)
        cfg = QuizConfig(title="T", bank_id=bank.id, mode="PRACTICE", time_limit_minutes=0, question_count=1)
        with pytest.raises(ValueError, match="Luyện tập"):
            QuizService().create_quiz(db_session, cfg, [_mc_snapshot()])

    def test_study_with_time_limit_is_allowed(self, db_session):
        """Architecture says STUDY has no timer, but service only enforces EXAM/PRACTICE.
        STUDY with time_limit_minutes set should NOT raise at service layer."""
        bank = _make_bank(db_session)
        cfg = QuizConfig(title="T", bank_id=bank.id, mode="STUDY", time_limit_minutes=None, question_count=1)
        quiz = QuizService().create_quiz(db_session, cfg, [_mc_snapshot()])
        assert quiz.id is not None

    def test_zero_questions_raises(self, db_session):
        bank = _make_bank(db_session)
        cfg = QuizConfig(title="T", bank_id=bank.id, mode="EXAM", time_limit_minutes=10, question_count=1)
        with pytest.raises(ValueError, match="ít nhất 1"):
            QuizService().create_quiz(db_session, cfg, [])

    def test_invalid_mode_raises(self, db_session):
        bank = _make_bank(db_session)
        cfg = QuizConfig(title="T", bank_id=bank.id, mode="INVALID", time_limit_minutes=None, question_count=1)
        with pytest.raises(ValueError, match="Mode"):
            QuizService().create_quiz(db_session, cfg, [_mc_snapshot()])


# ---------------------------------------------------------------------------
# create_quiz
# ---------------------------------------------------------------------------

class TestCreateQuiz:

    def test_creates_quiz_and_quiz_questions(self, db_session):
        bank = _make_bank(db_session)
        snaps = _full_snapshots_for_quiz(db_session, bank.id)
        cfg = QuizConfig(title="Quiz 1", bank_id=bank.id, mode="EXAM", time_limit_minutes=30, question_count=2)
        quiz = QuizService().create_quiz(db_session, cfg, snaps)

        assert quiz.id is not None
        assert quiz.title == "Quiz 1"
        assert quiz.mode == "EXAM"
        assert quiz.total_questions == 2

        qq_rows = db_session.query(QuizQuestion).filter_by(quiz_id=quiz.id).all()
        assert len(qq_rows) == 2

    def test_create_quiz_accepts_typed_creation_snapshots(self, db_session):
        bank = _make_bank(db_session)
        snaps = _full_snapshots_for_quiz(db_session, bank.id)
        typed = [QuizCreationSnapshot.from_dict(s) for s in snaps]

        cfg = QuizConfig(
            title="Quiz Typed",
            bank_id=bank.id,
            mode="EXAM",
            time_limit_minutes=30,
            question_count=2,
        )
        quiz = QuizService().create_quiz(db_session, cfg, typed)

        assert quiz.id is not None
        assert quiz.total_questions == 2

    def test_question_order_starts_at_1(self, db_session):
        bank = _make_bank(db_session)
        snaps = _full_snapshots_for_quiz(db_session, bank.id)
        cfg = QuizConfig(title="Q", bank_id=bank.id, mode="EXAM", time_limit_minutes=10, question_count=2)
        quiz = QuizService().create_quiz(db_session, cfg, snaps)
        orders = sorted(q.question_order for q in quiz.quiz_questions)
        assert orders == [1, 2]

    def test_blank_snapshot_encodes_answer_config(self, db_session):
        bank = _make_bank(db_session)
        bl_q = _make_blank_question(db_session, bank.id, answers=["Paris"], case_sensitive=True)
        sel = QuestionSelector()
        snap = sel.build_snapshots([bl_q], shuffle_options=False)[0]
        cfg = QuizConfig(title="B", bank_id=bank.id, mode="STUDY", time_limit_minutes=None, question_count=1)
        quiz = QuizService().create_quiz(db_session, cfg, [snap])

        qq = quiz.quiz_questions[0]
        raw = json.loads(qq.snapshot_accepted_answers)
        assert raw["answers"] == ["Paris"]
        assert raw["case_sensitive"] is True
        assert raw["trim_whitespace"] is True

    def test_mc_snapshot_options_stored_as_json(self, db_session):
        bank = _make_bank(db_session)
        mc_q = _make_mc_question(db_session, bank.id)
        sel = QuestionSelector()
        snap = sel.build_snapshots([mc_q], shuffle_options=False)[0]
        cfg = QuizConfig(title="M", bank_id=bank.id, mode="EXAM", time_limit_minutes=5, question_count=1)
        quiz = QuizService().create_quiz(db_session, cfg, [snap])

        qq = quiz.quiz_questions[0]
        opts = json.loads(qq.snapshot_options)
        assert any(o["key"] == "A" and o["is_correct"] is True for o in opts)

    def test_mc_snapshot_accepted_answers_is_null(self, db_session):
        bank = _make_bank(db_session)
        mc_q = _make_mc_question(db_session, bank.id)
        sel = QuestionSelector()
        snap = sel.build_snapshots([mc_q], shuffle_options=False)[0]
        cfg = QuizConfig(title="M", bank_id=bank.id, mode="EXAM", time_limit_minutes=5, question_count=1)
        quiz = QuizService().create_quiz(db_session, cfg, [snap])
        qq = quiz.quiz_questions[0]
        # For MC, snapshot_accepted_answers should be NULL (no accepted_answers list)
        assert qq.snapshot_accepted_answers is None


# ---------------------------------------------------------------------------
# create_attempt
# ---------------------------------------------------------------------------

class TestCreateAttempt:

    def _make_quiz(self, session, bank_id):
        snaps = _full_snapshots_for_quiz(session, bank_id)
        cfg = QuizConfig(title="A", bank_id=bank_id, mode="EXAM", time_limit_minutes=10, question_count=2)
        return QuizService().create_quiz(session, cfg, snaps)

    def test_creates_attempt_with_correct_mode(self, db_session):
        bank = _make_bank(db_session)
        quiz = self._make_quiz(db_session, bank.id)
        attempt = QuizService().create_attempt(db_session, quiz.id)
        assert attempt.id is not None
        assert attempt.mode == "EXAM"
        assert attempt.status == AttemptStatus.IN_PROGRESS.value

    def test_pre_creates_attempt_answers(self, db_session):
        bank = _make_bank(db_session)
        quiz = self._make_quiz(db_session, bank.id)
        attempt = QuizService().create_attempt(db_session, quiz.id)
        aas = db_session.query(AttemptAnswer).filter_by(attempt_id=attempt.id).all()
        assert len(aas) == 2

    def test_attempt_answers_pre_populated_as_unanswered(self, db_session):
        bank = _make_bank(db_session)
        quiz = self._make_quiz(db_session, bank.id)
        attempt = QuizService().create_attempt(db_session, quiz.id)
        aas = db_session.query(AttemptAnswer).filter_by(attempt_id=attempt.id).all()
        assert all(not aa.is_answered for aa in aas)

    def test_max_score_calculated_from_snapshot_point_values(self, db_session):
        bank = _make_bank(db_session)
        mc = _make_mc_question(db_session, bank.id)    # point_value=1.0
        ma = _make_ma_question(db_session, bank.id)    # point_value=2.0
        sel = QuestionSelector()
        snaps = sel.build_snapshots([mc, ma], shuffle_options=False)
        cfg = QuizConfig(title="X", bank_id=bank.id, mode="EXAM", time_limit_minutes=10, question_count=2)
        quiz = QuizService().create_quiz(db_session, cfg, snaps)
        attempt = QuizService().create_attempt(db_session, quiz.id)
        assert attempt.max_score == pytest.approx(3.0)

    def test_create_attempt_invalid_quiz_raises(self, db_session):
        with pytest.raises(ValueError):
            QuizService().create_attempt(db_session, 9999)


class TestGetQuizInfo:

    def test_get_quiz_info_returns_dto(self, db_session):
        bank = _make_bank(db_session)
        mc_q = _make_mc_question(db_session, bank.id)
        sel = QuestionSelector()
        snap = sel.build_snapshots([mc_q], shuffle_options=False)[0]
        cfg = QuizConfig(
            title="Quiz DTO",
            bank_id=bank.id,
            mode=QuizMode.EXAM.value,
            time_limit_minutes=25,
            question_count=1,
        )
        quiz = QuizService().create_quiz(db_session, cfg, [snap])

        info = QuizService().get_quiz_info(db_session, quiz.id)

        assert isinstance(info, QuizInfoDTO)
        assert info.title == "Quiz DTO"
        assert info.mode == QuizMode.EXAM.value
        assert info.time_limit == 25
        assert info.total == 1

    def test_get_quiz_info_invalid_id_raises(self, db_session):
        with pytest.raises(ValueError):
            QuizService().get_quiz_info(db_session, 9999)


# ---------------------------------------------------------------------------
# save_answer / autosave_answers
# ---------------------------------------------------------------------------

class TestSaveAnswer:

    def _setup(self, db_session):
        bank = _make_bank(db_session)
        snaps = _full_snapshots_for_quiz(db_session, bank.id)
        cfg = QuizConfig(title="S", bank_id=bank.id, mode="EXAM", time_limit_minutes=10, question_count=2)
        quiz = QuizService().create_quiz(db_session, cfg, snaps)
        attempt = QuizService().create_attempt(db_session, quiz.id)
        qq_id = quiz.quiz_questions[0].id
        return attempt.id, qq_id

    def test_save_answer_creates_or_updates(self, db_session):
        attempt_id, qq_id = self._setup(db_session)
        svc = QuizService()
        aa = svc.save_answer(db_session, attempt_id, qq_id, {"selected": "A"})
        assert aa.is_answered is True
        assert json.loads(aa.answer_payload)["selected"] == "A"

    def test_save_answer_upserts_existing(self, db_session):
        attempt_id, qq_id = self._setup(db_session)
        svc = QuizService()
        svc.save_answer(db_session, attempt_id, qq_id, {"selected": "A"})
        svc.save_answer(db_session, attempt_id, qq_id, {"selected": "B"})
        aa = db_session.query(AttemptAnswer).filter_by(
            attempt_id=attempt_id, quiz_question_id=qq_id
        ).first()
        assert json.loads(aa.answer_payload)["selected"] == "B"

    def test_autosave_batches_all_answers(self, db_session):
        bank = _make_bank(db_session)
        snaps = _full_snapshots_for_quiz(db_session, bank.id)
        cfg = QuizConfig(title="AS", bank_id=bank.id, mode="EXAM", time_limit_minutes=10, question_count=2)
        quiz = QuizService().create_quiz(db_session, cfg, snaps)
        attempt = QuizService().create_attempt(db_session, quiz.id)
        qq_ids = [q.id for q in quiz.quiz_questions]
        answers = {qq_ids[0]: {"selected": "A"}, qq_ids[1]: {"text": "Paris"}}
        QuizService().autosave_answers(db_session, attempt.id, answers)
        aas = {
            aa.quiz_question_id: aa
            for aa in db_session.query(AttemptAnswer).filter_by(attempt_id=attempt.id).all()
        }
        assert aas[qq_ids[0]].is_answered is True
        assert aas[qq_ids[1]].is_answered is True


# ---------------------------------------------------------------------------
# finalize_attempt
# ---------------------------------------------------------------------------

class TestFinalizeAttempt:

    def _make_quiz_and_attempt(self, db_session):
        bank = _make_bank(db_session)
        mc_q = _make_mc_question(db_session, bank.id)
        bl_q = _make_blank_question(db_session, bank.id, answers=["Paris"])
        sel = QuestionSelector()
        snaps = sel.build_snapshots([mc_q, bl_q], shuffle_options=False)
        cfg = QuizConfig(title="F", bank_id=bank.id, mode="EXAM", time_limit_minutes=10, question_count=2)
        quiz = QuizService().create_quiz(db_session, cfg, snaps)
        attempt = QuizService().create_attempt(db_session, quiz.id)
        return quiz, attempt

    def test_finalize_sets_status_and_stats(self, db_session):
        quiz, attempt = self._make_quiz_and_attempt(db_session)
        qq_ids = [q.id for q in quiz.quiz_questions]
        graded = [
            GradedRow(quiz_question_id=qq_ids[0], answer_payload={"selected": "A"}, is_correct=True, score_awarded=1.0, feedback_state="correct"),
            GradedRow(quiz_question_id=qq_ids[1], answer_payload={}, is_correct=None, score_awarded=0.0, feedback_state="skipped"),
        ]
        svc = QuizService()
        result = svc.finalize_attempt(db_session, attempt.id, "SUBMITTED", graded, 120)
        assert result.status == "SUBMITTED"
        assert result.correct_count == 1
        assert result.incorrect_count == 0
        assert result.skipped_count == 1
        assert result.score == pytest.approx(1.0)
        assert result.duration_seconds == 120

    def test_finalize_time_up_status(self, db_session):
        quiz, attempt = self._make_quiz_and_attempt(db_session)
        qq_ids = [q.id for q in quiz.quiz_questions]
        graded = [
            GradedRow(quiz_question_id=qq_ids[0], answer_payload={}, is_correct=None, score_awarded=0.0, feedback_state="skipped"),
            GradedRow(quiz_question_id=qq_ids[1], answer_payload={}, is_correct=None, score_awarded=0.0, feedback_state="skipped"),
        ]
        result = QuizService().finalize_attempt(db_session, attempt.id, "TIME_UP", graded, 600)
        assert result.status == "TIME_UP"

    def test_finalize_incorrect_answer_counted(self, db_session):
        quiz, attempt = self._make_quiz_and_attempt(db_session)
        qq_ids = [q.id for q in quiz.quiz_questions]
        graded = [
            GradedRow(quiz_question_id=qq_ids[0], answer_payload={"selected": "B"}, is_correct=False, score_awarded=0.0, feedback_state="incorrect"),
            GradedRow(quiz_question_id=qq_ids[1], answer_payload={"text": "Paris"}, is_correct=True, score_awarded=1.0, feedback_state="correct"),
        ]
        result = QuizService().finalize_attempt(db_session, attempt.id, "SUBMITTED", graded, 90)
        assert result.correct_count == 1
        assert result.incorrect_count == 1
        assert result.score == pytest.approx(1.0)

    def test_finalize_invalid_attempt_raises(self, db_session):
        graded: list[GradedRow] = []
        with pytest.raises(ValueError):
            QuizService().finalize_attempt(db_session, 9999, "SUBMITTED", graded, 0)


# ---------------------------------------------------------------------------
# grade_answer_from_dict
# ---------------------------------------------------------------------------

class TestGradeAnswerFromDict:

    def test_mc_correct(self):
        qq = _mc_snapshot()
        result = QuizService.grade_answer_from_dict(qq, {"selected": "A"})
        assert result.is_correct is True
        assert result.score_awarded == pytest.approx(1.0)

    def test_mc_incorrect(self):
        qq = _mc_snapshot()
        result = QuizService.grade_answer_from_dict(qq, {"selected": "B"})
        assert result.is_correct is False
        assert result.score_awarded == pytest.approx(0.0)

    def test_mc_no_selection_skipped(self):
        qq = _mc_snapshot()
        result = QuizService.grade_answer_from_dict(qq, {})
        assert result.is_correct is None
        assert result.score_awarded == pytest.approx(0.0)

    def test_ma_exact_match_correct(self):
        qq = {
            "type": "MA",
            "point_value": 2.0,
            "options": [
                {"key": "A", "is_correct": True},
                {"key": "B", "is_correct": True},
                {"key": "C", "is_correct": False},
            ],
            "accepted_answers": [],
        }
        result = QuizService.grade_answer_from_dict(qq, {"selected": ["A", "B"]})
        assert result.is_correct is True
        assert result.score_awarded == pytest.approx(2.0)

    def test_ma_partial_match_incorrect(self):
        qq = {
            "type": "MA",
            "point_value": 2.0,
            "options": [
                {"key": "A", "is_correct": True},
                {"key": "B", "is_correct": True},
                {"key": "C", "is_correct": False},
            ],
            "accepted_answers": [],
        }
        result = QuizService.grade_answer_from_dict(qq, {"selected": ["A"]})
        assert result.is_correct is False

    def test_ma_with_wrong_extra_selection_incorrect(self):
        qq = {
            "type": "MA",
            "point_value": 2.0,
            "options": [
                {"key": "A", "is_correct": True},
                {"key": "B", "is_correct": True},
                {"key": "C", "is_correct": False},
            ],
            "accepted_answers": [],
        }
        result = QuizService.grade_answer_from_dict(qq, {"selected": ["A", "B", "C"]})
        assert result.is_correct is False

    def test_blank_case_insensitive_correct(self):
        qq = _blank_snapshot(case_sensitive=False)
        result = QuizService.grade_answer_from_dict(qq, {"text": "PARIS"})
        assert result.is_correct is True

    def test_blank_case_sensitive_wrong_case(self):
        qq = _blank_snapshot(case_sensitive=True)
        # Only "Paris" and "paris" in accepted list
        result = QuizService.grade_answer_from_dict(qq, {"text": "PARIS"})
        assert result.is_correct is False

    def test_blank_case_sensitive_exact_match(self):
        qq = _blank_snapshot(case_sensitive=True)
        result = QuizService.grade_answer_from_dict(qq, {"text": "Paris"})
        assert result.is_correct is True
        assert result.score_awarded == pytest.approx(1.0)

    def test_blank_trim_whitespace(self):
        qq = _blank_snapshot(case_sensitive=False)
        result = QuizService.grade_answer_from_dict(qq, {"text": "  paris  "})
        assert result.is_correct is True

    def test_blank_empty_payload_skipped(self):
        qq = _blank_snapshot()
        result = QuizService.grade_answer_from_dict(qq, {"text": ""})
        assert result.is_correct is None or result.is_correct is False
        assert result.score_awarded == pytest.approx(0.0)

    def test_sa_correct_answer(self):
        qq = {
            "type": "SA",
            "point_value": 1.0,
            "options": [],
            "accepted_answers": ["Mercury"],
            "case_sensitive": False,
            "trim_whitespace": True,
        }
        result = QuizService.grade_answer_from_dict(qq, {"text": "mercury"})
        assert result.is_correct is True
        assert result.score_awarded == pytest.approx(1.0)

    def test_sa_wrong_answer(self):
        qq = {
            "type": "SA",
            "point_value": 1.0,
            "options": [],
            "accepted_answers": ["Mercury"],
            "case_sensitive": False,
            "trim_whitespace": True,
        }
        result = QuizService.grade_answer_from_dict(qq, {"text": "Venus"})
        assert result.is_correct is False
        assert result.score_awarded == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# QuestionSelector.select
# ---------------------------------------------------------------------------

class TestQuestionSelectorSelect:

    def test_returns_up_to_count(self, db_session):
        bank = _make_bank(db_session)
        for i in range(5):
            _make_mc_question(db_session, bank.id, content=f"Q{i}")
        sel = QuestionSelector()
        result = sel.select(db_session, bank.id, count=3, shuffle=False)
        assert len(result) == 3

    def test_returns_all_if_count_exceeds_available(self, db_session):
        bank = _make_bank(db_session)
        for i in range(3):
            _make_mc_question(db_session, bank.id, content=f"Q{i}")
        sel = QuestionSelector()
        result = sel.select(db_session, bank.id, count=10, shuffle=False)
        assert len(result) == 3

    def test_filters_by_type(self, db_session):
        bank = _make_bank(db_session)
        _make_mc_question(db_session, bank.id)
        _make_blank_question(db_session, bank.id)
        sel = QuestionSelector()
        result = sel.select(db_session, bank.id, count=10, question_types=["BLANK"], shuffle=False)
        assert all(q.question_type == "BLANK" for q in result)
        assert len(result) == 1

    def test_filters_inactive_questions(self, db_session):
        bank = _make_bank(db_session)
        _make_mc_question(db_session, bank.id)
        inactive = Question(
            bank_id=bank.id, question_type="MC", content="Inactive Q",
            point_value=1.0, is_active=False,
        )
        db_session.add(inactive)
        db_session.flush()
        sel = QuestionSelector()
        result = sel.select(db_session, bank.id, count=10, active_only=True, shuffle=False)
        assert all(q.is_active for q in result)
        assert len(result) == 1

    def test_inactive_included_when_active_only_false(self, db_session):
        bank = _make_bank(db_session)
        _make_mc_question(db_session, bank.id)
        inactive = Question(
            bank_id=bank.id, question_type="MC", content="Inactive Q",
            point_value=1.0, is_active=False,
        )
        db_session.add(inactive)
        db_session.flush()
        sel = QuestionSelector()
        result = sel.select(db_session, bank.id, count=10, active_only=False, shuffle=False)
        assert len(result) == 2

    def test_different_bank_not_included(self, db_session):
        bank1 = _make_bank(db_session, "Bank1")
        bank2 = _make_bank(db_session, "Bank2")
        _make_mc_question(db_session, bank1.id)
        _make_mc_question(db_session, bank2.id)
        sel = QuestionSelector()
        result = sel.select(db_session, bank1.id, count=10, shuffle=False)
        assert all(q.bank_id == bank1.id for q in result)
        assert len(result) == 1


# ---------------------------------------------------------------------------
# QuestionSelector.available_count
# ---------------------------------------------------------------------------

class TestQuestionSelectorAvailableCount:

    def test_available_count_matches_select(self, db_session):
        bank = _make_bank(db_session)
        for _ in range(4):
            _make_mc_question(db_session, bank.id)
        _make_blank_question(db_session, bank.id)
        sel = QuestionSelector()
        count_all = sel.available_count(db_session, bank.id)
        count_mc = sel.available_count(db_session, bank.id, question_types=["MC"])
        assert count_all == 5
        assert count_mc == 4

    def test_available_count_respects_active_only(self, db_session):
        bank = _make_bank(db_session)
        _make_mc_question(db_session, bank.id)
        db_session.add(Question(
            bank_id=bank.id, question_type="MC", content="I", point_value=1.0, is_active=False,
        ))
        db_session.flush()
        sel = QuestionSelector()
        assert sel.available_count(db_session, bank.id, active_only=True) == 1
        assert sel.available_count(db_session, bank.id, active_only=False) == 2


# ---------------------------------------------------------------------------
# QuestionSelector.build_snapshots
# ---------------------------------------------------------------------------

class TestBuildSnapshots:

    def test_mc_snapshot_has_options(self, db_session):
        bank = _make_bank(db_session)
        mc = _make_mc_question(db_session, bank.id)
        snaps = QuestionSelector().build_snapshots([mc], shuffle_options=False)
        assert len(snaps) == 1
        snap = snaps[0]
        assert snap["type"] == "MC"
        assert len(snap["options"]) == 3
        assert any(o["key"] == "A" and o["is_correct"] for o in snap["options"])
        assert snap["accepted_answers"] == []

    def test_blank_snapshot_has_accepted_answers(self, db_session):
        bank = _make_bank(db_session)
        bl = _make_blank_question(db_session, bank.id, answers=["Paris"])
        snaps = QuestionSelector().build_snapshots([bl], shuffle_options=False)
        snap = snaps[0]
        assert snap["type"] == "BLANK"
        assert "Paris" in snap["accepted_answers"]
        assert snap["options"] == []

    def test_snapshot_contains_required_keys(self, db_session):
        bank = _make_bank(db_session)
        mc = _make_mc_question(db_session, bank.id)
        snap = QuestionSelector().build_snapshots([mc])[0]
        for key in ("question_id", "content", "type", "hint", "explanation",
                    "point_value", "case_sensitive", "trim_whitespace", "options",
                    "accepted_answers"):
            assert key in snap, f"Missing key in snapshot: {key}"

    def test_snapshot_links_correct_question_id(self, db_session):
        bank = _make_bank(db_session)
        mc = _make_mc_question(db_session, bank.id)
        snap = QuestionSelector().build_snapshots([mc])[0]
        assert snap["question_id"] == mc.id

    def test_multiple_questions_preserve_order(self, db_session):
        bank = _make_bank(db_session)
        mc = _make_mc_question(db_session, bank.id, content="First")
        bl = _make_blank_question(db_session, bank.id)
        snaps = QuestionSelector().build_snapshots([mc, bl], shuffle_options=False)
        assert snaps[0]["question_id"] == mc.id
        assert snaps[1]["question_id"] == bl.id
