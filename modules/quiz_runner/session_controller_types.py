"""Shared DTOs for quiz runner session control."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from core.domain.services.quiz_service import AttemptResumeDTO, QuizQuestionSnapshot


@dataclass
class PreparedAttemptSession:
    """Typed runtime bundle returned to the quiz runner view."""

    snapshots: list[QuizQuestionSnapshot]
    attempt_id: int
    answers: dict[int, dict]
    started_at: datetime | None
    remaining_seconds: int | None
    submitter_name: str = ""
    submitter_id: str = ""
    resumed: bool = False

    @classmethod
    def from_resume(
        cls,
        resume: AttemptResumeDTO,
        snapshots: list[QuizQuestionSnapshot],
    ) -> "PreparedAttemptSession":
        return cls(
            snapshots=snapshots,
            attempt_id=resume.attempt_id,
            answers=resume.answers,
            started_at=resume.started_at,
            remaining_seconds=resume.remaining_seconds,
            submitter_name=resume.submitter_name,
            submitter_id=resume.submitter_id,
            resumed=True,
        )
