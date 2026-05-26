"""Unit tests for modules/quiz_runner/mode_policy.py (Phase 5).

Tests all 8 ModePolicy static methods for each of the three quiz modes:
  EXAM, PRACTICE, STUDY.
"""
from __future__ import annotations

import pytest

from core.utils.constants import QuizMode
from modules.quiz_runner.mode_policy import ModePolicy

EXAM     = QuizMode.EXAM.value       # "EXAM"
PRACTICE = QuizMode.PRACTICE.value   # "PRACTICE"
STUDY    = QuizMode.STUDY.value      # "STUDY"


# ---------------------------------------------------------------------------
# requires_timer
# ---------------------------------------------------------------------------

class TestRequiresTimer:

    def test_exam_requires_timer(self):
        assert ModePolicy.requires_timer(EXAM) is True

    def test_practice_requires_timer(self):
        assert ModePolicy.requires_timer(PRACTICE) is True

    def test_study_no_timer(self):
        assert ModePolicy.requires_timer(STUDY) is False


# ---------------------------------------------------------------------------
# show_hint
# ---------------------------------------------------------------------------

class TestShowHint:

    def test_exam_no_hint(self):
        assert ModePolicy.show_hint(EXAM) is False

    def test_practice_shows_hint(self):
        assert ModePolicy.show_hint(PRACTICE) is True

    def test_study_shows_hint(self):
        assert ModePolicy.show_hint(STUDY) is True


# ---------------------------------------------------------------------------
# show_per_question_feedback
# ---------------------------------------------------------------------------

class TestShowPerQuestionFeedback:

    def test_exam_no_per_question_feedback(self):
        assert ModePolicy.show_per_question_feedback(EXAM) is False

    def test_practice_no_per_question_feedback(self):
        assert ModePolicy.show_per_question_feedback(PRACTICE) is False

    def test_study_shows_per_question_feedback(self):
        assert ModePolicy.show_per_question_feedback(STUDY) is True


# ---------------------------------------------------------------------------
# show_correct_answer_in_feedback
# ---------------------------------------------------------------------------

class TestShowCorrectAnswerInFeedback:

    def test_exam_hides_correct_answer(self):
        assert ModePolicy.show_correct_answer_in_feedback(EXAM) is False

    def test_practice_hides_correct_answer(self):
        assert ModePolicy.show_correct_answer_in_feedback(PRACTICE) is False

    def test_study_shows_correct_answer(self):
        assert ModePolicy.show_correct_answer_in_feedback(STUDY) is True


# ---------------------------------------------------------------------------
# show_explanation_in_feedback
# ---------------------------------------------------------------------------

class TestShowExplanationInFeedback:

    def test_exam_hides_explanation(self):
        assert ModePolicy.show_explanation_in_feedback(EXAM) is False

    def test_practice_hides_explanation(self):
        assert ModePolicy.show_explanation_in_feedback(PRACTICE) is False

    def test_study_shows_explanation(self):
        assert ModePolicy.show_explanation_in_feedback(STUDY) is True


# ---------------------------------------------------------------------------
# allow_answer_change
# ---------------------------------------------------------------------------

class TestAllowAnswerChange:

    def test_exam_can_always_change_before_confirm(self):
        assert ModePolicy.allow_answer_change(EXAM, is_confirmed=False) is True

    def test_exam_can_still_change_after_confirm(self):
        # EXAM has no per-question confirm; confirmed flag has no effect
        assert ModePolicy.allow_answer_change(EXAM, is_confirmed=True) is True

    def test_practice_can_always_change_before_confirm(self):
        assert ModePolicy.allow_answer_change(PRACTICE, is_confirmed=False) is True

    def test_practice_can_still_change_after_confirm(self):
        assert ModePolicy.allow_answer_change(PRACTICE, is_confirmed=True) is True

    def test_study_can_change_before_confirmation(self):
        assert ModePolicy.allow_answer_change(STUDY, is_confirmed=False) is True

    def test_study_locked_after_confirmation(self):
        assert ModePolicy.allow_answer_change(STUDY, is_confirmed=True) is False


# ---------------------------------------------------------------------------
# end_result_type
# ---------------------------------------------------------------------------

class TestEndResultType:

    def test_exam_minimal(self):
        assert ModePolicy.end_result_type(EXAM) == "minimal"

    def test_practice_summary(self):
        assert ModePolicy.end_result_type(PRACTICE) == "summary"

    def test_study_per_question(self):
        assert ModePolicy.end_result_type(STUDY) == "per_question"


# ---------------------------------------------------------------------------
# show_submission_dialog
# ---------------------------------------------------------------------------

class TestShowSubmissionDialog:

    def test_exam_shows_dialog(self):
        assert ModePolicy.show_submission_dialog(EXAM) is True

    def test_practice_no_dialog(self):
        assert ModePolicy.show_submission_dialog(PRACTICE) is False

    def test_study_no_dialog(self):
        assert ModePolicy.show_submission_dialog(STUDY) is False


# ---------------------------------------------------------------------------
# Unknown/invalid mode safety
# ---------------------------------------------------------------------------

class TestUnknownModeSafety:

    def test_unknown_mode_does_not_require_timer(self):
        assert ModePolicy.requires_timer("UNKNOWN") is False

    def test_unknown_mode_hides_hint(self):
        assert ModePolicy.show_hint("UNKNOWN") is False

    def test_unknown_mode_has_no_per_question_feedback(self):
        assert ModePolicy.show_per_question_feedback("UNKNOWN") is False

    def test_unknown_mode_allows_answer_change(self):
        assert ModePolicy.allow_answer_change("UNKNOWN", is_confirmed=True) is True

    def test_unknown_mode_has_no_submission_dialog(self):
        assert ModePolicy.show_submission_dialog("UNKNOWN") is False

    def test_unknown_mode_falls_back_to_per_question_end_result(self):
        assert ModePolicy.end_result_type("UNKNOWN") == "per_question"
