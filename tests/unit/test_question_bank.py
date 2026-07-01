"""Unit tests for QuestionService – bank CRUD, question CRUD, search/filter.

All tests use the in-memory SQLite fixture from conftest.py; no actual DB
file is touched.  Import format and UI are NOT tested here.
"""
from __future__ import annotations

import json
import pytest

from core.domain.services.question_service import (
    BankStats,
    QuestionEditData,
    QuestionService,
)
from core.database.models import (
    Attempt,
    AttemptAnswer,
    Question,
    QuestionBank,
    QuestionOption,
    Quiz,
    QuizQuestion,
)
from core.utils.constants import Difficulty, QuestionType


# ──────────────────────────────────────────────
# Shared fixture helpers
# ──────────────────────────────────────────────

@pytest.fixture()
def svc() -> QuestionService:
    return QuestionService()


@pytest.fixture()
def session(db_session):
    """Alias so tests read more naturally."""
    return db_session


@pytest.fixture()
def bank(session, svc) -> QuestionBank:
    return svc.create_bank(session, "Test Bank")


def _mc_data(
    bank_id: int,
    content: str = "Which?",
    *,
    difficulty: str = "easy",
    learning_outcome_code: str = "",
) -> QuestionEditData:
    return QuestionEditData(
        bank_id=bank_id,
        question_type=QuestionType.MULTIPLE_CHOICE,
        content=content,
        difficulty=difficulty,
        learning_outcome_code=learning_outcome_code,
        score=1.0,
        options=[
            ("A", "Option A", True),
            ("B", "Option B", False),
            ("C", "Option C", False),
        ],
    )


def _ma_data(bank_id: int) -> QuestionEditData:
    return QuestionEditData(
        bank_id=bank_id,
        question_type=QuestionType.MULTIPLE_ANSWER,
        content="Choose all correct:",
        score=2.0,
        options=[
            ("A", "Right1", True),
            ("B", "Right2", True),
            ("C", "Wrong", False),
        ],
    )


def _blank_data(bank_id: int) -> QuestionEditData:
    return QuestionEditData(
        bank_id=bank_id,
        question_type=QuestionType.BLANK,
        content="The capital of France is ________.",
        score=1.0,
        accepted_answers=["Paris", "paris"],
    )


def _sa_data(bank_id: int) -> QuestionEditData:
    return QuestionEditData(
        bank_id=bank_id,
        question_type=QuestionType.SHORT_ANSWER,
        content="What is 2+2?",
        score=1.0,
        accepted_answers=["4", "four"],
    )


# ──────────────────────────────────────────────
# Bank CRUD
# ──────────────────────────────────────────────

