"""History service: read and manage attempt records.

Business rules (ARCHITECTURE §5.5):
  - EXAM:     do not reveal per-question correct/incorrect when
              displaying history detail without admin flag.
  - PRACTICE: summary totals only (correct / wrong / skipped).
  - STUDY:    per-question detail is stored and may be returned.

This service only supplies data; the presentation rules are enforced
by the UI layer (result_history_view.py / AttemptDetailDialog).
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session, joinedload

from core.database.models import Attempt, AttemptAnswer


def _score_pct(score: float, max_score: float) -> float:
    """Return score as a 0–100 percentage, rounded to 1 decimal."""
    if max_score and max_score > 0:
        return round(score / max_score * 100, 1)
    return 0.0


class HistoryService:
    """Stateless service for querying and deleting attempt history."""

    # ------------------------------------------------------------------
    # List
    # ------------------------------------------------------------------

    @staticmethod
    def list_attempts(session: Session, limit: int = 100) -> list[dict]:
        """Return attempt summaries ordered by started_at descending.

        Each dict contains: id, quiz_id, quiz_title, mode, status,
        started_at, submitted_at, duration_seconds, answered_count,
        correct_count, incorrect_count, skipped_count, score, max_score,
        score_pct.
        """
        rows = (
            session.query(Attempt)
            .options(joinedload(Attempt.quiz))
            .order_by(Attempt.started_at.desc())
            .limit(limit)
            .all()
        )
        return [HistoryService._attempt_summary(a) for a in rows]

    # ------------------------------------------------------------------
    # Detail
    # ------------------------------------------------------------------

    @staticmethod
    def get_attempt_detail(session: Session, attempt_id: int) -> dict | None:
        """Return full attempt data including sorted per-question answers.

        Returns None if attempt_id is not found.
        """
        attempt = (
            session.query(Attempt)
            .options(
                joinedload(Attempt.quiz),
                joinedload(Attempt.answers).joinedload(AttemptAnswer.quiz_question),
            )
            .filter(Attempt.id == attempt_id)
            .first()
        )
        if attempt is None:
            return None

        answers = []
        for aa in attempt.answers:
            qq = aa.quiz_question
            answers.append({
                "quiz_question_id": aa.quiz_question_id,
                "question_order": qq.question_order if qq else 0,
                "question_content": qq.snapshot_content if qq else "",
                "answer_payload": (
                    json.loads(aa.answer_payload) if aa.answer_payload else {}
                ),
                "is_answered": aa.is_answered,
                "is_correct": aa.is_correct,
                "score_awarded": aa.score_awarded,
                "feedback_state": aa.feedback_state or "pending",
            })
        answers.sort(key=lambda x: x["question_order"])

        summary = HistoryService._attempt_summary(attempt)
        summary["answers"] = answers
        return summary

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    @staticmethod
    def delete_attempt(session: Session, attempt_id: int) -> bool:
        """Delete an attempt (cascade-deletes its answers).

        Returns True if the attempt was found and deleted; False otherwise.
        """
        attempt = session.get(Attempt, attempt_id)
        if attempt is None:
            return False
        session.delete(attempt)
        session.flush()
        return True

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _attempt_summary(attempt: Attempt) -> dict:
        quiz_title = (
            attempt.quiz.title
            if attempt.quiz is not None
            else f"Quiz #{attempt.quiz_id}"
        )
        return {
            "id": attempt.id,
            "quiz_id": attempt.quiz_id,
            "quiz_title": quiz_title,
            "mode": attempt.mode,
            "status": attempt.status,
            "started_at": attempt.started_at,
            "submitted_at": attempt.submitted_at,
            "duration_seconds": attempt.duration_seconds,
            "answered_count": attempt.answered_count,
            "correct_count": attempt.correct_count,
            "incorrect_count": attempt.incorrect_count,
            "skipped_count": attempt.skipped_count,
            "score": attempt.score,
            "max_score": attempt.max_score,
            "score_pct": _score_pct(attempt.score, attempt.max_score),
        }
