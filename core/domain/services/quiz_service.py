"""Quiz lifecycle service: create quizzes, manage attempts and answers.

Business rules enforced (ARCHITECTURE §5.2, §7):
  - EXAM and PRACTICE require time_limit_minutes > 0.
  - STUDY must have time_limit_minutes = None (no timer).
  - A quiz must contain at least 1 question.
  - Attempt answers are pre-created as un-answered rows when attempt starts.
  - Grading is per-question using snapshot data (no extra DB query needed).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from core.database.models import Attempt, AttemptAnswer, Quiz, QuizQuestion
from core.utils.constants import AttemptStatus, QuizMode
from modules.grading.evaluators import GradeResult, GradingEngine


# ---------------------------------------------------------------------------
# Data transfer objects
# ---------------------------------------------------------------------------

@dataclass
class QuizConfig:
    """DTO for creating a new quiz and its question snapshot."""
    title: str
    bank_id: int
    mode: str                          # QuizMode value
    time_limit_minutes: Optional[int]  # None for STUDY
    question_count: int
    shuffle_questions: bool = True
    shuffle_options: bool = True
    show_hint_in_practice: bool = True
    show_explanation_in_study: bool = True


@dataclass
class GradedRow:
    """One graded answer, used to finalise an attempt."""
    quiz_question_id: int
    answer_payload: dict            # raw payload as stored / displayed
    is_correct: Optional[bool]
    score_awarded: float
    feedback_state: str             # "correct" | "incorrect" | "skipped"


@dataclass
class QuizQuestionSnapshot:
    """Typed runtime snapshot of a quiz question.

    Built from ORM QuizQuestion data by the session controller and passed
    through the runner pipeline instead of raw dicts, enabling static type
    checking and IDE auto-complete.
    """

    quiz_question_id: int
    order: int
    content: str
    type: str                               # QuizType value: MC | MA | BLANK | TF | SA | ES
    hint: str = ""
    explanation: str = ""
    point_value: float = 1.0
    options: list = field(default_factory=list)   # list[{"key": str, "text": str}]
    accepted_answers: Optional[list] = None
    case_sensitive: bool = False
    trim_whitespace: bool = True
    question_code: Optional[str] = None


@dataclass
class QuizCreationSnapshot:
    """Typed snapshot payload used when creating quiz_questions rows."""

    question_id: int
    content: str
    type: str
    hint: str = ""
    explanation: str = ""
    point_value: float = 1.0
    options: list = field(default_factory=list)
    accepted_answers: Optional[list] = None
    case_sensitive: bool = False
    trim_whitespace: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> "QuizCreationSnapshot":
        """Adapter for legacy dict snapshots during migration period."""
        return cls(
            question_id=data["question_id"],
            content=data["content"],
            type=data["type"],
            hint=data.get("hint") or "",
            explanation=data.get("explanation") or "",
            point_value=data.get("point_value", 1.0),
            options=data.get("options") or [],
            accepted_answers=data.get("accepted_answers"),
            case_sensitive=data.get("case_sensitive", False),
            trim_whitespace=data.get("trim_whitespace", True),
        )


@dataclass
class QuizInfoDTO:
    """Lightweight quiz setup info for runner setup screen."""

    title: str
    mode: str
    time_limit: Optional[int]
    total: int


@dataclass
class AttemptResumeDTO:
    """Persisted in-progress attempt data needed to resume a session."""

    attempt_id: int
    quiz_id: int
    started_at: datetime | None
    remaining_seconds: int | None
    submitter_name: str = ""
    submitter_id: str = ""
    answers: dict[int, dict] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class QuizService:
    """Encapsulates quiz creation, attempt management and basic grading."""

    # -----------------------------------------------------------------------
    # Quiz creation
    # -----------------------------------------------------------------------

    def create_quiz(
        self,
        session: Session,
        config: QuizConfig,
        question_snapshots: list[QuizCreationSnapshot | dict],
    ) -> Quiz:
        """Persist a Quiz record plus one QuizQuestion row per snapshot.

        Parameters
        ----------
        question_snapshots:
            Preferred input is list[QuizCreationSnapshot]. Legacy dict snapshots
            are still accepted for backward compatibility.
        """
        typed_snapshots: list[QuizCreationSnapshot] = []
        for snap in question_snapshots:
            if isinstance(snap, QuizCreationSnapshot):
                typed_snapshots.append(snap)
            else:
                typed_snapshots.append(QuizCreationSnapshot.from_dict(snap))

        self._validate_config(config, len(typed_snapshots))

        quiz = Quiz(
            title=config.title.strip(),
            bank_id=config.bank_id,
            mode=config.mode,
            time_limit_minutes=config.time_limit_minutes,
            shuffle_questions=config.shuffle_questions,
            shuffle_options=config.shuffle_options,
            show_hint_in_practice=config.show_hint_in_practice,
            show_explanation_in_study=config.show_explanation_in_study,
            total_questions=len(typed_snapshots),
        )
        session.add(quiz)
        session.flush()

        for order, snap in enumerate(typed_snapshots, start=1):
            qtype = snap.type
            # For BLANK/SA/ES encode accepted_answers together with matching config
            # so the grader can work from the snapshot alone (no live Question needed).
            if qtype in ("BLANK", "SA", "ES") and snap.accepted_answers:
                sa_json = json.dumps(
                    {
                        "answers": snap.accepted_answers,
                        "case_sensitive": snap.case_sensitive,
                        "trim_whitespace": snap.trim_whitespace,
                    },
                    ensure_ascii=False,
                )
            else:
                sa_json = None

            opt_json = (
                json.dumps(snap.options, ensure_ascii=False)
                if snap.options
                else None
            )

            qq = QuizQuestion(
                quiz_id=quiz.id,
                question_id=snap.question_id,
                question_order=order,
                snapshot_content=snap.content,
                snapshot_type=qtype,
                snapshot_hint=snap.hint or None,
                snapshot_explanation=snap.explanation or None,
                snapshot_point_value=snap.point_value,
                snapshot_options=opt_json,
                snapshot_accepted_answers=sa_json,
            )
            session.add(qq)

        session.flush()
        return quiz

    def get_quiz(self, session: Session, quiz_id: int) -> Quiz:
        q = session.get(Quiz, quiz_id)
        if q is None:
            raise ValueError(f"Không tìm thấy quiz id={quiz_id}.")
        return q

    def get_quiz_info(self, session: Session, quiz_id: int) -> QuizInfoDTO:
        """Return typed setup info for quiz runner initialization."""
        quiz = self.get_quiz(session, quiz_id)
        return QuizInfoDTO(
            title=quiz.title,
            mode=quiz.mode,
            time_limit=quiz.time_limit_minutes,
            total=quiz.total_questions,
        )

    def get_quiz_questions(
        self, session: Session, quiz_id: int
    ) -> list[QuizQuestion]:
        return (
            session.query(QuizQuestion)
            .filter_by(quiz_id=quiz_id)
            .order_by(QuizQuestion.question_order)
            .all()
        )

    # -----------------------------------------------------------------------
    # Attempt management
    # -----------------------------------------------------------------------

    def create_attempt(
        self,
        session: Session,
        quiz_id: int,
        *,
        submitter_name: str = "",
        submitter_id: str = "",
        remaining_seconds: int | None = None,
    ) -> Attempt:
        """Create an attempt and pre-populate AttemptAnswer rows."""
        quiz = self.get_quiz(session, quiz_id)
        max_score = sum(qq.snapshot_point_value or 1.0 for qq in quiz.quiz_questions)
        extra_data = self._build_attempt_extra_data(submitter_name, submitter_id)

        attempt = Attempt(
            quiz_id=quiz_id,
            mode=quiz.mode,
            status=AttemptStatus.IN_PROGRESS.value,
            max_score=max_score,
            answered_count=0,
            correct_count=0,
            incorrect_count=0,
            skipped_count=0,
            score=0.0,
            remaining_seconds=remaining_seconds,
            extra_data=extra_data,
        )
        session.add(attempt)
        session.flush()

        for qq in quiz.quiz_questions:
            session.add(
                AttemptAnswer(
                    attempt_id=attempt.id,
                    quiz_question_id=qq.id,
                    is_answered=False,
                )
            )
        session.flush()

        return attempt

    def save_answer(
        self,
        session: Session,
        attempt_id: int,
        quiz_question_id: int,
        payload: dict,
    ) -> AttemptAnswer:
        """Upsert a single answer payload for one quiz question."""
        aa = (
            session.query(AttemptAnswer)
            .filter_by(attempt_id=attempt_id, quiz_question_id=quiz_question_id)
            .first()
        )
        if aa is None:
            aa = AttemptAnswer(
                attempt_id=attempt_id, quiz_question_id=quiz_question_id
            )
            session.add(aa)
        aa.answer_payload = (
            json.dumps(payload, ensure_ascii=False) if payload else None
        )
        aa.is_answered = bool(payload)
        aa.answered_at = datetime.now(timezone.utc)
        session.flush()
        return aa

    def autosave_answers(
        self,
        session: Session,
        attempt_id: int,
        answers: dict[int, dict],
    ) -> None:
        """Batch-upsert in-progress answers. Called by the autosave timer."""
        for qq_id, payload in answers.items():
            if payload:
                self.save_answer(session, attempt_id, qq_id, payload)

    def autosave_progress(
        self,
        session: Session,
        attempt_id: int,
        answers: dict[int, dict],
        remaining_seconds: int | None,
    ) -> None:
        """Persist in-progress answers together with timer state."""
        attempt = session.get(Attempt, attempt_id)
        if attempt is None:
            raise ValueError(f"Không tìm thấy attempt id={attempt_id}.")
        attempt.remaining_seconds = remaining_seconds
        self.autosave_answers(session, attempt_id, answers)

    def get_resumable_attempt(
        self,
        session: Session,
        quiz_id: int,
    ) -> AttemptResumeDTO | None:
        """Return the latest in-progress attempt for one quiz, if any."""
        attempt = (
            session.query(Attempt)
            .filter_by(quiz_id=quiz_id, status=AttemptStatus.IN_PROGRESS.value)
            .order_by(Attempt.started_at.desc(), Attempt.id.desc())
            .first()
        )
        if attempt is None:
            return None

        answers: dict[int, dict] = {}
        for row in attempt.answers:
            if not row.answer_payload:
                continue
            try:
                payload = json.loads(row.answer_payload)
            except json.JSONDecodeError:
                continue
            if payload:
                answers[row.quiz_question_id] = payload

        extra_data = self._parse_attempt_extra_data(attempt.extra_data)
        return AttemptResumeDTO(
            attempt_id=attempt.id,
            quiz_id=attempt.quiz_id,
            started_at=self._normalize_started_at(attempt.started_at),
            remaining_seconds=attempt.remaining_seconds,
            submitter_name=extra_data.get("submitter_name", ""),
            submitter_id=extra_data.get("submitter_id", ""),
            answers=answers,
        )

    def delete_attempt(self, session: Session, attempt_id: int) -> bool:
        """Delete an attempt and its answers. Returns False if missing."""
        attempt = session.get(Attempt, attempt_id)
        if attempt is None:
            return False
        session.delete(attempt)
        session.flush()
        return True

    def finalize_attempt(
        self,
        session: Session,
        attempt_id: int,
        status: str,
        graded_rows: list[GradedRow],
        duration_seconds: int,
    ) -> Attempt:
        """Write grading results and close the attempt."""
        attempt = session.get(Attempt, attempt_id)
        if attempt is None:
            raise ValueError(f"Không tìm thấy attempt id={attempt_id}.")

        answered = correct = incorrect = skipped = 0
        total_score = 0.0

        for row in graded_rows:
            aa = (
                session.query(AttemptAnswer)
                .filter_by(
                    attempt_id=attempt_id, quiz_question_id=row.quiz_question_id
                )
                .first()
            )
            if aa:
                aa.answer_payload = json.dumps(
                    row.answer_payload, ensure_ascii=False
                )
                aa.is_answered = row.feedback_state != "skipped"
                aa.is_correct = row.is_correct
                aa.score_awarded = row.score_awarded
                aa.feedback_state = row.feedback_state
                aa.answered_at = aa.answered_at or datetime.now(timezone.utc)

            if row.feedback_state == "skipped":
                skipped += 1
            elif row.is_correct:
                correct += 1
                answered += 1
            else:
                incorrect += 1
                answered += 1
            total_score += row.score_awarded

        attempt.status = status
        attempt.submitted_at = datetime.now(timezone.utc)
        attempt.duration_seconds = duration_seconds
        attempt.remaining_seconds = 0
        attempt.answered_count = answered
        attempt.correct_count = correct
        attempt.incorrect_count = incorrect
        attempt.skipped_count = skipped
        attempt.score = total_score
        return attempt

    # -----------------------------------------------------------------------
    # Grading – delegates to GradingEngine (modules.grading.evaluators)
    # -----------------------------------------------------------------------

    @staticmethod
    def grade_answer(qq: QuizQuestion, payload: dict) -> GradeResult:
        """Grade one answer using ORM snapshot data.

        Converts the ORM object fields into a snapshot dict and delegates
        to ``GradingEngine.grade_from_dict``.
        """
        qq_dict = {
            "type": qq.snapshot_type,
            "content": qq.snapshot_content or "",
            "point_value": qq.snapshot_point_value or 1.0,
            "options": qq.get_snapshot_options(),
            "accepted_answers": qq.get_snapshot_accepted_answers(),
            "case_sensitive": qq.get_snapshot_answer_config().get("case_sensitive", False),
            "trim_whitespace": qq.get_snapshot_answer_config().get("trim_whitespace", True),
        }
        return GradingEngine.grade_from_dict(qq_dict, payload)

    @staticmethod
    def grade_answer_from_dict(
        qq_dict: dict | QuizQuestionSnapshot,
        payload: dict,
    ) -> GradeResult:
        """Grade from a snapshot dict or QuizQuestionSnapshot (no ORM needed).

        Accepts either a raw ``dict`` (legacy callers, test fixtures) or a
        typed ``QuizQuestionSnapshot`` produced by the session controller.
        Delegates to ``GradingEngine.grade_from_dict``.
        """
        if isinstance(qq_dict, QuizQuestionSnapshot):
            qq_dict = {
                "type": qq_dict.type,
                "content": qq_dict.content,
                "point_value": qq_dict.point_value,
                "options": qq_dict.options,
                "accepted_answers": qq_dict.accepted_answers,
                "case_sensitive": qq_dict.case_sensitive,
                "trim_whitespace": qq_dict.trim_whitespace,
            }
        return GradingEngine.grade_from_dict(qq_dict, payload)

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    def _validate_config(self, config: QuizConfig, question_count: int) -> None:
        if not config.title.strip():
            raise ValueError("Tên bài kiểm tra không được để trống.")
        if config.mode not in (m.value for m in QuizMode):
            raise ValueError(f"Mode không hợp lệ: {config.mode}")
        if config.mode in (QuizMode.EXAM.value, QuizMode.PRACTICE.value):
            if not config.time_limit_minutes or config.time_limit_minutes <= 0:
                raise ValueError(
                    "Chế độ Kiểm tra và Luyện tập cần giới hạn thời gian > 0 phút."
                )
        if question_count < 1:
            raise ValueError("Bài kiểm tra cần ít nhất 1 câu hỏi.")

    @staticmethod
    def _build_attempt_extra_data(submitter_name: str, submitter_id: str) -> str | None:
        if not submitter_name and not submitter_id:
            return None
        return json.dumps(
            {
                "submitter_name": submitter_name,
                "submitter_id": submitter_id,
            },
            ensure_ascii=False,
        )

    @staticmethod
    def _parse_attempt_extra_data(extra_data: str | None) -> dict:
        if not extra_data:
            return {}
        try:
            parsed = json.loads(extra_data)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    @staticmethod
    def _normalize_started_at(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