class TestBankCRUD:
    def test_create_bank_success(self, session, svc):
        b = svc.create_bank(session, "Alpha")
        assert b.id is not None
        assert b.name == "Alpha"

    def test_create_bank_trims_whitespace(self, session, svc):
        b = svc.create_bank(session, "  Trimmed  ")
        assert b.name == "Trimmed"

    def test_create_bank_empty_name_raises(self, session, svc):
        with pytest.raises(ValueError, match="trống"):
            svc.create_bank(session, "   ")

    def test_create_bank_duplicate_raises(self, session, svc):
        svc.create_bank(session, "Dup")
        with pytest.raises(ValueError, match="đã tồn tại"):
            svc.create_bank(session, "Dup")

    def test_list_banks_sorted(self, session, svc):
        svc.create_bank(session, "Zebra")
        svc.create_bank(session, "Alpha")
        svc.create_bank(session, "Mango")
        names = [b.name for b in svc.list_banks(session)]
        assert names == sorted(names)

    def test_rename_bank_success(self, session, svc):
        b = svc.create_bank(session, "Old")
        svc.rename_bank(session, b.id, "New")
        refreshed = session.get(QuestionBank, b.id)
        assert refreshed.name == "New"

    def test_rename_bank_empty_raises(self, session, svc):
        b = svc.create_bank(session, "Name")
        with pytest.raises(ValueError, match="trống"):
            svc.rename_bank(session, b.id, "")

    def test_rename_bank_conflict_raises(self, session, svc):
        b1 = svc.create_bank(session, "B1")
        svc.create_bank(session, "B2")
        with pytest.raises(ValueError, match="đã tồn tại"):
            svc.rename_bank(session, b1.id, "B2")

    def test_rename_bank_same_name_ok(self, session, svc):
        b = svc.create_bank(session, "Same")
        svc.rename_bank(session, b.id, "Same")  # should not raise
        assert session.get(QuestionBank, b.id).name == "Same"

    def test_rename_bank_not_found_raises(self, session, svc):
        with pytest.raises(ValueError, match="Không tìm thấy"):
            svc.rename_bank(session, 9999, "X")

    def test_delete_bank_removes_bank(self, session, svc):
        b = svc.create_bank(session, "Temporary")
        svc.delete_bank(session, b.id)
        session.flush()
        assert session.get(QuestionBank, b.id) is None

    def test_delete_bank_not_found_raises(self, session, svc):
        with pytest.raises(ValueError, match="Không tìm thấy"):
            svc.delete_bank(session, 9999)

    def test_get_bank_count(self, session, svc):
        svc.create_bank(session, "A")
        svc.create_bank(session, "B")
        assert svc.get_bank_count(session) == 2

    def test_get_bank_stats_counts(self, session, svc):
        b = svc.create_bank(session, "Stats")
        svc.create_question(session, _mc_data(b.id))
        svc.create_question(session, _mc_data(b.id, content="Q2"))
        stats = svc.get_bank_stats(session)
        found = next((s for s in stats if s.bank_id == b.id), None)
        assert found is not None
        assert found.question_count == 2

    def test_get_bank_stats_empty_bank(self, session, svc):
        b = svc.create_bank(session, "Empty")
        stats = svc.get_bank_stats(session)
        found = next((s for s in stats if s.bank_id == b.id), None)
        assert found.question_count == 0

    def test_get_bank_overview_rows_include_context_metadata(self, session, svc):
        bank = svc.create_bank(
            session,
            "Overview Bank",
            assessment_type="Thường xuyên",
            course_learning_outcomes=[
                {"code": "CLO_1", "description": "Mô tả 1"},
                {"code": "CLO_2", "description": "Mô tả 2"},
            ],
        )
        svc.create_question(session, _mc_data(bank.id))

        rows = svc.get_bank_overview_rows(session)
        found = next((row for row in rows if row.bank_id == bank.id), None)

        assert found is not None
        assert found.assessment_type == "Thường xuyên"
        assert found.question_count == 1
        assert found.course_learning_outcomes == [
            {"code": "CLO_1", "description": "Mô tả 1"},
            {"code": "CLO_2", "description": "Mô tả 2"},
        ]

    def test_create_bank_with_assessment_type_and_clos(self, session, svc):
        bank = svc.create_bank(
            session,
            "Metadata Bank",
            subject="Quản trị chuỗi cung ứng",
            course_code="SCM101",
            assessment_type="Định kỳ",
            course_learning_outcomes=[
                {"code": "CLO_1", "description": "Mô tả 1"},
                {"code": "CLO_2", "description": "Mô tả 2"},
            ],
        )

        refreshed = session.get(QuestionBank, bank.id)
        assert refreshed is not None
        assert refreshed.subject == "Quản trị chuỗi cung ứng"
        assert refreshed.assessment_type == "Định kỳ"
        assert refreshed.get_course_learning_outcomes() == [
            {"code": "CLO_1", "description": "Mô tả 1"},
            {"code": "CLO_2", "description": "Mô tả 2"},
        ]

    def test_update_bank_preserves_legacy_exam_title_and_updates_new_metadata(self, session, svc):
        bank = svc.create_bank(session, "Legacy Bank", exam_title="Giữa kỳ cũ")

        svc.update_bank(
            session,
            bank.id,
            "Legacy Bank",
            exam_title="Giữa kỳ cũ",
            assessment_type="Tổng kết",
            course_learning_outcomes=[
                {"code": "CLO_3", "description": "Mô tả CLO 3"},
            ],
        )

        refreshed = session.get(QuestionBank, bank.id)
        assert refreshed is not None
        assert refreshed.exam_title == "Giữa kỳ cũ"
        assert refreshed.assessment_type == "Tổng kết"
        assert refreshed.get_course_learning_outcomes() == [
            {"code": "CLO_3", "description": "Mô tả CLO 3"},
        ]

    def test_create_bank_rejects_invalid_assessment_type(self, session, svc):
        with pytest.raises(ValueError, match="Loại đánh giá"):
            svc.create_bank(session, "Invalid Assessment", assessment_type="Giữa kỳ")

    def test_create_bank_rejects_partial_clo_row(self, session, svc):
        with pytest.raises(ValueError, match="Mã CLO và Mô tả CLO"):
            svc.create_bank(
                session,
                "Invalid CLO",
                course_learning_outcomes=[{"code": "CLO_1", "description": ""}],
            )


