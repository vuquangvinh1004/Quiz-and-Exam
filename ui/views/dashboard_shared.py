"""Shared helpers for DashboardView."""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget, QSizePolicy

from ui.facades.dashboard_facade import DashboardFacade


class _DashboardOverviewWorker(QObject):
    """Load dashboard overview data in a background thread."""

    finished = Signal(object, object, object, object)

    def __init__(self, facade: DashboardFacade) -> None:
        super().__init__()
        self._facade = facade

    def run(self) -> None:
        try:
            overview = self._facade.load_overview()
            usage_banks = self._facade.load_usage_banks()
            warning_summary = self._facade.load_warning_summary()
            self.finished.emit(overview, usage_banks, warning_summary, None)
        except (RuntimeError, ValueError, OSError) as exc:  # pragma: no cover
            self.finished.emit(None, [], None, str(exc))


class _StatCard(QFrame):
    """A simple flat card showing a label and a large value."""

    def __init__(self, label: str, value: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("stat_card")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFixedHeight(90)
        self.setMinimumWidth(130)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        vl = QVBoxLayout(self)
        vl.setContentsMargins(14, 10, 14, 10)
        vl.setSpacing(2)
        self._lbl = QLabel(label)
        self._lbl.setObjectName("stat_card_label")
        self._val = QLabel(value)
        self._val.setObjectName("stat_card_value")
        vl.addWidget(self._lbl)
        vl.addWidget(self._val)

    def set_value(self, value: str) -> None:
        self._val.setText(value)
