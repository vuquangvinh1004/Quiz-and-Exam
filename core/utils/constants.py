"""Application-wide constants and enumerations.

All enums for QuestionType, QuizMode and AttemptStatus must be defined here
and imported from here. Do not redefine them elsewhere.
"""
from __future__ import annotations

from enum import StrEnum


class QuestionType(StrEnum):
    """Types of questions supported by the application.

    DB stores short codes (MC, MA, BLANK, TF, SA, ES).
    Import files use the long form (multiple_choice, etc.) and
    the import parser is responsible for the mapping.
    """

    MULTIPLE_CHOICE = "MC"
    MULTIPLE_ANSWER = "MA"
    BLANK = "BLANK"
    TRUE_FALSE = "TF"
    SHORT_ANSWER = "SA"
    ESSAY = "ES"
    PROBLEM = "PR"


class QuestionFamily(StrEnum):
    """Higher-level question families used for grouped UI labels."""

    CONSTRUCTED_RESPONSE = "CRQ"


# Mapping from import-format long names to internal DB codes
QUESTION_TYPE_IMPORT_MAP: dict[str, QuestionType] = {
    "multiple_choice": QuestionType.MULTIPLE_CHOICE,
    "multiple_answer": QuestionType.MULTIPLE_ANSWER,
    "blank": QuestionType.BLANK,
    "true_false": QuestionType.TRUE_FALSE,
    "short_answer": QuestionType.SHORT_ANSWER,
    "essay": QuestionType.ESSAY,
    "problem": QuestionType.PROBLEM,
}


CRQ_QUESTION_TYPES: tuple[QuestionType, ...] = (
    QuestionType.ESSAY,
    QuestionType.PROBLEM,
)


def is_crq_question_type(value: QuestionType | str) -> bool:
    """Return whether *value* belongs to the constructed-response family."""
    raw = value.value if isinstance(value, QuestionType) else str(value)
    return raw in {qt.value for qt in CRQ_QUESTION_TYPES}


class QuizMode(StrEnum):
    """The three quiz modes with distinct business rules."""

    EXAM = "EXAM"
    PRACTICE = "PRACTICE"
    STUDY = "STUDY"


class AttemptStatus(StrEnum):
    """Lifecycle states for a quiz attempt."""

    IN_PROGRESS = "IN_PROGRESS"
    SUBMITTED = "SUBMITTED"
    TIME_UP = "TIME_UP"
    COMPLETED = "COMPLETED"


class Difficulty(StrEnum):
    """Question difficulty levels (matches import format)."""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class QuestionStatus(StrEnum):
    """Active/inactive flag for a question."""

    ACTIVE = "active"
    INACTIVE = "inactive"


# Option labels allowed in import and answer payloads
VALID_OPTION_LABELS: tuple[str, ...] = ("A", "B", "C", "D", "E", "F")

# Import delimiter for multi-value fields (e.g. correct_answers for MA/BLANK/SA)
MULTI_VALUE_DELIMITER: str = "||"

# Canonical placeholder used in Blank question text (per import spec)
BLANK_PLACEHOLDER: str = "[[blank]]"
# Backward-compatible legacy placeholder accepted during migration period.
LEGACY_BLANK_PLACEHOLDER: str = "________"

# Default values
DEFAULT_SCORE: float = 1.0
DEFAULT_DIFFICULTY: Difficulty = Difficulty.MEDIUM
DEFAULT_STATUS: QuestionStatus = QuestionStatus.ACTIVE