class TestDashboardStatsAPI:
    def test_get_question_type_breakdown(self, session, svc, bank):
        svc.create_question(session, _mc_data(bank.id, content="mc"))
        svc.create_question(session, _ma_data(bank.id))
        svc.create_question(session, _blank_data(bank.id))
        svc.create_question(session, _sa_data(bank.id))

        breakdown = svc.get_question_type_breakdown(session)

        assert breakdown.mc == 1
        assert breakdown.ma == 1
        assert breakdown.blank == 1
        assert breakdown.sa == 1

    def test_get_usage_banks_returns_counts(self, session, svc):
        b1 = svc.create_bank(session, "Usage A")
        b2 = svc.create_bank(session, "Usage B")
        svc.create_question(session, _mc_data(b1.id, content="a1"))
        svc.create_question(session, _mc_data(b1.id, content="a2"))
        svc.create_question(session, _mc_data(b2.id, content="b1"))

        rows = svc.get_usage_banks(session)
        counts = {r.bank_name: r.question_count for r in rows}

        assert counts["Usage A"] == 2
        assert counts["Usage B"] == 1

    def test_get_question_usage_rows_and_summary(self, session, svc, bank):
        q = svc.create_question(session, _mc_data(bank.id, content="usage"))

        quiz = Quiz(
            title="Usage Quiz",
            bank_id=bank.id,
            mode="EXAM",
            time_limit_minutes=30,
            total_questions=1,
        )
        session.add(quiz)
        session.flush()

        qq = QuizQuestion(
            quiz_id=quiz.id,
            question_id=q.id,
            question_order=1,
            snapshot_content=q.content,
            snapshot_type=q.question_type,
            snapshot_point_value=1.0,
        )
        session.add(qq)
        session.flush()

        attempt = Attempt(
            quiz_id=quiz.id,
            mode="EXAM",
            status="SUBMITTED",
            answered_count=1,
            correct_count=1,
            incorrect_count=0,
            skipped_count=0,
            score=1.0,
            max_score=1.0,
        )
        session.add(attempt)
        session.flush()

        session.add(
            AttemptAnswer(
                attempt_id=attempt.id,
                quiz_question_id=qq.id,
                answer_payload='{"selected":"A"}',
                is_answered=True,
                is_correct=True,
                score_awarded=1.0,
                feedback_state="correct",
            )
        )
        session.flush()

        rows = svc.get_question_usage_rows(session, bank.id)
        summary = svc.build_usage_summary(rows)

        assert len(rows) == 1
        assert rows[0].question_id == q.id
        assert rows[0].learning_outcome_code == ""
        assert rows[0].used_count == 1
        assert rows[0].correct_count == 1
        assert summary.total_questions == 1
        assert summary.active_questions == 1
        assert summary.total_uses == 1
        assert summary.total_correct == 1
        assert summary.difficulty_breakdown["Nhớ"] == 1
        assert summary.learning_outcome_count == 0

    def test_usage_summary_counts_clo_and_normalizes_levels(self, session, svc, bank):
        bank = svc.create_bank(
            session,
            "CLO Bank",
            course_learning_outcomes=[
                {"code": "CLO_1", "description": "Mô tả 1"},
                {"code": "CLO_2", "description": "Mô tả 2"},
            ],
        )
        svc.create_question(
            session,
            _mc_data(
                bank.id,
                content="usage clo",
                difficulty="medium",
                learning_outcome_code="CLO_1",
            ),
        )
        svc.create_question(
            session,
            QuestionEditData(
                bank_id=bank.id,
                question_type=QuestionType.SHORT_ANSWER,
                content="SA usage",
                difficulty="Phân tích",
                learning_outcome_code="CLO_2",
                score=1.0,
                accepted_answers=["x"],
            ),
        )

        rows = svc.get_question_usage_rows(session, bank.id)
        summary = svc.build_usage_summary(rows)

        assert summary.learning_outcome_count == 2
        assert summary.learning_outcome_top == [("CLO_1", 1), ("CLO_2", 1)]
        assert summary.difficulty_breakdown["Hiểu"] == 1
        assert summary.difficulty_breakdown["Phân tích"] == 1


