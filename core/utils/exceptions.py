"""Application exception hierarchy.

All custom exceptions originate from QuizAppError.
Raise specific subclasses; never raise the base class directly.
"""
from __future__ import annotations


class QuizAppError(Exception):
    """Base exception for all Quiz Desktop App errors."""


# ---------------------------------------------------------------------------
# Import subsystem
# ---------------------------------------------------------------------------

class ImportError(QuizAppError):
    """Raised when a file import operation fails."""


class ImportValidationError(ImportError):
    """Raised when one or more rows in an import file fail validation."""

    def __init__(self, errors: list[dict]) -> None:
        """
        Args:
            errors: list of dicts with keys 'row', 'severity', 'message'.
        """
        self.errors = errors
        summary = f"{len(errors)} validation error(s) during import"
        super().__init__(summary)


class ImportFileError(ImportError):
    """Raised when the import file cannot be read (missing, corrupt, wrong format)."""


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class ValidationError(QuizAppError):
    """Raised when domain-level validation fails (not import-specific)."""


# ---------------------------------------------------------------------------
# Grading
# ---------------------------------------------------------------------------

class GradingError(QuizAppError):
    """Raised when grading logic encounters an unrecoverable state."""


# ---------------------------------------------------------------------------
# Database / persistence
# ---------------------------------------------------------------------------

class DatabaseError(QuizAppError):
    """Raised when a database operation fails unexpectedly."""


class MigrationError(DatabaseError):
    """Raised when a schema migration fails."""


# ---------------------------------------------------------------------------
# Quiz runtime
# ---------------------------------------------------------------------------

class QuizRuntimeError(QuizAppError):
    """Raised when the quiz runner encounters an illegal state."""


class AttemptNotFoundError(QuizRuntimeError):
    """Raised when an attempt record cannot be found."""


# ---------------------------------------------------------------------------
# Settings / configuration
# ---------------------------------------------------------------------------

class SettingsError(QuizAppError):
    """Raised when settings cannot be loaded or saved."""


# ---------------------------------------------------------------------------
# Submission
# ---------------------------------------------------------------------------

class SubmissionError(QuizAppError):
    """Base error for submission workflows (email/folder)."""


class SubmissionConfigError(SubmissionError):
    """Raised when submission configuration/inputs are invalid."""


class SubmissionDeliveryError(SubmissionError):
    """Raised when delivery channel fails (SMTP/folder I/O)."""
