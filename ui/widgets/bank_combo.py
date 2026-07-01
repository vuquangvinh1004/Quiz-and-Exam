from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QWidget

from ui.facades.question_bank_facade import QuestionBankFacade


class BankCombo(QComboBox):
    """Bank combo box with reload support and id lookup."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._facade = QuestionBankFacade()

    def reload(self) -> None:
        self.blockSignals(True)
        prev_id = self.currentData(Qt.ItemDataRole.UserRole) if self.currentIndex() >= 0 else None
        self.clear()
        try:
            items = self._facade.list_bank_items()
        except Exception:
            items = []

        for meta in items:
            self.addItem(meta["name"], userData=meta)

        for i in range(self.count()):
            d = self.itemData(i, Qt.ItemDataRole.UserRole)
            if isinstance(d, dict) and d.get("id") == prev_id:
                self.setCurrentIndex(i)
                break
        self.blockSignals(False)

    def current_bank_id(self) -> int | None:
        d = self.currentData(Qt.ItemDataRole.UserRole)
        if isinstance(d, dict):
            return d.get("id")
        return None