# ──────────────────────────────────────────────
# Question CRUD
# ──────────────────────────────────────────────

class TestQuestionCreate:
    def test_create_mc_question(self, session, svc, bank):
        q = svc.create_question(session, _mc_data(bank.id))
        assert q.id is not None
        assert q.question_type == "MC"
        assert q.content == "Which?"
        assert q.bank_id == bank.id

    def test_mc_options_saved(self, session, svc, bank):
        q = svc.create_question(session, _mc_data(bank.id))
        session.flush()
        opts = session.query(QuestionOption).filter_by(question_id=q.id).all()
        assert len(opts) == 3
        correct = [o for o in opts if o.is_correct]
        assert len(correct) == 1
        assert correct[0].option_key == "A"

    def test_create_ma_question(self, session, svc, bank):
        q = svc.create_question(session, _ma_data(bank.id))
        assert q.question_type == "MA"
        session.flush()
        opts = session.query(QuestionOption).filter_by(question_id=q.id).all()
        correct = [o for o in opts if o.is_correct]
        assert len(correct) == 2

    def test_create_blank_question(self, session, svc, bank):
        q = svc.create_question(session, _blank_data(bank.id))
        assert q.question_type == "BLANK"
        answers = json.loads(q.accepted_answers)
        assert "Paris" in answers

    def test_create_sa_question(self, session, svc, bank):
        q = svc.create_question(session, _sa_data(bank.id))
        assert q.question_type == "SA"
        answers = json.loads(q.accepted_answers)
        assert "4" in answers

    def test_create_question_with_learning_outcome_code(self, session, svc):
        bank = svc.create_bank(
            session,
            "CLO Bank",
            course_learning_outcomes=[
                {"code": "CLO_1", "description": "Mô tả 1"},
            ],
        )
        data = _mc_data(bank.id)
        data.learning_outcome_code = "CLO_1"

        q = svc.create_question(session, data)

        assert q.learning_outcome_code == "CLO_1"

    def test_get_question_count(self, session, svc, bank):
        svc.create_question(session, _mc_data(bank.id))
        svc.create_question(session, _mc_data(bank.id, content="Q2"))
        assert svc.get_question_count(session) == 2


class TestQuestionValidation:
    def test_mc_empty_content_raises(self, session, svc, bank):
        data = _mc_data(bank.id)
        data.content = "   "
        with pytest.raises(ValueError, match="trống"):
            svc.create_question(session, data)

    def test_mc_needs_2_options(self, session, svc, bank):
        data = _mc_data(bank.id)
        data.options = [("A", "Only", True)]
        with pytest.raises(ValueError, match="2 lựa chọn"):
            svc.create_question(session, data)

    def test_mc_needs_exactly_1_correct(self, session, svc, bank):
        data = _mc_data(bank.id)
        data.options = [("A", "A", True), ("B", "B", True)]
        with pytest.raises(ValueError, match="1 đáp án"):
            svc.create_question(session, data)

    def test_ma_needs_2_correct(self, session, svc, bank):
        data = _ma_data(bank.id)
        data.options = [("A", "A", True), ("B", "B", False), ("C", "C", False)]
        with pytest.raises(ValueError, match="2 đáp án"):
            svc.create_question(session, data)

    def test_blank_needs_accepted_answers(self, session, svc, bank):
        data = _blank_data(bank.id)
        data.accepted_answers = []
        with pytest.raises(ValueError, match="đáp án"):
            svc.create_question(session, data)

    def test_sa_needs_accepted_answers(self, session, svc, bank):
        data = _sa_data(bank.id)
        data.accepted_answers = []
        with pytest.raises(ValueError, match="đáp án"):
            svc.create_question(session, data)

    def test_zero_score_raises(self, session, svc, bank):
        data = _mc_data(bank.id)
        data.score = 0
        with pytest.raises(ValueError, match="dương"):
            svc.create_question(session, data)

    def test_question_learning_outcome_must_belong_to_bank(self, session, svc, bank):
        data = _mc_data(bank.id)
        data.learning_outcome_code = "CLO_999"
        with pytest.raises(ValueError, match="Chuẩn đầu ra"):
            svc.create_question(session, data)

    def test_negative_score_raises(self, session, svc, bank):
        data = _mc_data(bank.id)
        data.score = -1.0
        with pytest.raises(ValueError, match="dương"):
            svc.create_question(session, data)

    def test_blank_whitespace_only_answers_stripped(self, session, svc, bank):
        data = _blank_data(bank.id)
        data.accepted_answers = ["   ", ""]
        with pytest.raises(ValueError, match="đáp án"):
            svc.create_question(session, data)


