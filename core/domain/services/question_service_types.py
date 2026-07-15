"""Shared DTOs for question-bank services."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from core.utils.constants import DEFAULT_DIFFICULTY, DEFAULT_SCORE, DEFAULT_STATUS, QuestionType


@dataclass
class BankStats:
    bank_id: int
    bank_name: str
    question_count: int


@dataclass
class BankOverviewRow:
    bank_id: int
    bank_name: str
    assessment_type: str
    course_learning_outcomes: list[dict[str, str]]
    question_count: int


@dataclass
class ProblemRubricRow:
    """One accepted-answer rubric row for problem-style essay questions."""

    marker: str = ""
    content: str = ""
    score: float = 0.0


@dataclass
class ProblemRubricTemplateSummary:
    """Lightweight template metadata for template pickers."""

    template_id: int
    bank_id: int
    name: str
    row_count: int
    total_score: float


@dataclass
class ProblemRubricTemplateData:
    """Full template payload used when loading a saved rubric template."""

    template_id: int
    bank_id: int
    name: str
    rows: list[ProblemRubricRow] = field(default_factory=list)


@dataclass
class ProblemRubricTemplateMeta:
    """Template provenance stored alongside a problem rubric payload."""

    template_id: int | None = None
    template_name: str = ""


@dataclass
class QuestionEditData:
    """DTO used to create or update a question via the editor dialog."""

    bank_id: int
    question_type: QuestionType
    content: str
    difficulty: str = field(default_factory=lambda: DEFAULT_DIFFICULTY.value)
    score: float = DEFAULT_SCORE
    hint: str = ""
    explanation: str = ""
    learning_outcome_code: str = ""
    category: str = ""
    tags: str = ""
    status: str = field(default_factory=lambda: DEFAULT_STATUS.value)
    case_sensitive: bool = False
    trim_whitespace: bool = True
    question_code: str = ""
    options: list[tuple[str, str, bool]] = field(default_factory=list)
    accepted_answers: list[str] = field(default_factory=list)
    editor_variant: str = "standard"
    problem_rubric: list[ProblemRubricRow] = field(default_factory=list)
    problem_template_id: int | None = None
    problem_template_name: str = ""


@dataclass
class QuestionTypeBreakdown:
    mc: int = 0
    ma: int = 0
    blank: int = 0
    tf: int = 0
    sa: int = 0
    es: int = 0


@dataclass
class QuestionUsageRow:
    question_id: int
    question_code: str
    question_type: str
    learning_outcome_code: str
    difficulty: str
    point_value: float
    is_active: bool
    content: str
    used_count: int
    correct_count: int


@dataclass
class QuestionUsageSummary:
    total_questions: int
    active_questions: int
    total_uses: int
    total_correct: int
    type_breakdown: QuestionTypeBreakdown
    difficulty_breakdown: dict[str, int] = field(default_factory=dict)
    learning_outcome_count: int = 0
    learning_outcome_top: list[tuple[str, int]] = field(default_factory=list)


__all__ = [
    "BankOverviewRow",
    "BankStats",
    "ProblemRubricRow",
    "ProblemRubricTemplateMeta",
    "ProblemRubricTemplateData",
    "ProblemRubricTemplateSummary",
    "QuestionEditData",
    "QuestionTypeBreakdown",
    "QuestionUsageRow",
    "QuestionUsageSummary",
]
