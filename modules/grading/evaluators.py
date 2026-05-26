"""Dedicated grading evaluators for each question type.

Each evaluator is a stateless class with a static ``grade`` method.
``GradingEngine`` dispatches to the correct evaluator based on question type.

Business rules enforced (ARCHITECTURE §5.4, §7.5):
    MC    : one correct option; payload ``selected`` must match exactly.
    MA    : selected set must equal correct set exactly (full-match v1.0).
    BLANK : text must match at least one accepted answer after normalisation.
            For multi-blank questions (blank_count > 1), the user separates
            answers with "||" and each part is matched positionally.
    SA    : identical grading logic to BLANK (separate class for clarity).

Normalisation rules applied when trimming/casing flags are set:
    trim_whitespace (default True)  – strip leading/trailing whitespace.
    case_sensitive  (default False) – compare case-insensitively.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core.utils.constants import MULTI_VALUE_DELIMITER
from core.utils.validators import count_blank_placeholders


# ---------------------------------------------------------------------------
# Result DTO
# ---------------------------------------------------------------------------

@dataclass
class GradeResult:
    """Immutable result of grading one answer.

    Attributes
    ----------
    is_correct:
        True = correct, False = incorrect, None = skipped / no payload.
    score_awarded:
        Points awarded.  Zero when incorrect or skipped.
    feedback_state:
        One of ``"correct"``, ``"incorrect"``, ``"skipped"``.
    correct_answer_display:
        Human-readable string of the correct answer(s).
        Used in STUDY-mode per-question feedback.
    """

    is_correct: Optional[bool]
    score_awarded: float
    feedback_state: str          # "correct" | "incorrect" | "skipped"
    correct_answer_display: str


# ---------------------------------------------------------------------------
# Evaluators
# ---------------------------------------------------------------------------

class MCEvaluator:
    """Evaluator for Multiple Choice questions."""

    @staticmethod
    def grade(options: list[dict], payload: dict, point_value: float) -> GradeResult:
        display = _mc_correct_display(options)
        if not payload:
            return GradeResult(None, 0.0, "skipped", display)

        selected = payload.get("selected", "")
        correct_keys = {o["key"] for o in options if o.get("is_correct")}
        is_correct = bool(selected) and selected in correct_keys
        return GradeResult(
            is_correct=is_correct,
            score_awarded=point_value if is_correct else 0.0,
            feedback_state="correct" if is_correct else "incorrect",
            correct_answer_display=display,
        )


class MAEvaluator:
    """Evaluator for Multiple Answer questions (full-match, v1.0 policy)."""

    @staticmethod
    def grade(options: list[dict], payload: dict, point_value: float) -> GradeResult:
        display = _ma_correct_display(options)
        if not payload:
            return GradeResult(None, 0.0, "skipped", display)

        selected = set(payload.get("selected", []))
        correct_keys = {o["key"] for o in options if o.get("is_correct")}
        # v1.0: full-match only – selected must equal correct_keys exactly
        is_correct = bool(selected) and selected == correct_keys
        return GradeResult(
            is_correct=is_correct,
            score_awarded=point_value if is_correct else 0.0,
            feedback_state="correct" if is_correct else "incorrect",
            correct_answer_display=display,
        )


class BlankEvaluator:
    """Evaluator for Blank (fill-in) questions.

    Single-blank: input is compared against all accepted answers (any match = correct).
    Multi-blank : input must be split by "||" into exactly len(accepted) parts;
                 each part is matched positionally against the corresponding
                 accepted answer.
    """

    @staticmethod
    def grade(
        accepted: list[str],
        case_sensitive: bool,
        trim_whitespace: bool,
        payload: dict,
        point_value: float,
        blank_count: int = 1,
    ) -> GradeResult:
        display = " / ".join(accepted[:3]) if accepted else "\u2014"

        if not payload:
            return GradeResult(None, 0.0, "skipped", display)

        text = payload.get("text", "")
        if not text:
            return GradeResult(None, 0.0, "skipped", display)

        if trim_whitespace:
            text = text.strip()

        # Multi-blank: split by delimiter, match each part positionally.
        if blank_count > 1:
            parts = [
                p.strip() if trim_whitespace else p
                for p in text.split(MULTI_VALUE_DELIMITER)
            ]
            if len(parts) != len(accepted):
                return GradeResult(False, 0.0, "incorrect", display)
            norm_accepted = [
                a.strip() if trim_whitespace else a for a in accepted
            ]
            if case_sensitive:
                is_correct = all(p == a for p, a in zip(parts, norm_accepted))
            else:
                is_correct = all(
                    p.lower() == a.lower() for p, a in zip(parts, norm_accepted)
                )
            return GradeResult(
                is_correct=is_correct,
                score_awarded=point_value if is_correct else 0.0,
                feedback_state="correct" if is_correct else "incorrect",
                correct_answer_display=display,
            )

        # Single-blank: any matching accepted answer is correct.
        normalised_accepted = [a.strip() if trim_whitespace else a for a in accepted]

        if case_sensitive:
            is_correct = text in normalised_accepted
        else:
            is_correct = text.lower() in [a.lower() for a in normalised_accepted]

        return GradeResult(
            is_correct=is_correct,
            score_awarded=point_value if is_correct else 0.0,
            feedback_state="correct" if is_correct else "incorrect",
            correct_answer_display=display,
        )


class SAEvaluator:
    """Evaluator for Short Answer questions.

    Identical grading logic to ``BlankEvaluator``; separate class for
    clarity and future extension (e.g. fuzzy matching, regex).
    """

    @staticmethod
    def grade(
        accepted: list[str],
        case_sensitive: bool,
        trim_whitespace: bool,
        payload: dict,
        point_value: float,
    ) -> GradeResult:
        return BlankEvaluator.grade(
            accepted, case_sensitive, trim_whitespace, payload, point_value
        )


# ---------------------------------------------------------------------------
# Dispatch engine
# ---------------------------------------------------------------------------

class GradingEngine:
    """Dispatches grading to the appropriate evaluator by question type.

    All public methods are static so the engine can be used without
    instantiation.
    """

    @staticmethod
    def grade_from_dict(qq_dict: dict, payload: dict) -> GradeResult:
        """Grade using a snapshot dict (no ORM object required).

        This is the canonical grading entry-point for the quiz runner and
        all code that works with in-memory snapshots.

        Parameters
        ----------
        qq_dict:
            Snapshot dict produced by ``QuestionSelector.build_snapshots()``.
            Must contain: ``type``, ``point_value``, ``options`` (MC/MA),
            ``accepted_answers`` (BLANK/SA), ``case_sensitive``,
            ``trim_whitespace``.
        payload:
            Answer payload from the runner.  Empty dict ``{}`` means skipped.
        """
        qtype = qq_dict.get("type", "")
        point = qq_dict.get("point_value", 1.0)

        if qtype == "MC":
            return MCEvaluator.grade(qq_dict.get("options", []), payload, point)

        if qtype == "MA":
            return MAEvaluator.grade(qq_dict.get("options", []), payload, point)

        if qtype in ("BLANK", "SA"):
            acc = qq_dict.get("accepted_answers", [])
            cs = qq_dict.get("case_sensitive", False)
            tw = qq_dict.get("trim_whitespace", True)
            if qtype == "BLANK":
                blank_count = count_blank_placeholders(qq_dict.get("content", ""))
                return BlankEvaluator.grade(
                    accepted=acc,
                    case_sensitive=cs,
                    trim_whitespace=tw,
                    payload=payload,
                    point_value=point,
                    blank_count=blank_count,
                )
            return SAEvaluator.grade(
                accepted=acc,
                case_sensitive=cs,
                trim_whitespace=tw,
                payload=payload,
                point_value=point,
            )

        # Unknown / unsupported type → treat as skipped
        return GradeResult(None, 0.0, "skipped", "\u2014")


# ---------------------------------------------------------------------------
# Private display helpers
# ---------------------------------------------------------------------------

def _mc_correct_display(options: list[dict]) -> str:
    for o in options:
        if o.get("is_correct"):
            return f"{o['key']}. {o.get('text', '')}"
    return "\u2014"


def _ma_correct_display(options: list[dict]) -> str:
    texts = [
        f"{o['key']}. {o.get('text', '')}"
        for o in options
        if o.get("is_correct")
    ]
    return "; ".join(texts) or "\u2014"
