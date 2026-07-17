"""Unit tests for core/utils/constants.py"""
from __future__ import annotations

from core.utils.constants import (
    BLANK_PLACEHOLDER,
    DEFAULT_DIFFICULTY,
    DEFAULT_SCORE,
    DEFAULT_STATUS,
    LEGACY_BLANK_PLACEHOLDER,
    MULTI_VALUE_DELIMITER,
    QUESTION_TYPE_IMPORT_MAP,
    VALID_OPTION_LABELS,
    AttemptStatus,
    Difficulty,
    QuestionStatus,
    QuestionType,
    QuizMode,
)


class TestQuestionType:
    def test_all_types_present(self):
        values = {qt.value for qt in QuestionType}
        assert values == {"MC", "MA", "BLANK", "TF", "SA", "ES", "PR"}

    def test_import_map_covers_all_types(self):
        assert set(QUESTION_TYPE_IMPORT_MAP.values()) == set(QuestionType)

    def test_import_map_keys_are_long_form(self):
        expected_keys = {
            "multiple_choice",
            "multiple_answer",
            "blank",
            "true_false",
            "short_answer",
            "essay",
            "problem",
        }
        assert set(QUESTION_TYPE_IMPORT_MAP.keys()) == expected_keys

    def test_is_str_enum(self):
        # QuestionType must be usable as plain strings (for DB CHECK constraints)
        assert QuestionType.MULTIPLE_CHOICE == "MC"
        assert QuestionType.BLANK == "BLANK"


class TestQuizMode:
    def test_three_modes_present(self):
        values = {m.value for m in QuizMode}
        assert values == {"EXAM", "PRACTICE", "STUDY"}

    def test_is_str_enum(self):
        assert QuizMode.EXAM == "EXAM"
        assert QuizMode.STUDY == "STUDY"


class TestAttemptStatus:
    def test_four_statuses_present(self):
        values = {s.value for s in AttemptStatus}
        assert values == {"IN_PROGRESS", "SUBMITTED", "TIME_UP", "COMPLETED"}


class TestDifficulty:
    def test_values(self):
        assert set(Difficulty) == {Difficulty.EASY, Difficulty.MEDIUM, Difficulty.HARD}


class TestDefaults:
    def test_default_score(self):
        assert DEFAULT_SCORE == 1.0

    def test_default_difficulty(self):
        assert DEFAULT_DIFFICULTY == Difficulty.MEDIUM

    def test_default_status(self):
        assert DEFAULT_STATUS == QuestionStatus.ACTIVE


class TestConstants:
    def test_blank_placeholder(self):
        assert BLANK_PLACEHOLDER == "[[blank]]"

    def test_legacy_blank_placeholder(self):
        assert LEGACY_BLANK_PLACEHOLDER == "________"

    def test_multi_value_delimiter(self):
        assert MULTI_VALUE_DELIMITER == "||"

    def test_valid_option_labels_length(self):
        assert len(VALID_OPTION_LABELS) == 6

    def test_valid_option_labels_values(self):
        assert set(VALID_OPTION_LABELS) == {"A", "B", "C", "D", "E", "F"}
