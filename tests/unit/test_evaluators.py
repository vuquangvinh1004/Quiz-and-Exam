"""Unit tests for modules/grading/evaluators.py (Phase 5).

Test matrix covering:
  - MCEvaluator  : correct, incorrect, empty payload, invalid key, empty
  - MAEvaluator  : exact match, partial, extra selection, empty, order-independent
  - BlankEvaluator : case-insensitive, case-sensitive, trim, no text, empty accepted
  - SAEvaluator  : delegates to BlankEvaluator (smoke tests)
  - GradingEngine : dispatch to each evaluator + unknown type
"""
from __future__ import annotations

import pytest

from modules.grading.evaluators import (
    BlankEvaluator,
    GradeResult,
    GradingEngine,
    MAEvaluator,
    MCEvaluator,
    SAEvaluator,
)

# ---------------------------------------------------------------------------
# Shared fixtures / helpers
# ---------------------------------------------------------------------------

_MC_OPTIONS = [
    {"key": "A", "text": "Paris", "is_correct": True},
    {"key": "B", "text": "London", "is_correct": False},
    {"key": "C", "text": "Berlin", "is_correct": False},
]

_MA_OPTIONS = [
    {"key": "A", "text": "Alice", "is_correct": True},
    {"key": "B", "text": "Bob",   "is_correct": True},
    {"key": "C", "text": "Carol", "is_correct": False},
]

_BLANK_ACCEPTED = ["Paris", "paris"]
_BLANK_ACCEPTED_SINGLE = ["Mercury"]


# ---------------------------------------------------------------------------
# MCEvaluator
# ---------------------------------------------------------------------------

class TestMCEvaluator:

    def test_correct_selection(self):
        r = MCEvaluator.grade(_MC_OPTIONS, {"selected": "A"}, 1.0)
        assert r.is_correct is True
        assert r.score_awarded == pytest.approx(1.0)
        assert r.feedback_state == "correct"

    def test_incorrect_selection(self):
        r = MCEvaluator.grade(_MC_OPTIONS, {"selected": "B"}, 1.0)
        assert r.is_correct is False
        assert r.score_awarded == pytest.approx(0.0)
        assert r.feedback_state == "incorrect"

    def test_empty_payload_skipped(self):
        r = MCEvaluator.grade(_MC_OPTIONS, {}, 1.0)
        assert r.is_correct is None
        assert r.score_awarded == pytest.approx(0.0)
        assert r.feedback_state == "skipped"

    def test_invalid_key_incorrect(self):
        r = MCEvaluator.grade(_MC_OPTIONS, {"selected": "Z"}, 1.0)
        assert r.is_correct is False
        assert r.score_awarded == pytest.approx(0.0)

    def test_empty_string_selected_incorrect(self):
        r = MCEvaluator.grade(_MC_OPTIONS, {"selected": ""}, 1.0)
        assert r.is_correct is False

    def test_custom_point_value(self):
        r = MCEvaluator.grade(_MC_OPTIONS, {"selected": "A"}, 2.5)
        assert r.score_awarded == pytest.approx(2.5)

    def test_correct_answer_display_populated(self):
        r = MCEvaluator.grade(_MC_OPTIONS, {"selected": "B"}, 1.0)
        assert "A" in r.correct_answer_display
        assert "Paris" in r.correct_answer_display

    def test_no_correct_option_display_fallback(self):
        options = [{"key": "A", "text": "x", "is_correct": False}]
        r = MCEvaluator.grade(options, {"selected": "A"}, 1.0)
        assert r.correct_answer_display == "—"


# ---------------------------------------------------------------------------
# MAEvaluator
# ---------------------------------------------------------------------------

class TestMAEvaluator:

    def test_exact_match_correct(self):
        r = MAEvaluator.grade(_MA_OPTIONS, {"selected": ["A", "B"]}, 2.0)
        assert r.is_correct is True
        assert r.score_awarded == pytest.approx(2.0)
        assert r.feedback_state == "correct"

    def test_order_independent_correct(self):
        r = MAEvaluator.grade(_MA_OPTIONS, {"selected": ["B", "A"]}, 2.0)
        assert r.is_correct is True

    def test_partial_selection_incorrect(self):
        r = MAEvaluator.grade(_MA_OPTIONS, {"selected": ["A"]}, 2.0)
        assert r.is_correct is False
        assert r.score_awarded == pytest.approx(0.0)

    def test_extra_selection_incorrect(self):
        r = MAEvaluator.grade(_MA_OPTIONS, {"selected": ["A", "B", "C"]}, 2.0)
        assert r.is_correct is False
        assert r.score_awarded == pytest.approx(0.0)

    def test_empty_payload_skipped(self):
        r = MAEvaluator.grade(_MA_OPTIONS, {}, 2.0)
        assert r.is_correct is None
        assert r.score_awarded == pytest.approx(0.0)
        assert r.feedback_state == "skipped"

    def test_empty_list_selected_incorrect(self):
        r = MAEvaluator.grade(_MA_OPTIONS, {"selected": []}, 2.0)
        assert r.is_correct is False

    def test_wrong_keys_incorrect(self):
        r = MAEvaluator.grade(_MA_OPTIONS, {"selected": ["C"]}, 2.0)
        assert r.is_correct is False

    def test_correct_answer_display_contains_correct_keys(self):
        r = MAEvaluator.grade(_MA_OPTIONS, {"selected": []}, 2.0)
        assert "A" in r.correct_answer_display
        assert "B" in r.correct_answer_display


