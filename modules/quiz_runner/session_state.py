"""Session state container for quiz runner UI.

Keeps mutable runtime state outside the view class so UI code focuses on
rendering and interaction wiring.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from core.domain.services.quiz_service import QuizInfoDTO, QuizQuestionSnapshot


@dataclass
class QuizRunnerState:
    """Mutable state for one quiz runner lifecycle."""

    pending_quiz_id: int | None = None
    quiz_info: QuizInfoDTO | None = None

    quiz_title: str = ""
    mode: str = ""
    attempt_id: int | None = None
    quiz_questions: list[QuizQuestionSnapshot] = field(default_factory=list)
    current_index: int = 0
    answers: dict[int, dict] = field(default_factory=dict)
    confirmed: set[int] = field(default_factory=set)
    submitter_name: str = ""
    submitter_id: str = ""
    started_at: datetime | None = None
    remaining_seconds: int | None = None
    resumed_from_autosave: bool = False
    finalizing: bool = False
    retry_submit_only: bool = False

    def reset_runtime(self) -> None:
        """Reset in-progress attempt data while keeping pending quiz info."""
        self.quiz_title = ""
        self.mode = ""
        self.attempt_id = None
        self.quiz_questions = []
        self.current_index = 0
        self.answers = {}
        self.confirmed = set()
        self.submitter_name = ""
        self.submitter_id = ""
        self.started_at = None
        self.remaining_seconds = None
        self.resumed_from_autosave = False
        self.finalizing = False
        self.retry_submit_only = False

    def reset_all(self) -> None:
        """Reset both pending setup and runtime state."""
        self.pending_quiz_id = None
        self.quiz_info = None
        self.reset_runtime()