class TestQuestionUpdate:
    def test_update_question_content(self, session, svc, bank):
        q = svc.create_question(session, _mc_data(bank.id))
        session.flush()
        qid = q.id

        data = _mc_data(bank.id, content="Updated content?")
        svc.update_question(session, qid, data)
        refreshed = session.get(Question, qid)
        assert refreshed.content == "Updated content?"

    def test_update_replaces_options(self, session, svc, bank):
        q = svc.create_question(session, _mc_data(bank.id))
        session.flush()
        qid = q.id

        new_data = _mc_data(bank.id)
        new_data.options = [
            ("A", "New A", False),
            ("B", "New B", True),
        ]
        svc.update_question(session, qid, new_data)
        session.flush()

        opts = session.query(QuestionOption).filter_by(question_id=qid).all()
        assert len(opts) == 2
        assert any(o.is_correct and o.option_key == "B" for o in opts)

    def test_update_not_found_raises(self, session, svc, bank):
        with pytest.raises(ValueError, match="Không tìm thấy"):
            svc.update_question(session, 9999, _mc_data(bank.id))

    def test_update_type_blank_to_sa_changes_type(self, session, svc, bank):
        q = svc.create_question(session, _blank_data(bank.id))
        session.flush()
        new_data = _sa_data(bank.id)
        svc.update_question(session, q.id, new_data)
        assert session.get(Question, q.id).question_type == "SA"

    def test_update_question_learning_outcome_code(self, session, svc):
        bank = svc.create_bank(
            session,
            "Update CLO",
            course_learning_outcomes=[
                {"code": "CLO_1", "description": "Mô tả 1"},
                {"code": "CLO_2", "description": "Mô tả 2"},
            ],
        )
        q = svc.create_question(session, _mc_data(bank.id))
        session.flush()

        data = _mc_data(bank.id, content="Updated content?")
        data.learning_outcome_code = "CLO_2"
        svc.update_question(session, q.id, data)

        assert session.get(Question, q.id).learning_outcome_code == "CLO_2"


class TestQuestionDelete:
    def test_delete_question(self, session, svc, bank):
        q = svc.create_question(session, _mc_data(bank.id))
        session.flush()
        qid = q.id
        svc.delete_question(session, qid)
        session.flush()
        assert session.get(Question, qid) is None

    def test_delete_question_not_found_raises(self, session, svc):
        with pytest.raises(ValueError, match="Không tìm thấy"):
            svc.delete_question(session, 9999)

    def test_delete_bulk_returns_count(self, session, svc, bank):
        q1 = svc.create_question(session, _mc_data(bank.id))
        q2 = svc.create_question(session, _mc_data(bank.id, content="Q2"))
        session.flush()
        deleted = svc.delete_questions_bulk(session, [q1.id, q2.id])
        assert deleted == 2

    def test_delete_bulk_skips_missing(self, session, svc, bank):
        q = svc.create_question(session, _mc_data(bank.id))
        session.flush()
        deleted = svc.delete_questions_bulk(session, [q.id, 9999])
        assert deleted == 1

    def test_delete_bulk_empty_list(self, session, svc):
        deleted = svc.delete_questions_bulk(session, [])
        assert deleted == 0

    def test_delete_bank_cascades_questions(self, session, svc):
        b = svc.create_bank(session, "Cascade")
        q = svc.create_question(session, _mc_data(b.id))
        session.flush()
        qid = q.id
        svc.delete_bank(session, b.id)
        session.flush()
        assert session.get(Question, qid) is None


# ──────────────────────────────────────────────
# Search and filter
# ──────────────────────────────────────────────

