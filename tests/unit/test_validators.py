"""Unit tests for core/utils/validators.py"""
from __future__ import annotations

import pytest

from core.utils.constants import QuestionType
from core.utils.validators import (
    count_blank_placeholders,
    is_valid_option_label,
    validate_correct_answers_for_type,
)


class TestIsValidOptionLabel:
    @pytest.mark.parametrize("label", ["A", "B", "C", "D", "E", "F"])
    def test_valid_labels(self, label):
        assert is_valid_option_label(label) is True

    @pytest.mark.parametrize("label", ["G", "H", "Z", "1", ""])
    def test_invalid_labels(self, label):
        assert is_valid_option_label(label) is False

    def test_case_insensitive(self):
        assert is_valid_option_label("a") is True
        assert is_valid_option_label("f") is True


class TestCountBlankPlaceholders:
    def test_one_legacy_placeholder(self):
        assert count_blank_placeholders("Thủ đô là ________.") == 1

    def test_one_canonical_placeholder(self):
        assert count_blank_placeholders("Thủ đô là [[blank]].") == 1

    def test_zero_placeholders(self):
        assert count_blank_placeholders("No placeholder here.") == 0

    def test_two_placeholders(self):
        assert count_blank_placeholders("________ and [[blank]]") == 2

    def test_case_insensitive(self):
        assert count_blank_placeholders("Test [[BLANK]] here") == 1


class TestValidateCorrectAnswersForType:
    def test_mc_valid(self):
        errors = validate_correct_answers_for_type(
            QuestionType.MULTIPLE_CHOICE, "A", ["A", "B", "C"]
        )
        assert errors == []

    def test_mc_multiple_answers_is_error(self):
        errors = validate_correct_answers_for_type(
            QuestionType.MULTIPLE_CHOICE, "A||B", ["A", "B", "C"]
        )
        assert any("exactly 1" in e for e in errors)

    def test_mc_nonexistent_option_is_error(self):
        errors = validate_correct_answers_for_type(
            QuestionType.MULTIPLE_CHOICE, "G", ["A", "B", "C"]
        )
        assert any("non-existent" in e for e in errors)

    def test_ma_valid(self):
        errors = validate_correct_answers_for_type(
            QuestionType.MULTIPLE_ANSWER, "A||C", ["A", "B", "C", "D"]
        )
        assert errors == []

    def test_ma_single_answer_is_error(self):
        errors = validate_correct_answers_for_type(
            QuestionType.MULTIPLE_ANSWER, "A", ["A", "B"]
        )
        assert any("at least 2" in e for e in errors)

    def test_ma_duplicate_answer_is_error(self):
        errors = validate_correct_answers_for_type(
            QuestionType.MULTIPLE_ANSWER, "A||A||C", ["A", "B", "C"]
        )
        assert any("Duplicate" in e for e in errors)

    def test_blank_valid(self):
        errors = validate_correct_answers_for_type(
            QuestionType.BLANK, "Hà Nội||Ha Noi", []
        )
        assert errors == []

    def test_sa_valid(self):
        errors = validate_correct_answers_for_type(
            QuestionType.SHORT_ANSWER, "EOQ||Economic Order Quantity", []
        )
        assert errors == []

    def test_empty_correct_answers_returns_error(self):
        errors = validate_correct_answers_for_type(
            QuestionType.MULTIPLE_CHOICE, "", ["A", "B"]
        )
        assert any("must not be empty" in e for e in errors)
