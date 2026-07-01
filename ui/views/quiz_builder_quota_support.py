"""Quota-table support helpers for QuizBuilderView."""
from __future__ import annotations

from PySide6.QtGui import QBrush, QColor

from core.database.models import Question
from modules.quiz_builder.quota_allocator import QuotaPlan, build_inventory, validate_quota_plan


def _set_table_row_warning(table, spin, warning: bool, *, spin_col: int = 2, max_col: int = 2) -> None:
    for row in range(table.rowCount()):
        if table.cellWidget(row, spin_col) is not spin:
            continue
        color = QColor("#fdecea") if warning else None
        for col in range(max_col + 1):
            item = table.item(row, col)
            if item is not None:
                item.setBackground(QBrush(color) if color is not None else QBrush())
        break


def sync_quota_availability(view, questions: list[Question]) -> None:
    inv = build_inventory(questions)

    def _apply(spins, available_items, counts) -> None:
        for key, spin in spins.items():
            available = counts.get(key, 0)
            item = available_items.get(key)
            if item is not None:
                item.setText(str(available))
            spin.setMaximum(max(0, available))
            if spin.value() > available:
                spin.setValue(available)

    _apply(view._chapter_spins, view._chapter_available, inv.by_chapter)
    _apply(view._type_spins, view._type_available, inv.by_type)
    _apply(view._clo_spins, view._clo_available, inv.by_clo)


def refresh_quota_warnings(view, value_or_questions: object | None = None) -> None:
    questions = value_or_questions if isinstance(value_or_questions, list) else None
    if questions is None:
        questions = view._eligible_questions()

    for spin in view._chapter_spins.values():
        view._clear_spin_warning(spin)
        _set_table_row_warning(view._chapter_table, spin, False, spin_col=2, max_col=3)
    for spin in view._type_spins.values():
        view._clear_spin_warning(spin)
        _set_table_row_warning(view._type_table, spin, False, spin_col=2, max_col=3)
    for spin in view._clo_spins.values():
        view._clear_spin_warning(spin)
        _set_table_row_warning(view._clo_table, spin, False, spin_col=3, max_col=3)

    chapter_quota = view._active_quota_dict(view._chapter_spins, view._quota_cb_chapter.isChecked())
    type_quota = view._active_quota_dict(view._type_spins, view._quota_cb_type.isChecked())
    clo_quota = view._active_quota_dict(view._clo_spins, view._quota_cb_clo.isChecked())

    plan = QuotaPlan(
        total_questions=view._count_spin.value(),
        chapter_quota=chapter_quota,
        type_quota=type_quota,
        clo_quota=clo_quota,
    )
    inv = build_inventory(questions)
    result = validate_quota_plan(plan, inv)

    for key in result.chapter_overflow:
        spin = view._chapter_spins.get(key)
        if spin:
            view._mark_spin_warning(spin)
            _set_table_row_warning(view._chapter_table, spin, True, spin_col=2, max_col=3)
    for key in result.type_overflow:
        spin = view._type_spins.get(key)
        if spin:
            view._mark_spin_warning(spin)
            _set_table_row_warning(view._type_table, spin, True, spin_col=2, max_col=3)
    for key in result.clo_overflow:
        spin = view._clo_spins.get(key)
        if spin:
            view._mark_spin_warning(spin)
            _set_table_row_warning(view._clo_table, spin, True, spin_col=3, max_col=3)

    if sum(plan.chapter_quota.values()) > plan.total_questions:
        for spin in view._chapter_spins.values():
            if spin.value() > 0:
                view._mark_spin_warning(spin)
                _set_table_row_warning(view._chapter_table, spin, True, spin_col=2, max_col=3)
    if sum(plan.type_quota.values()) > plan.total_questions:
        for spin in view._type_spins.values():
            if spin.value() > 0:
                view._mark_spin_warning(spin)
                _set_table_row_warning(view._type_table, spin, True, spin_col=2, max_col=3)
    if sum(plan.clo_quota.values()) > plan.total_questions:
        for spin in view._clo_spins.values():
            if spin.value() > 0:
                view._mark_spin_warning(spin)
                _set_table_row_warning(view._clo_table, spin, True, spin_col=3, max_col=3)