# ---------------------------------------------------------------------------
# BlankEvaluator
# ---------------------------------------------------------------------------

class TestBlankEvaluator:

    def test_case_insensitive_correct(self):
        r = BlankEvaluator.grade(_BLANK_ACCEPTED, False, True, {"text": "PARIS"}, 1.0)
        assert r.is_correct is True

    def test_case_insensitive_wrong_word(self):
        r = BlankEvaluator.grade(_BLANK_ACCEPTED, False, True, {"text": "London"}, 1.0)
        assert r.is_correct is False
        assert r.score_awarded == pytest.approx(0.0)

    def test_case_sensitive_exact_match(self):
        r = BlankEvaluator.grade(_BLANK_ACCEPTED, True, True, {"text": "Paris"}, 1.0)
        assert r.is_correct is True
        assert r.score_awarded == pytest.approx(1.0)

    def test_case_sensitive_wrong_case(self):
        r = BlankEvaluator.grade(_BLANK_ACCEPTED, True, True, {"text": "PARIS"}, 1.0)
        assert r.is_correct is False

    def test_trim_whitespace_correct(self):
        r = BlankEvaluator.grade(_BLANK_ACCEPTED, False, True, {"text": "  paris  "}, 1.0)
        assert r.is_correct is True

    def test_no_trim_whitespace_fails_padded(self):
        r = BlankEvaluator.grade(_BLANK_ACCEPTED, False, False, {"text": "  paris  "}, 1.0)
        assert r.is_correct is False

    def test_empty_text_skipped(self):
        r = BlankEvaluator.grade(_BLANK_ACCEPTED, False, True, {"text": ""}, 1.0)
        assert r.is_correct is None
        assert r.feedback_state == "skipped"

    def test_missing_text_key_skipped(self):
        r = BlankEvaluator.grade(_BLANK_ACCEPTED, False, True, {"other": "x"}, 1.0)
        assert r.is_correct is None
        assert r.score_awarded == pytest.approx(0.0)

    def test_empty_payload_skipped(self):
        r = BlankEvaluator.grade(_BLANK_ACCEPTED, False, True, {}, 1.0)
        assert r.is_correct is None
        assert r.feedback_state == "skipped"

    def test_empty_accepted_answers_incorrect(self):
        r = BlankEvaluator.grade([], False, True, {"text": "Paris"}, 1.0)
        assert r.is_correct is False

    def test_correct_answer_display_populated(self):
        r = BlankEvaluator.grade(_BLANK_ACCEPTED, False, True, {"text": "wrong"}, 1.0)
        assert r.correct_answer_display != ""

    def test_empty_accepted_display_fallback(self):
        r = BlankEvaluator.grade([], False, True, {}, 1.0)
        assert r.correct_answer_display == "—"

    def test_custom_point_value(self):
        r = BlankEvaluator.grade(_BLANK_ACCEPTED, False, True, {"text": "paris"}, 3.0)
        assert r.score_awarded == pytest.approx(3.0)

    # Multi-blank (blank_count > 1)

    def test_multi_blank_correct(self):
        r = BlankEvaluator.grade(
            ["tổng thể", "N"], False, True, {"text": "tổng thể||N"}, 1.5,
            blank_count=2,
        )
        assert r.is_correct is True
        assert r.score_awarded == pytest.approx(1.5)

    def test_multi_blank_case_insensitive(self):
        r = BlankEvaluator.grade(
            ["tổng thể", "N"], False, True, {"text": "TỔNG THỂ||n"}, 1.0,
            blank_count=2,
        )
        assert r.is_correct is True

    def test_multi_blank_wrong_part(self):
        r = BlankEvaluator.grade(
            ["tổng thể", "N"], False, True, {"text": "mẫu||N"}, 1.0,
            blank_count=2,
        )
        assert r.is_correct is False
        assert r.score_awarded == pytest.approx(0.0)

    def test_multi_blank_wrong_count_not_enough_parts(self):
        r = BlankEvaluator.grade(
            ["tổng thể", "N"], False, True, {"text": "tổng thể"}, 1.0,
            blank_count=2,
        )
        assert r.is_correct is False

    def test_multi_blank_wrong_count_too_many_parts(self):
        r = BlankEvaluator.grade(
            ["tổng thể", "N"], False, True, {"text": "tổng thể||N||extra"}, 1.0,
            blank_count=2,
        )
        assert r.is_correct is False

    def test_multi_blank_trim_whitespace(self):
        r = BlankEvaluator.grade(
            ["tổng thể", "N"], False, True, {"text": "  tổng thể  ||  N  "}, 1.0,
            blank_count=2,
        )
        assert r.is_correct is True


