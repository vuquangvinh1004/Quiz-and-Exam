"""Quota table and warning helpers for QuizBuilderView."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractSpinBox, QSpinBox, QTableWidget, QTableWidgetItem

from modules.quiz_builder.quota_allocator import build_inventory, chapter_key
from ui.views.quiz_builder_quota_support import refresh_quota_warnings, sync_quota_availability
from ui.views.quiz_builder_shared import _DIFFICULTY_LEVEL_ORDER, center_item, short_type_label


class QuizBuilderQuotaMixin:
    """Quota row management, ratio updates, and warning styling."""

    def _reload_chapter_quota_rows(self, questions: list) -> None:
        old_values = {name: spin.value() for name, spin in self._chapter_spins.items()}
        self._chapter_spins.clear()
        self._chapter_available.clear()
        self._chapter_ratio.clear()
        self._chapter_table.setRowCount(0)

        inv = build_inventory(questions)
        chapters = sorted({chapter_key(q.category) for q in questions})
        for chap in chapters:
            spin, available_item = self._append_quota_row(
                self._chapter_table,
                chap,
                available=inv.by_chapter.get(chap, 0),
            )
            spin.setValue(min(old_values.get(chap, 0), spin.maximum()))
            self._chapter_spins[chap] = spin
            self._chapter_available[chap] = available_item

        self._reload_type_quota_rows(questions)
        self._reload_clo_quota_rows(questions)

    def _reload_type_quota_rows(self, questions: list) -> None:
        old_values = {key: spin.value() for key, spin in self._type_spins.items()}
        self._type_spins.clear()
        self._type_available.clear()
        self._type_ratio.clear()
        self._type_table.setRowCount(0)

        inv = build_inventory(questions)
        type_order = ("MC", "MA", "TF", "BLANK", "SA", "ES", "PR")
        for qtype in type_order:
            available = inv.by_type.get(qtype, 0)
            if available <= 0:
                continue
            spin, available_item = self._append_quota_row(
                self._type_table,
                short_type_label(qtype),
                available=available,
            )
            spin.setValue(min(old_values.get(qtype, 0), spin.maximum()))
            self._type_spins[qtype] = spin
            self._type_available[qtype] = available_item

    def _reload_clo_quota_rows(self, questions: list) -> None:
        old_values = {key: spin.value() for key, spin in self._clo_spins.items()}
        self._clo_spins.clear()
        self._clo_available.clear()
        self._clo_ratio.clear()
        self._clo_table.setRowCount(0)

        inv = build_inventory(questions)
        clo_rows = sorted(
            inv.by_clo.items(),
            key=lambda item: (
                item[0][0].lower(),
                _DIFFICULTY_LEVEL_ORDER.index(item[0][1])
                if item[0][1] in _DIFFICULTY_LEVEL_ORDER
                else len(_DIFFICULTY_LEVEL_ORDER),
                item[0][1].lower(),
            ),
        )
        for (clo, level), available in clo_rows:
            spin, available_item = self._append_clo_quota_row(
                self._clo_table,
                clo,
                level,
                available=available,
            )
            spin.setValue(min(old_values.get((clo, level), 0), spin.maximum()))
            self._clo_spins[(clo, level)] = spin
            self._clo_available[(clo, level)] = available_item

    def _append_quota_row(
        self,
        table: QTableWidget,
        label: str,
        *,
        available: int = 0,
    ) -> tuple[QSpinBox, QTableWidgetItem]:
        row = table.rowCount()
        table.insertRow(row)
        table.setItem(row, 0, center_item(label))

        available_item = QTableWidgetItem(str(available))
        available_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        available_item.setFlags(available_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        table.setItem(row, 1, available_item)

        spin = QSpinBox()
        spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        spin.setRange(0, max(0, available))
        spin.setFixedWidth(56)
        spin.setFixedHeight(30)
        spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        spin.valueChanged.connect(self._refresh_quota_warnings)
        table.setCellWidget(row, 2, spin)
        ratio_item = center_item("0.0%")
        table.setItem(row, 3, ratio_item)
        return spin, available_item

    def _append_clo_quota_row(
        self,
        table: QTableWidget,
        clo: str,
        level: str,
        *,
        available: int = 0,
    ) -> tuple[QSpinBox, QTableWidgetItem]:
        row = table.rowCount()
        table.insertRow(row)
        table.setItem(row, 0, center_item(clo))
        table.setItem(row, 1, center_item(level))

        available_item = QTableWidgetItem(str(available))
        available_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        available_item.setFlags(available_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        table.setItem(row, 2, available_item)

        spin = QSpinBox()
        spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        spin.setRange(0, max(0, available))
        spin.setFixedWidth(56)
        spin.setFixedHeight(30)
        spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        spin.valueChanged.connect(self._refresh_quota_warnings)
        table.setCellWidget(row, 3, spin)
        ratio_item = center_item("0.0%")
        table.setItem(row, 4, ratio_item)
        return spin, available_item

    def _append_type_quota_row(
        self,
        table: QTableWidget,
        label: str,
        *,
        available: int = 0,
    ) -> tuple[QSpinBox, QTableWidgetItem]:
        return self._append_quota_row(table, label, available=available)

    def _sync_quota_availability(self, questions: list) -> None:
        sync_quota_availability(self, questions)

    def _quota_dict(self, source: dict) -> dict:
        return {
            key: spin.value()
            for key, spin in source.items()
            if spin.value() > 0
        }

    def _active_quota_dict(self, source: dict, enabled: bool) -> dict:
        return self._quota_dict(source) if enabled else {}

    @staticmethod
    def _ratio_text(value: int, total: int) -> str:
        if total <= 0:
            return "0.0%"
        return f"{(value / total) * 100:.1f}%"

    def _update_quota_ratios(self) -> None:
        total = max(1, self._count_spin.value())

        for row in range(self._chapter_table.rowCount()):
            spin = self._chapter_table.cellWidget(row, 2)
            item = self._chapter_table.item(row, 3)
            if isinstance(spin, QSpinBox) and item is not None:
                item.setText(self._ratio_text(spin.value(), total))

        for row in range(self._type_table.rowCount()):
            spin = self._type_table.cellWidget(row, 2)
            item = self._type_table.item(row, 3)
            if isinstance(spin, QSpinBox) and item is not None:
                item.setText(self._ratio_text(spin.value(), total))

        for row in range(self._clo_table.rowCount()):
            spin = self._clo_table.cellWidget(row, 3)
            item = self._clo_table.item(row, 4)
            if isinstance(spin, QSpinBox) and item is not None:
                item.setText(self._ratio_text(spin.value(), total))

    def _total_questions_from_quota(self) -> int:
        active_totals: list[int] = []
        if self._quota_cb_chapter.isChecked():
            active_totals.append(sum(self._chapter_spins[chap].value() for chap in self._chapter_spins))
        if self._quota_cb_type.isChecked():
            active_totals.append(sum(self._type_spins[qtype].value() for qtype in self._type_spins))
        if self._quota_cb_clo.isChecked():
            active_totals.append(sum(self._clo_spins[key].value() for key in self._clo_spins))

        if active_totals:
            return max(1, max(active_totals))
        try:
            return max(1, len(self._eligible_questions()))
        except Exception:
            return max(1, self._count_spin.value())

    def _sync_total_question_count(self) -> None:
        total = self._total_questions_from_quota()
        if self._count_spin.value() != total:
            self._count_spin.blockSignals(True)
            self._count_spin.setValue(total)
            self._count_spin.blockSignals(False)

    def _clear_spin_warning(self, spin: QSpinBox) -> None:
        spin.setStyleSheet("")

    def _mark_spin_warning(self, spin: QSpinBox) -> None:
        spin.setStyleSheet(
            "QSpinBox { background-color: #f8d7da; }"
            "QSpinBox QLineEdit { background-color: #f8d7da; }"
        )

    def _refresh_quota_warnings(self, value_or_questions: object | None = None) -> None:
        self._sync_total_question_count()
        self._update_quota_ratios()
        refresh_quota_warnings(self, value_or_questions)

    @staticmethod
    def _chapter_key(value: str) -> str:
        return chapter_key(value)
