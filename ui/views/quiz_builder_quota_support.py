"""Quota-table support helpers for QuizBuilderView."""
from __future__ import annotations

from PySide6.QtGui import QBrush, QColor

from core.database.models import Question
from modules.quiz_builder.quota_allocator import QuotaPlan, build_inventory, validate_quota_plan


def _set_table_row_warning(table, spin, warning: bool) -> None:
    for row in range(table.rowCount()):
        if table.cellWidget(row, 2) is not spin:
            continue
        color = QColor("#fdecea") if warning else None
        for col in (0, 1, 2):
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
    _apply(view._difficulty_spins, view._difficulty_available, inv.by_difficulty)


def refresh_quota_warnings(view, value_or_questions: object | None = None) -> None:
    questions = value_or_questions if isinstance(value_or_questions, list) else None
    if questions is None:
        questions = view._eligible_questions()

    for spin in view._chapter_spins.values():
        view._clear_spin_warning(spin)
        _set_table_row_warning(view._chapter_table, spin, False)
    for spin in view._type_spins.values():
        view._clear_spin_warning(spin)
        _set_table_row_warning(view._type_table, spin, False)
    for spin in view._difficulty_spins.values():
        view._clear_spin_warning(spin)
        _set_table_row_warning(view._difficulty_table, spin, False)

    plan = QuotaPlan(
        total_questions=view._count_spin.value(),
        chapter_quota=view._quota_dict(view._chapter_spins),
        type_quota=view._quota_dict(view._type_spins),
        difficulty_quota=view._quota_dict(view._difficulty_spins),
    )
    inv = build_inventory(questions)
    result = validate_quota_plan(plan, inv)

    for key in result.chapter_overflow:
        spin = view._chapter_spins.get(key)
        if spin:
            view._mark_spin_warning(spin)
            _set_table_row_warning(view._chapter_table, spin, True)
    for key in result.type_overflow:
        spin = view._type_spins.get(key)
        if spin:
            view._mark_spin_warning(spin)
            _set_table_row_warning(view._type_table, spin, True)
    for key in result.difficulty_overflow:
        spin = view._difficulty_spins.get(key)
        if spin:
            view._mark_spin_warning(spin)
            _set_table_row_warning(view._difficulty_table, spin, True)

    if sum(plan.chapter_quota.values()) > plan.total_questions:
        for spin in view._chapter_spins.values():
            if spin.value() > 0:
                view._mark_spin_warning(spin)
                _set_table_row_warning(view._chapter_table, spin, True)
    if sum(plan.type_quota.values()) > plan.total_questions:
        for spin in view._type_spins.values():
            if spin.value() > 0:
                view._mark_spin_warning(spin)
                _set_table_row_warning(view._type_table, spin, True)
    if sum(plan.difficulty_quota.values()) > plan.total_questions:
        for spin in view._difficulty_spins.values():
            if spin.value() > 0:
                view._mark_spin_warning(spin)
                _set_table_row_warning(view._difficulty_table, spin, True)
