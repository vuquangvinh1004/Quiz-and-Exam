"""Submit handler — pure Python grading + result assembly.

Pulled out of QuizRunnerView so grading logic is testable without UI.

Public API:
    build_graded_result(...)  -> tuple[list[GradedRow], AttemptResultData]
    payload_display(qtype, payload) -> str
"""
from __future__ import annotations

from datetime import datetime, timezone

from core.domain.services.quiz_service import GradedRow, QuizQuestionSnapshot, QuizService
from modules.grading.result_builder import AttemptResultData, QuestionResultRow


def payload_display(qtype: str, payload: dict) -> str:
    """Human-readable answer text for a given payload."""
    if not payload:
        return "Bỏ qua"
    if qtype == "MC":
        return payload.get("selected", "\u2014")
    if qtype == "MA":
        selected = payload.get("selected", [])
        return ", ".join(selected) if selected else "\u2014"
    return payload.get("text", "\u2014")


def build_graded_result(
    quiz_questions: list[QuizQuestionSnapshot],
    answers: dict[int, dict],
    started_at: datetime | None,
    submitter_name: str,
    submitter_id: str,
    quiz_title: str,
    mode: str,
) -> tuple[list[GradedRow], AttemptResultData]:
    """Grade all questions and assemble AttemptResultData.

    Returns:
        (graded_rows, result_data) — graded_rows for DB persistence,
        result_data for UI display.
    """
    submitted_at = datetime.now(timezone.utc)
    duration = int(
        (submitted_at - started_at).total_seconds()
        if started_at
        else 0
    )

    graded_rows: list[GradedRow] = []
    result_rows: list[QuestionResultRow] = []

    for qq in quiz_questions:
        qid = qq.quiz_question_id
        payload = answers.get(qid, {})
        grade = QuizService.grade_answer_from_dict(qq, payload)

        graded_rows.append(
            GradedRow(
                quiz_question_id=qid,
                answer_payload=payload,
                is_correct=grade.is_correct,
                score_awarded=grade.score_awarded,
                feedback_state=grade.feedback_state,
            )
        )
        result_rows.append(
            QuestionResultRow(
                order=qq.order,
                question_text=qq.content,
                answer_text=payload_display(qq.type, payload),
                is_correct=grade.is_correct,
                score_awarded=grade.score_awarded,
                max_score=qq.point_value,
                question_code=qq.question_code,
                correct_answer_display=grade.correct_answer_display,
            )
        )

    correct_count = sum(1 for r in result_rows if r.is_correct)
    incorrect_count = sum(1 for r in result_rows if r.is_correct is False)
    skipped_count = sum(1 for r in result_rows if r.is_correct is None)
    total_score = sum(r.score_awarded for r in result_rows)
    max_score = sum(r.max_score for r in result_rows)

    result_data = AttemptResultData(
        submitter_name=submitter_name or "\u2014",
        submitter_id=submitter_id or "\u2014",
        quiz_title=quiz_title,
        mode=mode,
        started_at=started_at or submitted_at,
        submitted_at=submitted_at,
        duration_seconds=duration,
        score=total_score,
        max_score=max_score,
        correct_count=correct_count,
        incorrect_count=incorrect_count,
        skipped_count=skipped_count,
        questions=result_rows,
    )

    return graded_rows, result_data
