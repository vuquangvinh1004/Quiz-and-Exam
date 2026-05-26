"""Unit tests for core/utils/exceptions.py"""
from __future__ import annotations

import pytest

from core.utils.exceptions import (
    AttemptNotFoundError,
    DatabaseError,
    GradingError,
    ImportError,
    ImportFileError,
    ImportValidationError,
    MigrationError,
    QuizAppError,
    QuizRuntimeError,
    SettingsError,
    ValidationError,
)


class TestExceptionHierarchy:
    def test_all_exceptions_inherit_from_quiz_app_error(self):
        assert issubclass(ImportError, QuizAppError)
        assert issubclass(ImportValidationError, ImportError)
        assert issubclass(ImportFileError, ImportError)
        assert issubclass(ValidationError, QuizAppError)
        assert issubclass(GradingError, QuizAppError)
        assert issubclass(DatabaseError, QuizAppError)
        assert issubclass(MigrationError, DatabaseError)
        assert issubclass(QuizRuntimeError, QuizAppError)
        assert issubclass(AttemptNotFoundError, QuizRuntimeError)
        assert issubclass(SettingsError, QuizAppError)

    def test_raise_and_catch_import_validation_error(self):
        errors = [{"row": 2, "severity": "ERROR", "message": "Missing question_text"}]
        with pytest.raises(ImportValidationError) as exc_info:
            raise ImportValidationError(errors)
        assert exc_info.value.errors == errors
        assert "1 validation error" in str(exc_info.value)

    def test_raise_and_catch_grading_error(self):
        with pytest.raises(GradingError):
            raise GradingError("Cannot grade empty answer")

    def test_base_exception_catchable_as_quiz_app_error(self):
        with pytest.raises(QuizAppError):
            raise ValidationError("bad input")
