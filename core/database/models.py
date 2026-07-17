"""SQLAlchemy ORM models for Quiz Desktop App.

Schema source of truth: QUIZ_APP_ARCHITECTURE.md §8.
Do not alter column names or constraints without creating an Alembic migration.

Eight tables:
    question_banks, questions, question_options,
    quizzes, quiz_questions,
    attempts, attempt_answers,
    app_settings
"""
from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


# ---------------------------------------------------------------------------
# question_banks
# ---------------------------------------------------------------------------

class QuestionBank(Base):
    """Stores question bank records (folders grouping questions)."""

    __tablename__ = "question_banks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    # Optional metadata used to pre-fill the exam export form
    school: Mapped[str | None] = mapped_column(Text)
    department: Mapped[str | None] = mapped_column(Text)
    subject: Mapped[str | None] = mapped_column(Text)
    course_code: Mapped[str | None] = mapped_column(Text)
    exam_title: Mapped[str | None] = mapped_column(Text)
    assessment_type: Mapped[str | None] = mapped_column(Text)
    course_learning_outcomes: Mapped[str | None] = mapped_column(Text)  # JSON list
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )

    questions: Mapped[list[Question]] = relationship(
        "Question", back_populates="bank", cascade="all, delete-orphan"
    )
    quizzes: Mapped[list[Quiz]] = relationship(
        "Quiz", back_populates="bank", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<QuestionBank id={self.id} name={self.name!r}>"

    def get_course_learning_outcomes(self) -> list[dict[str, str]]:
        """Deserialize CLO metadata into a Python list."""
        if not self.course_learning_outcomes:
            return []
        try:
            data = json.loads(self.course_learning_outcomes)
        except (TypeError, ValueError, json.JSONDecodeError):
            return []
        if not isinstance(data, list):
            return []
        items: list[dict[str, str]] = []
        for row in data:
            if not isinstance(row, dict):
                continue
            items.append(
                {
                    "code": str(row.get("code", "")).strip(),
                    "description": str(row.get("description", "")).strip(),
                }
            )
        return items

    def set_course_learning_outcomes(self, items: list[dict[str, str]]) -> None:
        """Serialize CLO metadata as JSON."""
        cleaned: list[dict[str, str]] = []
        for row in items:
            code = str(row.get("code", "")).strip()
            description = str(row.get("description", "")).strip()
            if not code and not description:
                continue
            cleaned.append({"code": code, "description": description})
        self.course_learning_outcomes = (
            json.dumps(cleaned, ensure_ascii=False) if cleaned else None
        )


# ---------------------------------------------------------------------------
# questions
# ---------------------------------------------------------------------------

class Question(Base):
    """Stores individual questions in a question bank."""

    __tablename__ = "questions"
    __table_args__ = (
        CheckConstraint(
            "question_type IN ('MC', 'MA', 'BLANK', 'TF', 'SA', 'ES', 'PR')",
            name="ck_questions_type",
        ),
        Index("ix_questions_bank_id", "bank_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bank_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("question_banks.id", ondelete="CASCADE"), nullable=False
    )
    question_code: Mapped[str | None] = mapped_column(Text, unique=True)
    question_type: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    hint: Mapped[str | None] = mapped_column(Text)
    explanation: Mapped[str | None] = mapped_column(Text)
    difficulty: Mapped[str | None] = mapped_column(Text)
    learning_outcome_code: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[str | None] = mapped_column(Text)
    # JSON string for BLANK/SA accepted answers; NULL for MC/MA
    accepted_answers: Mapped[str | None] = mapped_column(Text)
    point_value: Mapped[float] = mapped_column(Float, default=1.0)
    case_sensitive: Mapped[bool] = mapped_column(Boolean, default=False)
    trim_whitespace: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )

    bank: Mapped[QuestionBank] = relationship("QuestionBank", back_populates="questions")
    options: Mapped[list[QuestionOption]] = relationship(
        "QuestionOption", back_populates="question", cascade="all, delete-orphan",
        order_by="QuestionOption.sort_order",
    )

    def get_accepted_answer_payload(self) -> list[str] | dict[str, object]:
        """Deserialize the raw accepted-answers payload from JSON storage."""
        if not self.accepted_answers:
            return []
        return json.loads(self.accepted_answers)

    def get_accepted_answers(self) -> list[str]:
        """Return normalized accepted answers from list or structured payloads."""
        data = self.get_accepted_answer_payload()
        if isinstance(data, list):
            return [str(answer) for answer in data]
        if isinstance(data, dict):
            answers = data.get("answers", [])
            if not answers:
                rubric = data.get("rubric", [])
                if isinstance(rubric, list):
                    answers = [
                        str(row.get("content", "")).strip()
                        for row in rubric
                        if isinstance(row, dict) and str(row.get("content", "")).strip()
                    ]
            if isinstance(answers, list):
                return [str(answer) for answer in answers]
        return []

    def set_accepted_answers(self, answers: list[str] | dict[str, object]) -> None:
        """Serialize and store accepted answers as JSON."""
        self.accepted_answers = json.dumps(answers, ensure_ascii=False)

    def is_crq_question(self) -> bool:
        """Return whether this question uses the CRQ rubric payload format."""
        if self.question_type in {"ES", "PR"}:
            return True
        data = self.get_accepted_answer_payload()
        if not isinstance(data, dict):
            return False
        kind = str(data.get("kind", "")).strip().lower()
        return kind in {"problem", "crq"}

    def is_problem_question(self) -> bool:
        """Backward-compatible alias for legacy problem-style CRQ questions."""
        if self.question_type == "PR":
            return True
        data = self.get_accepted_answer_payload()
        if not isinstance(data, dict):
            return False
        kind = str(data.get("kind", "")).strip().lower()
        subtype = str(data.get("subtype", "")).strip().lower()
        if kind == "problem" and not subtype:
            return True
        return kind in {"problem", "crq"} and subtype in {"problem", "bai_toan"}

    def get_crq_subtype(self) -> str:
        """Return the CRQ subtype: essay or problem."""
        if self.question_type == "PR":
            return "problem"
        if self.question_type == "ES":
            data = self.get_accepted_answer_payload()
            if isinstance(data, dict):
                kind = str(data.get("kind", "")).strip().lower()
                subtype = str(data.get("subtype", "")).strip().lower()
                if subtype in {"essay", "problem"}:
                    return subtype
                if kind == "problem":
                    return "problem"
            return "essay"
        data = self.get_accepted_answer_payload()
        if isinstance(data, dict):
            kind = str(data.get("kind", "")).strip().lower()
            subtype = str(data.get("subtype", "")).strip().lower()
            if subtype in {"essay", "problem"}:
                return subtype
            if kind == "problem":
                return "problem"
        return ""

    def get_crq_rubric(self) -> list[dict[str, object]]:
        """Return structured rubric rows for CRQ questions."""
        data = self.get_accepted_answer_payload()
        if not isinstance(data, dict):
            return []
        rubric = data.get("rubric", [])
        return rubric if isinstance(rubric, list) else []

    def get_problem_rubric(self) -> list[dict[str, object]]:
        """Backward-compatible alias for CRQ rubric rows."""
        return self.get_crq_rubric()

    def get_crq_template_id(self) -> int | None:
        """Return the template id saved with a CRQ payload, if any."""
        data = self.get_accepted_answer_payload()
        if not isinstance(data, dict):
            return None
        raw = data.get("template_id")
        try:
            return int(raw) if raw is not None and str(raw).strip() else None
        except (TypeError, ValueError):
            return None

    def get_problem_template_id(self) -> int | None:
        """Backward-compatible alias for CRQ template id."""
        return self.get_crq_template_id()

    def get_crq_template_name(self) -> str:
        """Return the template name saved with a CRQ payload, if any."""
        data = self.get_accepted_answer_payload()
        if not isinstance(data, dict):
            return ""
        return str(data.get("template_name", "") or "").strip()

    def get_problem_template_name(self) -> str:
        """Backward-compatible alias for CRQ template name."""
        return self.get_crq_template_name()

    def __repr__(self) -> str:
        return f"<Question id={self.id} type={self.question_type} code={self.question_code!r}>"


# ---------------------------------------------------------------------------
# question_rubric_templates
# ---------------------------------------------------------------------------

class QuestionRubricTemplate(Base):
    """Stores reusable rubric templates for problem-style questions."""

    __tablename__ = "question_rubric_templates"
    __table_args__ = (
        UniqueConstraint("bank_id", "name", name="uq_question_rubric_templates_bank_name"),
        Index("ix_question_rubric_templates_bank_id", "bank_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bank_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("question_banks.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    template_payload: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )

    def get_rows(self) -> list[dict[str, object]]:
        """Deserialize template rows from the JSON payload."""
        if not self.template_payload:
            return []
        data = json.loads(self.template_payload)
        if isinstance(data, dict):
            rows = data.get("rows", [])
            if isinstance(rows, list):
                return rows
            return []
        if isinstance(data, list):
            return data
        return []

    def set_rows(self, rows: list[dict[str, object]]) -> None:
        """Serialize template rows into the JSON payload."""
        payload = {
            "version": 1,
            "rows": rows,
        }
        self.template_payload = json.dumps(payload, ensure_ascii=False)

    def __repr__(self) -> str:
        return f"<QuestionRubricTemplate id={self.id} bank_id={self.bank_id} name={self.name!r}>"


# ---------------------------------------------------------------------------
# question_options
# ---------------------------------------------------------------------------

class QuestionOption(Base):
    """Stores answer options for MC and MA questions."""

    __tablename__ = "question_options"
    __table_args__ = (
        UniqueConstraint("question_id", "option_key", name="uq_question_options_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    question_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False
    )
    option_key: Mapped[str] = mapped_column(Text, nullable=False)  # A, B, C, D, E, F
    option_text: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)

    question: Mapped[Question] = relationship("Question", back_populates="options")

    def __repr__(self) -> str:
        return (
            f"<QuestionOption id={self.id} key={self.option_key} "
            f"correct={self.is_correct}>"
        )


# ---------------------------------------------------------------------------
# quizzes
# ---------------------------------------------------------------------------

class Quiz(Base):
    """Stores quiz configurations created by the user."""

    __tablename__ = "quizzes"
    __table_args__ = (
        CheckConstraint(
            "mode IN ('EXAM', 'PRACTICE', 'STUDY')", name="ck_quizzes_mode"
        ),
        Index("ix_quizzes_bank_id", "bank_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    bank_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("question_banks.id", ondelete="CASCADE"), nullable=False
    )
    mode: Mapped[str] = mapped_column(Text, nullable=False)
    time_limit_minutes: Mapped[int | None] = mapped_column(Integer)
    shuffle_questions: Mapped[bool] = mapped_column(Boolean, default=True)
    shuffle_options: Mapped[bool] = mapped_column(Boolean, default=True)
    show_hint_in_practice: Mapped[bool] = mapped_column(Boolean, default=True)
    show_explanation_in_study: Mapped[bool] = mapped_column(Boolean, default=True)
    total_questions: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )

    bank: Mapped[QuestionBank] = relationship("QuestionBank", back_populates="quizzes")
    quiz_questions: Mapped[list[QuizQuestion]] = relationship(
        "QuizQuestion", back_populates="quiz", cascade="all, delete-orphan",
        order_by="QuizQuestion.question_order",
    )
    attempts: Mapped[list[Attempt]] = relationship(
        "Attempt", back_populates="quiz", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Quiz id={self.id} title={self.title!r} mode={self.mode}>"


# ---------------------------------------------------------------------------
# quiz_questions  (snapshot)
# ---------------------------------------------------------------------------

class QuizQuestion(Base):
    """Snapshot of each question as it was when the quiz was created."""

    __tablename__ = "quiz_questions"
    __table_args__ = (
        UniqueConstraint("quiz_id", "question_order", name="uq_quiz_questions_order"),
        Index("ix_quiz_questions_question_id", "question_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    quiz_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False
    )
    question_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False
    )
    question_order: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot_content: Mapped[str] = mapped_column(Text, nullable=False)
    snapshot_type: Mapped[str] = mapped_column(Text, nullable=False)
    snapshot_hint: Mapped[str | None] = mapped_column(Text)
    snapshot_explanation: Mapped[str | None] = mapped_column(Text)
    snapshot_point_value: Mapped[float] = mapped_column(Float, default=1.0)
    # JSON string – serialized list of {key, text, is_correct}
    snapshot_options: Mapped[str | None] = mapped_column(Text)
    # JSON string – list of accepted answer strings (for BLANK/SA)
    snapshot_accepted_answers: Mapped[str | None] = mapped_column(Text)

    quiz: Mapped[Quiz] = relationship("Quiz", back_populates="quiz_questions")
    attempt_answers: Mapped[list[AttemptAnswer]] = relationship(
        "AttemptAnswer", back_populates="quiz_question", cascade="all, delete-orphan"
    )

    def get_snapshot_options(self) -> list[dict]:
        """Deserialize snapshot_options JSON."""
        if not self.snapshot_options:
            return []
        return json.loads(self.snapshot_options)

    def get_snapshot_accepted_answers(self) -> list[str]:
        """Deserialize snapshot_accepted_answers JSON (back-compat: list or dict)."""
        if not self.snapshot_accepted_answers:
            return []
        data = json.loads(self.snapshot_accepted_answers)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("answers", [])
        return []

    def get_snapshot_answer_config(self) -> dict:
        """Return {case_sensitive, trim_whitespace} for BLANK/SA questions.

        Encoded as a JSON dict in snapshot_accepted_answers by QuizService.
        Falls back to safe defaults when not present.
        """
        if not self.snapshot_accepted_answers:
            return {"case_sensitive": False, "trim_whitespace": True}
        data = json.loads(self.snapshot_accepted_answers)
        if isinstance(data, dict):
            return {
                "case_sensitive": data.get("case_sensitive", False),
                "trim_whitespace": data.get("trim_whitespace", True),
            }
        return {"case_sensitive": False, "trim_whitespace": True}

    def __repr__(self) -> str:
        return (
            f"<QuizQuestion id={self.id} quiz={self.quiz_id} "
            f"order={self.question_order}>"
        )


# ---------------------------------------------------------------------------
# attempts
# ---------------------------------------------------------------------------

class Attempt(Base):
    """Records a single quiz session by a user."""

    __tablename__ = "attempts"
    __table_args__ = (
        CheckConstraint(
            "mode IN ('EXAM', 'PRACTICE', 'STUDY')", name="ck_attempts_mode"
        ),
        CheckConstraint(
            "status IN ('IN_PROGRESS', 'SUBMITTED', 'TIME_UP', 'COMPLETED')",
            name="ck_attempts_status",
        ),
        Index("ix_attempts_quiz_id", "quiz_id"),
        Index("ix_attempts_started_at", "started_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    quiz_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False
    )
    mode: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="IN_PROGRESS")
    started_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    answered_count: Mapped[int] = mapped_column(Integer, default=0)
    correct_count: Mapped[int] = mapped_column(Integer, default=0)
    incorrect_count: Mapped[int] = mapped_column(Integer, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    max_score: Mapped[float] = mapped_column(Float, default=0.0)
    remaining_seconds: Mapped[int | None] = mapped_column(Integer)
    extra_data: Mapped[str | None] = mapped_column(Text)  # JSON blob (renamed from metadata)

    quiz: Mapped[Quiz] = relationship("Quiz", back_populates="attempts")
    answers: Mapped[list[AttemptAnswer]] = relationship(
        "AttemptAnswer", back_populates="attempt", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Attempt id={self.id} quiz={self.quiz_id} status={self.status}>"


# ---------------------------------------------------------------------------
# attempt_answers
# ---------------------------------------------------------------------------

class AttemptAnswer(Base):
    """Stores the user's answer for each question in an attempt."""

    __tablename__ = "attempt_answers"
    __table_args__ = (
        UniqueConstraint(
            "attempt_id", "quiz_question_id", name="uq_attempt_answers_question"
        ),
        Index("ix_attempt_answers_quiz_question_id", "quiz_question_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    attempt_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("attempts.id", ondelete="CASCADE"), nullable=False
    )
    quiz_question_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("quiz_questions.id", ondelete="CASCADE"), nullable=False
    )
    # JSON string e.g. {"selected":"B"} or {"text":"EOQ"} – see ARCHITECTURE §8.4
    answer_payload: Mapped[str | None] = mapped_column(Text)
    is_answered: Mapped[bool] = mapped_column(Boolean, default=False)
    is_correct: Mapped[bool | None] = mapped_column(Boolean)
    score_awarded: Mapped[float] = mapped_column(Float, default=0.0)
    # One of: 'correct', 'incorrect', 'skipped', 'pending'
    feedback_state: Mapped[str | None] = mapped_column(Text)
    answered_at: Mapped[datetime | None] = mapped_column(DateTime)

    attempt: Mapped[Attempt] = relationship("Attempt", back_populates="answers")
    quiz_question: Mapped[QuizQuestion] = relationship(
        "QuizQuestion", back_populates="attempt_answers"
    )

    def __repr__(self) -> str:
        return (
            f"<AttemptAnswer id={self.id} attempt={self.attempt_id} "
            f"qq={self.quiz_question_id} correct={self.is_correct}>"
        )


# ---------------------------------------------------------------------------
# app_settings
# ---------------------------------------------------------------------------

class AppSetting(Base):
    """Key-value table for persistent application settings."""

    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    setting_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    setting_value: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )

    def __repr__(self) -> str:
        return f"<AppSetting {self.setting_key}={self.setting_value!r}>"
