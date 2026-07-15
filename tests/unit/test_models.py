"""Unit tests for SQLAlchemy models (in-memory DB)."""
from __future__ import annotations

import json

import pytest

from core.database.models import (
    AppSetting,
    Attempt,
    AttemptAnswer,
    Question,
    QuestionBank,
    QuestionOption,
    QuestionRubricTemplate,
    Quiz,
    QuizQuestion,
)
from core.utils.constants import AttemptStatus, QuizMode


class TestQuestionBank:
    def test_create_and_retrieve(self, db_session):
        bank = QuestionBank(name="Test Bank", description="A test bank")
        db_session.add(bank)
        db_session.flush()
        assert bank.id is not None
        fetched = db_session.get(QuestionBank, bank.id)
        assert fetched.name == "Test Bank"

    def test_unique_name_constraint(self, db_session):
        db_session.add(QuestionBank(name="Unique"))
        db_session.flush()
        db_session.add(QuestionBank(name="Unique"))
        with pytest.raises(Exception):  # IntegrityError
            db_session.flush()


class TestQuestion:
    def test_create_mc_question(self, db_session):
        bank = QuestionBank(name="BankMC")
        db_session.add(bank)
        db_session.flush()

        q = Question(
            bank_id=bank.id,
            question_type="MC",
            content="What is 2+2?",
            point_value=1.0,
        )
        db_session.add(q)
        db_session.flush()
        assert q.id is not None

    def test_accepted_answers_serialization(self, db_session):
        bank = QuestionBank(name="BankSA")
        db_session.add(bank)
        db_session.flush()

        q = Question(bank_id=bank.id, question_type="SA", content="What is EOQ?")
        q.set_accepted_answers(["EOQ", "Economic Order Quantity"])
        db_session.add(q)
        db_session.flush()

        fetched = db_session.get(Question, q.id)
        assert fetched.get_accepted_answers() == ["EOQ", "Economic Order Quantity"]

    def test_problem_payload_helpers(self, db_session):
        bank = QuestionBank(name="BankProblem")
        db_session.add(bank)
        db_session.flush()

        q = Question(bank_id=bank.id, question_type="ES", content="Giải bài toán")
        q.set_accepted_answers(
            {
                "kind": "problem",
                "answers": ["Bước 1", "Bước 2"],
                "rubric": [
                    {"marker": "B1", "content": "Bước 1", "score": 1.0},
                    {"marker": "B2", "content": "Bước 2", "score": 2.0},
                ],
            }
        )
        db_session.add(q)
        db_session.flush()

        fetched = db_session.get(Question, q.id)
        assert fetched.is_problem_question() is True
        assert fetched.get_accepted_answers() == ["Bước 1", "Bước 2"]
        assert fetched.get_problem_rubric()[0]["marker"] == "B1"
        assert fetched.get_problem_template_name() == ""
        assert fetched.get_problem_template_id() is None

        q.set_accepted_answers(
            {
                "kind": "problem",
                "template_id": 7,
                "template_name": "Mẫu A",
                "answers": ["Bước 1"],
                "rubric": [{"marker": "B1", "content": "Bước 1", "score": 1.0}],
            }
        )
        db_session.flush()
        assert q.get_problem_template_id() == 7
        assert q.get_problem_template_name() == "Mẫu A"

    def test_problem_template_serialization(self, db_session):
        bank = QuestionBank(name="BankTemplate")
        db_session.add(bank)
        db_session.flush()

        template = QuestionRubricTemplate(
            bank_id=bank.id,
            name="Template A",
            template_payload="",
        )
        template.set_rows(
            [
                {"marker": "B1", "content": "Dòng 1", "score": 1.0},
                {"marker": "", "content": "Dòng 2", "score": 2.0},
            ]
        )
        db_session.add(template)
        db_session.flush()

        fetched = db_session.get(QuestionRubricTemplate, template.id)
        rows = fetched.get_rows()
        assert rows[0]["marker"] == "B1"
        assert rows[1]["content"] == "Dòng 2"

    def test_invalid_course_learning_outcomes_are_tolerated(self, db_session):
        bank = QuestionBank(name="BankBadCLO")
        bank.course_learning_outcomes = "{not-json"
        db_session.add(bank)
        db_session.flush()

        fetched = db_session.get(QuestionBank, bank.id)
        assert fetched.get_course_learning_outcomes() == []

    def test_cascade_delete_question_deletes_options(self, db_session):
        bank = QuestionBank(name="BankCascade")
        db_session.add(bank)
        db_session.flush()

        q = Question(bank_id=bank.id, question_type="MC", content="Delete me?")
        db_session.add(q)
        db_session.flush()

        opt = QuestionOption(
            question_id=q.id,
            option_key="A",
            option_text="Yes",
            is_correct=True,
            sort_order=0,
        )
        db_session.add(opt)
        db_session.flush()

        db_session.delete(q)
        db_session.flush()
        remaining = db_session.query(QuestionOption).filter_by(id=opt.id).first()
        assert remaining is None


class TestQuizAndAttempt:
    def _make_bank_and_quiz(self, db_session) -> tuple:
        bank = QuestionBank(name="QuizBank")
        db_session.add(bank)
        db_session.flush()
        quiz = Quiz(
            title="Sprint 1 Quiz",
            bank_id=bank.id,
            mode=QuizMode.STUDY.value,
            total_questions=5,
        )
        db_session.add(quiz)
        db_session.flush()
        return bank, quiz

    def test_create_quiz(self, db_session):
        _, quiz = self._make_bank_and_quiz(db_session)
        assert quiz.id is not None
        assert quiz.mode == "STUDY"

    def test_create_attempt(self, db_session):
        _, quiz = self._make_bank_and_quiz(db_session)
        attempt = Attempt(
            quiz_id=quiz.id,
            mode=QuizMode.STUDY.value,
            status=AttemptStatus.IN_PROGRESS.value,
        )
        db_session.add(attempt)
        db_session.flush()
        assert attempt.id is not None
        assert attempt.status == "IN_PROGRESS"


class TestAppSetting:
    def test_store_and_retrieve(self, db_session):
        setting = AppSetting(setting_key="theme", setting_value="dark")
        db_session.add(setting)
        db_session.flush()
        fetched = db_session.query(AppSetting).filter_by(setting_key="theme").first()
        assert fetched.setting_value == "dark"

    def test_unique_key_constraint(self, db_session):
        db_session.add(AppSetting(setting_key="dup", setting_value="1"))
        db_session.flush()
        db_session.add(AppSetting(setting_key="dup", setting_value="2"))
        with pytest.raises(Exception):
            db_session.flush()
