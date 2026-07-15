"""Implementation helpers for quiz lifecycle service."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from core.database.models import Attempt, AttemptAnswer, Quiz, QuizQuestion
from core.domain.services.quiz_service_types import (
    AttemptResumeDTO,
    GradedRow,
    QuizConfig,
    QuizCreationSnapshot,
    QuizInfoDTO,
    QuizQuestionSnapshot,
)
from core.utils.constants import AttemptStatus, QuizMode
from modules.grading.evaluators import GradeResult, GradingEngine


class QuizCatalogService:
    """Quiz definition and snapshot persistence helpers."""

    @staticmethod
    def create_quiz(
        session: Session,
        config: QuizConfig,
        question_snapshots: list[QuizCreationSnapshot | dict],
    ) -> Quiz:
        typed_snapshots: list[QuizCreationSnapshot] = []
        for snap in question_snapshots:
            if isinstance(snap, QuizCreationSnapshot):
                typed_snapshots.append(snap)
            else:
                typed_snapshots.append(QuizCreationSnapshot.from_dict(snap))

        QuizCatalogService._validate_config(config, len(typed_snapshots))

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
            if qtype in ("BLANK", "SA", "ES", "PR") and snap.accepted_answers:
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

    @staticmethod
    def get_quiz(session: Session, quiz_id: int) -> Quiz:
        q = session.get(Quiz, quiz_id)
        if q is None:
            raise ValueError(f"Không tìm thấy quiz id={quiz_id}.")
        return q

    @staticmethod
    def get_quiz_info(session: Session, quiz_id: int) -> QuizInfoDTO:
        quiz = QuizCatalogService.get_quiz(session, quiz_id)
        return QuizInfoDTO(
            title=quiz.title,
            mode=quiz.mode,
            time_limit=quiz.time_limit_minutes,
            total=quiz.total_questions,
        )

    @staticmethod
    def get_quiz_questions(
        session: Session,
        quiz_id: int,
    ) -> list[QuizQuestion]:
        return (
            session.query(QuizQuestion)
            .filter_by(quiz_id=quiz_id)
            .order_by(QuizQuestion.question_order)
            .all()
        )

    @staticmethod
    def _validate_config(config: QuizConfig, question_count: int) -> None:
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


class QuizAttemptService:
    """Attempt lifecycle helpers for autosave/resume/finalize."""

    @staticmethod
    def create_attempt(
        session: Session,
        quiz_id: int,
        *,
        submitter_name: str = "",
        submitter_id: str = "",
        remaining_seconds: int | None = None,
    ) -> Attempt:
        quiz = QuizCatalogService.get_quiz(session, quiz_id)
        max_score = sum(qq.snapshot_point_value or 1.0 for qq in quiz.quiz_questions)
        extra_data = QuizAttemptService._build_attempt_extra_data(
            submitter_name,
            submitter_id,
        )

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

    @staticmethod
    def save_answer(
        session: Session,
        attempt_id: int,
        quiz_question_id: int,
        payload: dict,
    ) -> AttemptAnswer:
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

    @staticmethod
    def autosave_answers(
        session: Session,
        attempt_id: int,
        answers: dict[int, dict],
    ) -> None:
        for qq_id, payload in answers.items():
            if payload:
                QuizAttemptService.save_answer(session, attempt_id, qq_id, payload)

    @staticmethod
    def autosave_progress(
        session: Session,
        attempt_id: int,
        answers: dict[int, dict],
        remaining_seconds: int | None,
    ) -> None:
        attempt = session.get(Attempt, attempt_id)
        if attempt is None:
            raise ValueError(f"Không tìm thấy attempt id={attempt_id}.")
        attempt.remaining_seconds = remaining_seconds
        QuizAttemptService.autosave_answers(session, attempt_id, answers)

    @staticmethod
    def get_resumable_attempt(
        session: Session,
        quiz_id: int,
    ) -> AttemptResumeDTO | None:
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

        extra_data = QuizAttemptService._parse_attempt_extra_data(attempt.extra_data)
        return AttemptResumeDTO(
            attempt_id=attempt.id,
            quiz_id=attempt.quiz_id,
            started_at=QuizAttemptService._normalize_started_at(attempt.started_at),
            remaining_seconds=attempt.remaining_seconds,
            submitter_name=extra_data.get("submitter_name", ""),
            submitter_id=extra_data.get("submitter_id", ""),
            answers=answers,
        )

    @staticmethod
    def delete_attempt(session: Session, attempt_id: int) -> bool:
        attempt = session.get(Attempt, attempt_id)
        if attempt is None:
            return False
        session.delete(attempt)
        session.flush()
        return True

    @staticmethod
    def finalize_attempt(
        session: Session,
        attempt_id: int,
        status: str,
        graded_rows: list[GradedRow],
        duration_seconds: int,
    ) -> Attempt:
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
                aa.answer_payload = json.dumps(row.answer_payload, ensure_ascii=False)
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


class QuizGradingService:
    """Grading helpers built on top of GradingEngine."""

    @staticmethod
    def grade_answer(qq, payload: dict) -> GradeResult:
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
