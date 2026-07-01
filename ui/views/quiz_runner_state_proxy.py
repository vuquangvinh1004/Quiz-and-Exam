from __future__ import annotations

from datetime import datetime

from core.domain.services.quiz_service import QuizInfoDTO, QuizQuestionSnapshot


class QuizRunnerStateProxyMixin:
    """Property proxy layer preserving old attribute names on top of _state."""

    @property
    def _pending_quiz_id(self) -> int | None:
        return self._state.pending_quiz_id

    @_pending_quiz_id.setter
    def _pending_quiz_id(self, value: int | None) -> None:
        self._state.pending_quiz_id = value

    @property
    def _quiz_info(self) -> QuizInfoDTO | None:
        return self._state.quiz_info

    @_quiz_info.setter
    def _quiz_info(self, value: QuizInfoDTO | None) -> None:
        self._state.quiz_info = value

    @property
    def _quiz_title(self) -> str:
        return self._state.quiz_title

    @_quiz_title.setter
    def _quiz_title(self, value: str) -> None:
        self._state.quiz_title = value

    @property
    def _mode(self) -> str:
        return self._state.mode

    @_mode.setter
    def _mode(self, value: str) -> None:
        self._state.mode = value

    @property
    def _attempt_id(self) -> int | None:
        return self._state.attempt_id

    @_attempt_id.setter
    def _attempt_id(self, value: int | None) -> None:
        self._state.attempt_id = value

    @property
    def _quiz_questions(self) -> list[QuizQuestionSnapshot]:
        return self._state.quiz_questions

    @_quiz_questions.setter
    def _quiz_questions(self, value: list[QuizQuestionSnapshot]) -> None:
        self._state.quiz_questions = value

    @property
    def _current_index(self) -> int:
        return self._state.current_index

    @_current_index.setter
    def _current_index(self, value: int) -> None:
        self._state.current_index = value

    @property
    def _answers(self) -> dict[int, dict]:
        return self._state.answers

    @_answers.setter
    def _answers(self, value: dict[int, dict]) -> None:
        self._state.answers = value

    @property
    def _confirmed(self) -> set[int]:
        return self._state.confirmed

    @_confirmed.setter
    def _confirmed(self, value: set[int]) -> None:
        self._state.confirmed = value

    @property
    def _submitter_name(self) -> str:
        return self._state.submitter_name

    @_submitter_name.setter
    def _submitter_name(self, value: str) -> None:
        self._state.submitter_name = value

    @property
    def _submitter_id(self) -> str:
        return self._state.submitter_id

    @_submitter_id.setter
    def _submitter_id(self, value: str) -> None:
        self._state.submitter_id = value

    @property
    def _started_at(self) -> datetime | None:
        return self._state.started_at

    @_started_at.setter
    def _started_at(self, value: datetime | None) -> None:
        self._state.started_at = value

    @property
    def _remaining_seconds(self) -> int | None:
        return self._state.remaining_seconds

    @_remaining_seconds.setter
    def _remaining_seconds(self, value: int | None) -> None:
        self._state.remaining_seconds = value

    @property
    def _resumed_from_autosave(self) -> bool:
        return self._state.resumed_from_autosave

    @_resumed_from_autosave.setter
    def _resumed_from_autosave(self, value: bool) -> None:
        self._state.resumed_from_autosave = value

    @property
    def _finalizing(self) -> bool:
        return self._state.finalizing

    @_finalizing.setter
    def _finalizing(self, value: bool) -> None:
        self._state.finalizing = value

    @property
    def _retry_submit_only(self) -> bool:
        return self._state.retry_submit_only

    @_retry_submit_only.setter
    def _retry_submit_only(self, value: bool) -> None:
        self._state.retry_submit_only = value
