"""Runtime controller for quiz runner data/session operations.

Encapsulates persistence-related operations so the view layer does not
manipulate DB session/query details directly.
"""
from __future__ import annotations

from core.database.session import get_session
from core.domain.services.quiz_service import GradedRow, QuizInfoDTO
from core.domain.services.submission_service import SubmissionService, SubmissionSettings
from modules.quiz_runner.session_controller_impl import QuizRunnerSessionControllerService
from modules.quiz_runner.session_controller_types import PreparedAttemptSession


class QuizRunnerSessionController(QuizRunnerSessionControllerService):
    """Compatibility facade for quiz runner persistence orchestration."""


__all__ = [
    "PreparedAttemptSession",
    "QuizRunnerSessionController",
]
