"""Domain-level validators shared across layers.

These are pure functions that return validation results rather than raising
exceptions, so callers can aggregate errors before deciding how to fail.
"""
from __future__ import annotations

from core.utils.constants import (
    BLANK_PLACEHOLDER,
    LEGACY_BLANK_PLACEHOLDER,
    MULTI_VALUE_DELIMITER,
    VALID_OPTION_LABELS,
    QuestionType,
)


def is_valid_option_label(label: str) -> bool:
    """Return True if *label* is one of A–F (case-insensitive)."""
    return label.strip().upper() in VALID_OPTION_LABELS


def count_blank_placeholders(question_text: str) -> int:
    """Count BLANK placeholders (canonical + legacy for compatibility)."""
    text = question_text.lower()
    return (
        text.count(BLANK_PLACEHOLDER.lower())
        + text.count(LEGACY_BLANK_PLACEHOLDER.lower())
    )


def validate_correct_answers_for_type(
    question_type: QuestionType,
    correct_answers_raw: str,
    option_labels_present: list[str],
) -> list[str]:
    """Validate ``correct_answers`` for a given question type.

    Args:
        question_type:         One of the QuestionType enum values.
        correct_answers_raw:   Raw string from import column.
        option_labels_present: Non-empty option labels available (e.g. ['A','B','C']).

    Returns:
        List of error message strings.  Empty list means no errors.
    """
    errors: list[str] = []
    tokens = [t.strip().upper() for t in correct_answers_raw.split(MULTI_VALUE_DELIMITER) if t.strip()]

    if not tokens:
        errors.append("correct_answers must not be empty.")
        return errors

    if question_type == QuestionType.MULTIPLE_CHOICE:
        if len(tokens) != 1:
            errors.append(
                f"multiple_choice requires exactly 1 correct answer; got {len(tokens)}."
            )
        for tok in tokens:
            if tok not in [lbl.upper() for lbl in option_labels_present]:
                errors.append(f"Correct answer '{tok}' references a non-existent option.")

    elif question_type == QuestionType.MULTIPLE_ANSWER:
        if len(tokens) < 2:
            errors.append(
                f"multiple_answer requires at least 2 correct answers; got {len(tokens)}."
            )
        seen: set[str] = set()
        for tok in tokens:
            if tok in seen:
                errors.append(f"Duplicate correct answer '{tok}'.")
            seen.add(tok)
            if tok not in [lbl.upper() for lbl in option_labels_present]:
                errors.append(f"Correct answer '{tok}' references a non-existent option.")

    # BLANK / SHORT_ANSWER / ESSAY: just need at least one non-empty value; already confirmed above.
    elif question_type == QuestionType.TRUE_FALSE:
        if len(tokens) != 1:
            errors.append(
                f"true_false requires exactly 1 correct answer; got {len(tokens)}."
            )
        for tok in tokens:
            if tok not in [lbl.upper() for lbl in option_labels_present]:
                errors.append(f"Correct answer '{tok}' references a non-existent option.")

    return errors
