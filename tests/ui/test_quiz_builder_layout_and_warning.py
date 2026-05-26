from __future__ import annotations

import os

import pytest
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication

from core.database.models import Question
from ui.views.quiz_builder_view import QuizBuilderView
from ui.views.quiz_runner_view import QuizRunnerView

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp_instance():
    app = QApplication.instance() or QApplication([])
    yield app


def test_quota_tables_render_side_by_side(qapp_instance):
    view = QuizBuilderView()
    view.resize(1400, 900)
    view.show()
    qapp_instance.processEvents()

    chapter_box = view._chapter_table.parentWidget()
    type_box = view._type_table.parentWidget()
    diff_box = view._difficulty_table.parentWidget()

    chapter_pos = chapter_box.mapTo(view, QPoint(0, 0))
    type_pos = type_box.mapTo(view, QPoint(0, 0))
    diff_pos = diff_box.mapTo(view, QPoint(0, 0))

    assert abs(chapter_pos.y() - type_pos.y()) <= 4
    assert abs(type_pos.y() - diff_pos.y()) <= 4
    assert chapter_pos.x() < type_pos.x() < diff_pos.x()


def test_spinbox_min_width_and_quota_row_height(qapp_instance):
    builder = QuizBuilderView()
    assert builder._exam_count_spin.minimumWidth() >= 120
    assert builder._count_spin.minimumWidth() >= 120
    assert builder._duration_spin.minimumWidth() >= 120

    assert all(spin.minimumWidth() >= 140 for spin in builder._type_spins.values())
    assert all(spin.minimumWidth() >= 140 for spin in builder._difficulty_spins.values())
    assert builder._type_table.verticalHeader().defaultSectionSize() >= 36
    assert builder._difficulty_table.verticalHeader().defaultSectionSize() >= 36

    runner = QuizRunnerView()
    assert runner._setup_time_spin.minimumWidth() >= 120
    assert runner._setup_count_spin.minimumWidth() >= 120


def test_type_quota_is_capped_by_available_count(qapp_instance):
    view = QuizBuilderView()

    questions = [
        Question(
            bank_id=1,
            question_type="MC",
            content="Nội dung mẫu",
            difficulty="easy",
            category="Chương 1",
        )
    ]

    view._count_spin.setValue(2)
    view._sync_quota_availability(questions)
    view._type_spins["MC"].setValue(2)
    view._refresh_quota_warnings(questions)

    assert view._type_table.item(0, 1).text() == "1"
    assert view._type_spins["MC"].maximum() == 1
    assert view._type_spins["MC"].value() == 1


def test_partial_quota_does_not_warn_when_axis_sum_not_exceed_total(qapp_instance):
    view = QuizBuilderView()

    questions = [
        Question(
            bank_id=1,
            question_type="MC",
            content="Q1",
            difficulty="easy",
            category="Chương 1",
        ),
        Question(
            bank_id=1,
            question_type="MA",
            content="Q2",
            difficulty="medium",
            category="Chương 2",
        ),
    ]

    view._count_spin.setValue(2)
    view._sync_quota_availability(questions)
    view._type_spins["MC"].setValue(1)
    view._refresh_quota_warnings(questions)

    assert "fdecea" not in view._type_spins["MC"].styleSheet().lower()
