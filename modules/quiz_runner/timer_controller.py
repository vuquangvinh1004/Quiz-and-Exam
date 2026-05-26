"""Quiz timer controller.

Encapsulates countdown timer logic so QuizRunnerView stays UI-only.

Signals:
    tick(remaining_seconds: int) — emitted every second while running
    time_up()                    — emitted once when remaining hits 0
"""
from __future__ import annotations

from PySide6.QtCore import QObject, QTimer, Signal


class QuizTimerController(QObject):
    """Countdown timer that emits signals; has no UI knowledge."""

    tick = Signal(int)   # remaining seconds
    time_up = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._on_tick)
        self._time_limit_seconds: int = 0
        self._elapsed_seconds: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def elapsed_seconds(self) -> int:
        return self._elapsed_seconds

    def start(self, time_limit_seconds: int) -> None:
        """Start (or restart) the countdown from *time_limit_seconds*."""
        self._time_limit_seconds = time_limit_seconds
        self._elapsed_seconds = 0
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()

    def is_active(self) -> bool:
        return self._timer.isActive()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _on_tick(self) -> None:
        self._elapsed_seconds += 1
        remaining = max(0, self._time_limit_seconds - self._elapsed_seconds)
        self.tick.emit(remaining)
        if remaining == 0:
            self._timer.stop()
            self.time_up.emit()
