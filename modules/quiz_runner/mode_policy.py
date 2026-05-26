"""Mode policy helpers for quiz runner.

Single source of truth for the behavioural rules of each quiz mode.
All consumers (runner view, grading, result display) should call these
helpers rather than using inline comparisons against mode strings.

Rules source: ARCHITECTURE §7.
"""
from __future__ import annotations

from core.utils.constants import QuizMode


class ModePolicy:
    """Stateless policy helpers; all methods are static.

    Usage example::

        if ModePolicy.requires_timer(self._mode):
            self._countdown_timer.start()
    """

    # ------------------------------------------------------------------
    # Timer
    # ------------------------------------------------------------------

    @staticmethod
    def requires_timer(mode: str) -> bool:
        """EXAM and PRACTICE require a countdown timer.

        STUDY must NOT have a timer (ARCHITECTURE §7.4 rule 1).
        """
        return mode in (QuizMode.EXAM.value, QuizMode.PRACTICE.value)

    # ------------------------------------------------------------------
    # Hint
    # ------------------------------------------------------------------

    @staticmethod
    def show_hint(mode: str) -> bool:
        """Hints are visible in PRACTICE and STUDY; hidden in EXAM.

        ARCHITECTURE §7.2 rule 2 and §7.3 rule 2.
        """
        return mode in (QuizMode.PRACTICE.value, QuizMode.STUDY.value)

    # ------------------------------------------------------------------
    # Per-question feedback
    # ------------------------------------------------------------------

    @staticmethod
    def show_per_question_feedback(mode: str) -> bool:
        """Immediate per-question feedback is shown only in STUDY mode.

        EXAM and PRACTICE do not reveal correct/incorrect until the
        attempt ends (or not at all for EXAM).
        ARCHITECTURE §7.4 rule 2.
        """
        return mode == QuizMode.STUDY.value

    @staticmethod
    def show_correct_answer_in_feedback(mode: str) -> bool:
        """The correct answer is revealed in STUDY feedback.

        Not shown in EXAM or PRACTICE during the attempt.
        ARCHITECTURE §7.4 rule 2, §7.2 rule 3.
        """
        return mode == QuizMode.STUDY.value

    @staticmethod
    def show_explanation_in_feedback(mode: str) -> bool:
        """Explanation text is shown after confirming a STUDY answer.

        ARCHITECTURE §7.4 rule 3.
        """
        return mode == QuizMode.STUDY.value

    # ------------------------------------------------------------------
    # Answer locking
    # ------------------------------------------------------------------

    @staticmethod
    def allow_answer_change(mode: str, is_confirmed: bool) -> bool:
        """Whether the user can still modify their answer.

        In STUDY mode, once the "Confirm" button is pressed the answer
        widget is locked.  In EXAM and PRACTICE, answers can be changed
        any time before final submission.
        """
        if mode == QuizMode.STUDY.value:
            return not is_confirmed
        return True

    # ------------------------------------------------------------------
    # End-of-quiz result display
    # ------------------------------------------------------------------

    @staticmethod
    def end_result_type(mode: str) -> str:
        """Return the expected end-of-quiz result display strategy.

        Returns
        -------
        ``"minimal"``
            EXAM: a completion notice; no per-question
            correct/incorrect breakdown by default.
        ``"summary"``
            PRACTICE: totals (correct / wrong / skipped / score).
        ``"per_question"``
            STUDY: per-question detail was already shown inline.
        """
        if mode == QuizMode.EXAM.value:
            return "minimal"
        if mode == QuizMode.PRACTICE.value:
            return "summary"
        return "per_question"  # STUDY

    # ------------------------------------------------------------------
    # Submission dialog
    # ------------------------------------------------------------------

    @staticmethod
    def show_submission_dialog(mode: str) -> bool:
        """Whether to show the full SubmitDialog (email/folder) after the attempt.

        Only EXAM mode triggers the submission workflow.
        ARCHITECTURE §6.4, §7.2 rule 6.
        """
        return mode == QuizMode.EXAM.value