# ---------------------------------------------------------------------------
# SAEvaluator (delegates to BlankEvaluator)
# ---------------------------------------------------------------------------

class TestSAEvaluator:

    def test_correct_case_insensitive(self):
        r = SAEvaluator.grade(["Mercury"], False, True, {"text": "mercury"}, 1.0)
        assert r.is_correct is True
        assert r.score_awarded == pytest.approx(1.0)

    def test_incorrect_wrong_answer(self):
        r = SAEvaluator.grade(["Mercury"], False, True, {"text": "Venus"}, 1.0)
        assert r.is_correct is False
        assert r.score_awarded == pytest.approx(0.0)

    def test_empty_payload_skipped(self):
        r = SAEvaluator.grade(["Mercury"], False, True, {}, 1.0)
        assert r.is_correct is None
        assert r.feedback_state == "skipped"

    def test_returns_grade_result_instance(self):
        r = SAEvaluator.grade(["Mercury"], False, True, {"text": "mercury"}, 1.0)
        assert isinstance(r, GradeResult)


# ---------------------------------------------------------------------------
# GradingEngine
# ---------------------------------------------------------------------------

class TestGradingEngine:

    def _mc_qq(self):
        return {
            "type": "MC",
            "point_value": 1.0,
            "options": _MC_OPTIONS,
            "accepted_answers": [],
            "case_sensitive": False,
            "trim_whitespace": True,
        }

    def _ma_qq(self):
        return {
            "type": "MA",
            "point_value": 2.0,
            "options": _MA_OPTIONS,
            "accepted_answers": [],
            "case_sensitive": False,
            "trim_whitespace": True,
        }

    def _blank_qq(self, case_sensitive=False):
        return {
            "type": "BLANK",
            "point_value": 1.0,
            "options": [],
            "accepted_answers": ["Paris", "paris"],
            "case_sensitive": case_sensitive,
            "trim_whitespace": True,
        }

    def _sa_qq(self):
        return {
            "type": "SA",
            "point_value": 1.0,
            "options": [],
            "accepted_answers": ["Mercury"],
            "case_sensitive": False,
            "trim_whitespace": True,
        }

    def test_dispatches_mc_correct(self):
        r = GradingEngine.grade_from_dict(self._mc_qq(), {"selected": "A"})
        assert r.is_correct is True

    def test_dispatches_mc_skipped(self):
        r = GradingEngine.grade_from_dict(self._mc_qq(), {})
        assert r.is_correct is None

    def test_dispatches_ma_correct(self):
        r = GradingEngine.grade_from_dict(self._ma_qq(), {"selected": ["A", "B"]})
        assert r.is_correct is True

    def test_dispatches_ma_partial(self):
        r = GradingEngine.grade_from_dict(self._ma_qq(), {"selected": ["A"]})
        assert r.is_correct is False

    def test_dispatches_blank_correct(self):
        r = GradingEngine.grade_from_dict(self._blank_qq(), {"text": "PARIS"})
        assert r.is_correct is True

    def test_dispatches_blank_wrong(self):
        r = GradingEngine.grade_from_dict(self._blank_qq(), {"text": "London"})
        assert r.is_correct is False

    def test_dispatches_sa_correct(self):
        r = GradingEngine.grade_from_dict(self._sa_qq(), {"text": "mercury"})
        assert r.is_correct is True

    def test_dispatches_sa_wrong(self):
        r = GradingEngine.grade_from_dict(self._sa_qq(), {"text": "Venus"})
        assert r.is_correct is False

    def test_unknown_type_skipped(self):
        qq = {"type": "UNKNOWN", "point_value": 1.0}
        r = GradingEngine.grade_from_dict(qq, {"text": "anything"})
        assert r.is_correct is None
        assert r.score_awarded == pytest.approx(0.0)
        assert r.feedback_state == "skipped"

    def test_returns_grade_result_instance(self):
        r = GradingEngine.grade_from_dict(self._mc_qq(), {"selected": "A"})
        assert isinstance(r, GradeResult)
