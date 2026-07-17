"""Shared DTOs for quiz lifecycle services."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class QuizConfig:
    """DTO for creating a new quiz and its question snapshot."""

    title: str
    bank_id: int
    mode: str
    time_limit_minutes: int | None
    question_count: int
    shuffle_questions: bool = True
    shuffle_options: bool = True
    show_hint_in_practice: bool = True
    show_explanation_in_study: bool = True


@dataclass
class GradedRow:
    """One graded answer, used to finalise an attempt."""

    quiz_question_id: int
    answer_payload: dict
    is_correct: bool | None
    score_awarded: float
    feedback_state: str


@dataclass
class QuizQuestionSnapshot:
    """Typed runtime snapshot of a quiz question."""

    quiz_question_id: int
    order: int
    content: str
    type: str
    hint: str = ""
    explanation: str = ""
    point_value: float = 1.0
    options: list = field(default_factory=list)
    accepted_answers: list | None = None
    case_sensitive: bool = False
    trim_whitespace: bool = True
    question_code: str | None = None


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
    accepted_answers: list | None = None
    case_sensitive: bool = False
    trim_whitespace: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> QuizCreationSnapshot:
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
    time_limit: int | None
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