class TestQuestionSearch:
    @pytest.fixture(autouse=True)
    def _setup(self, session, svc):
        self.session = session
        self.svc = svc
        self.bank = svc.create_bank(session, "Search Bank")
        d1 = QuestionEditData(
            bank_id=self.bank.id,
            question_type=QuestionType.MULTIPLE_CHOICE,
            content="What is photosynthesis?",
            score=1.0,
            category="Biology",
            tags="science||nature",
            difficulty="easy",
            options=[("A", "Process", True), ("B", "Wrong", False)],
        )
        d2 = QuestionEditData(
            bank_id=self.bank.id,
            question_type=QuestionType.SHORT_ANSWER,
            content="Define Python programming language.",
            score=2.0,
            category="Technology",
            tags="coding||software",
            difficulty="medium",
            accepted_answers=["interpreted language"],
        )
        d3 = QuestionEditData(
            bank_id=self.bank.id,
            question_type=QuestionType.MULTIPLE_ANSWER,
            content="Which are prime numbers?",
            score=3.0,
            category="Math",
            tags="numbers",
            difficulty="hard",
            options=[
                ("A", "2", True),
                ("B", "3", True),
                ("C", "4", False),
            ],
        )
        self.q1 = svc.create_question(session, d1)
        self.q2 = svc.create_question(session, d2)
        self.q3 = svc.create_question(session, d3)
        session.flush()

    def test_list_all_in_bank(self):
        qs = self.svc.list_questions(self.session, bank_id=self.bank.id)
        assert len(qs) == 3

    def test_search_by_content(self):
        qs = self.svc.list_questions(self.session, bank_id=self.bank.id, search="photosynthesis")
        assert len(qs) == 1
        assert qs[0].id == self.q1.id

    def test_search_case_insensitive(self):
        qs = self.svc.list_questions(self.session, bank_id=self.bank.id, search="PYTHON")
        assert len(qs) == 1

    def test_search_by_category(self):
        qs = self.svc.list_questions(self.session, bank_id=self.bank.id, search="Technology")
        assert len(qs) == 1
        assert qs[0].id == self.q2.id

    def test_search_by_tags(self):
        qs = self.svc.list_questions(self.session, bank_id=self.bank.id, search="coding")
        assert len(qs) == 1
        assert qs[0].id == self.q2.id

    def test_search_by_learning_outcome_code(self):
        bank = self.svc.get_bank_by_id(self.session, self.bank.id)
        bank.set_course_learning_outcomes([{"code": "CLO_1", "description": "Mô tả 1"}])
        self.q1.learning_outcome_code = "CLO_1"
        self.session.flush()

        qs = self.svc.list_questions(self.session, bank_id=self.bank.id, search="CLO_1")

        assert len(qs) == 1
        assert qs[0].id == self.q1.id

    def test_filter_by_type_mc(self):
        qs = self.svc.list_questions(self.session, bank_id=self.bank.id, question_type="MC")
        assert all(q.question_type == "MC" for q in qs)
        assert len(qs) == 1

    def test_filter_by_type_ma(self):
        qs = self.svc.list_questions(self.session, bank_id=self.bank.id, question_type="MA")
        assert len(qs) == 1
        assert qs[0].id == self.q3.id

    def test_filter_by_difficulty(self):
        qs = self.svc.list_questions(self.session, bank_id=self.bank.id, difficulty="Nhớ")
        assert len(qs) == 1
        assert qs[0].id == self.q1.id

    def test_search_no_match_returns_empty(self):
        qs = self.svc.list_questions(self.session, bank_id=self.bank.id, search="ZZZNOMATCH")
        assert qs == []

    def test_no_bank_filter_returns_all(self):
        other = self.svc.create_bank(self.session, "Other Bank")
        self.svc.create_question(self.session, _mc_data(other.id))
        all_qs = self.svc.list_questions(self.session)
        assert len(all_qs) >= 4

    def test_combined_search_and_type(self):
        qs = self.svc.list_questions(
            self.session, bank_id=self.bank.id, search="prime", question_type="MA"
        )
        assert len(qs) == 1
        assert qs[0].id == self.q3.id

    def test_combined_search_type_no_match(self):
        qs = self.svc.list_questions(
            self.session, bank_id=self.bank.id, search="photosynthesis", question_type="SA"
        )
        assert qs == []
