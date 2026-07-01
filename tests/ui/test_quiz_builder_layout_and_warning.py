from __future__ import annotations

import os

import pytest
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication

from core.database.models import Question
from ui.dialogs.question_pool_picker_dialog import QuestionPoolPickerDialog
from ui.views.quiz_builder_view import QuizBuilderView
from ui.views.quiz_runner_view import QuizRunnerView

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp_instance():
    app = QApplication.instance() or QApplication([])
    yield app


def test_quota_tables_render_side_by_side(qapp_instance):
    view = QuizBuilderView()
    view._quota_cb_clo.setChecked(True)
    view._quota_cb_chapter.setChecked(True)
    view._quota_cb_type.setChecked(True)
    view.resize(1400, 900)
    view.show()
    qapp_instance.processEvents()

    clo_box = view._clo_table.parentWidget()
    chapter_box = view._chapter_table.parentWidget()
    type_box = view._type_table.parentWidget()

    clo_pos = clo_box.mapTo(view, QPoint(0, 0))
    chapter_pos = chapter_box.mapTo(view, QPoint(0, 0))
    type_pos = type_box.mapTo(view, QPoint(0, 0))

    assert abs(clo_pos.y() - chapter_pos.y()) <= 4
    assert abs(chapter_pos.y() - type_pos.y()) <= 4
    assert clo_pos.x() < chapter_pos.x() < type_pos.x()


def test_spinbox_min_width_and_quota_row_height(qapp_instance):
    builder = QuizBuilderView()
    builder._reload_chapter_quota_rows(
        [
            Question(
                bank_id=1,
                question_type="MC",
                content="Q1",
                difficulty="easy",
                category="Chương 1",
                learning_outcome_code="CLO_A",
            ),
            Question(
                bank_id=1,
                question_type="MA",
                content="Q2",
                difficulty="medium",
                category="Chương 2",
                learning_outcome_code="CLO_B",
            ),
        ]
    )
    assert builder._exam_count_spin.minimumWidth() >= 120
    assert builder._count_spin.minimumWidth() >= 120
    assert builder._duration_spin.minimumWidth() >= 120

    assert all(spin.minimumWidth() == 56 and spin.maximumWidth() == 56 for spin in builder._type_spins.values())
    assert all(spin.minimumWidth() == 56 and spin.maximumWidth() == 56 for spin in builder._clo_spins.values())
    assert builder._chapter_table.verticalHeader().defaultSectionSize() >= 36
    assert builder._type_table.verticalHeader().defaultSectionSize() >= 36
    assert builder._clo_table.verticalHeader().defaultSectionSize() >= 36
    assert builder._chapter_table.columnWidth(2) >= 80
    assert builder._type_table.columnWidth(2) >= 80
    assert builder._clo_table.columnWidth(3) >= 80
    assert "không chọn checkbox quota nào" in builder._quota_note.text().lower()
    assert "#c0392b" in builder._quota_note.styleSheet().lower()
    assert not builder._clo_table_wrap.isVisible()
    assert not builder._chapter_table_wrap.isVisible()
    assert not builder._type_table_wrap.isVisible()

    runner = QuizRunnerView()
    assert runner._setup_time_spin.minimumWidth() >= 120
    assert runner._setup_count_spin.minimumWidth() >= 120


def test_clo_quota_is_capped_by_available_count(qapp_instance):
    view = QuizBuilderView()

    questions = [
        Question(
            bank_id=1,
            question_type="MC",
            content="Nội dung mẫu",
            difficulty="easy",
            category="Chương 1",
            learning_outcome_code="CLO_A",
        )
    ]

    view._count_spin.setValue(2)
    view._eligible_questions = lambda: questions  # type: ignore[method-assign]
    view._reload_chapter_quota_rows(questions)
    view._type_spins["MC"].setValue(1)
    view._clo_spins[("CLO_A", "Nhớ")].setValue(2)
    view._refresh_quota_warnings(questions)

    assert view._clo_table.item(0, 2).text() == "1"
    assert view._type_spins["MC"].maximum() == 1
    assert view._type_spins["MC"].value() == 1
    assert view._clo_spins[("CLO_A", "Nhớ")].maximum() == 1
    assert view._clo_spins[("CLO_A", "Nhớ")].value() == 1


def test_partial_quota_does_not_warn_when_axis_sum_not_exceed_total(qapp_instance):
    view = QuizBuilderView()

    questions = [
        Question(
            bank_id=1,
            question_type="MC",
            content="Q1",
            difficulty="easy",
            category="Chương 1",
            learning_outcome_code="CLO_A",
        ),
        Question(
            bank_id=1,
            question_type="MA",
            content="Q2",
            difficulty="medium",
            category="Chương 2",
            learning_outcome_code="CLO_B",
        ),
    ]

    view._count_spin.setValue(2)
    view._reload_chapter_quota_rows(questions)
    view._type_spins["MC"].setValue(1)
    view._clo_spins[("CLO_A", "Nhớ")].setValue(1)
    view._refresh_quota_warnings(questions)

    assert "fdecea" not in view._type_spins["MC"].styleSheet().lower()
    assert "fdecea" not in view._clo_spins[("CLO_A", "Nhớ")].styleSheet().lower()


def test_hidden_quota_tables_do_not_participate_in_selection_state(qapp_instance):
    view = QuizBuilderView()
    questions = [
        Question(
            bank_id=1,
            question_type="MC",
            content="Q1",
            difficulty="easy",
            category="Chương 1",
            learning_outcome_code="CLO_A",
        ),
        Question(
            bank_id=1,
            question_type="MA",
            content="Q2",
            difficulty="medium",
            category="Chương 2",
            learning_outcome_code="CLO_B",
        ),
    ]

    view._reload_chapter_quota_rows(questions)
    view._chapter_spins["Chương 1"].setValue(1)
    view._type_spins["MC"].setValue(1)
    view._clo_spins[("CLO_A", "Nhớ")].setValue(1)

    state = view._get_selection_state()
    assert state.chapter_quota == {}
    assert state.type_quota == {}
    assert state.clo_quota == {}
    assert state.question_count == 2

    view._quota_cb_chapter.setChecked(True)
    state = view._get_selection_state()
    assert state.chapter_quota == {"Chương 1": 1}
    assert state.type_quota == {}
    assert state.clo_quota == {}
    assert state.question_count == 1


def test_quota_tables_show_ratio_column_and_update_values(qapp_instance):
    view = QuizBuilderView()
    questions = [
        Question(
            bank_id=1,
            question_type="MC",
            content="Q1",
            difficulty="easy",
            category="Chương 1",
            learning_outcome_code="CLO_A",
        ),
        Question(
            bank_id=1,
            question_type="MA",
            content="Q2",
            difficulty="medium",
            category="Chương 2",
            learning_outcome_code="CLO_B",
        ),
    ]

    view._quota_cb_clo.setChecked(True)
    view._quota_cb_chapter.setChecked(True)
    view._quota_cb_type.setChecked(True)
    view._reload_chapter_quota_rows(questions)
    view._chapter_spins["Chương 1"].setValue(1)
    view._chapter_spins["Chương 2"].setValue(1)
    view._type_spins["MC"].setValue(1)
    view._type_spins["MA"].setValue(1)
    view._clo_spins[("CLO_A", "Nhớ")].setValue(1)
    view._clo_spins[("CLO_B", "Hiểu")].setValue(1)
    view._refresh_quota_warnings(questions)

    assert view._chapter_table.horizontalHeaderItem(3).text() == "Tỷ lệ"
    assert view._clo_table.horizontalHeaderItem(4).text() == "Tỷ lệ"
    assert view._type_table.horizontalHeaderItem(3).text() == "Tỷ lệ"
    assert view._chapter_table.item(0, 3).text() == "50.0%"
    assert view._type_table.item(0, 3).text() == "50.0%"
    assert view._clo_table.item(0, 4).text() == "50.0%"


def test_question_pool_picker_uses_vertical_checkbox_filters(qapp_instance, monkeypatch):
    sample_questions = [
        Question(
            id=1,
            bank_id=1,
            question_type="MC",
            content="Q1",
            question_code="DF_TX01",
            category="Chương 1",
            learning_outcome_code="CLO_1",
            difficulty="easy",
            is_active=True,
        ),
        Question(
            id=2,
            bank_id=1,
            question_type="MA",
            content="Q2",
            question_code="DF_TX02",
            category="Chương 2",
            learning_outcome_code="CLO_2",
            difficulty="hard",
            is_active=True,
        ),
        Question(
            id=3,
            bank_id=1,
            question_type="BLANK",
            content="Q3",
            question_code="DF_TX03",
            category="Chương 3",
            learning_outcome_code="CLO_3",
            difficulty="medium",
            is_active=True,
        ),
    ]

    monkeypatch.setattr(
        "ui.dialogs.question_pool_picker_dialog.QuestionBankFacade.list_questions",
        lambda self, **kwargs: sample_questions,
    )
    dlg = QuestionPoolPickerDialog(1)
    dlg.show()
    qapp_instance.processEvents()

    assert list(dlg._chapter_filters.keys()) == ["Chương 1", "Chương 2", "Chương 3"]
    assert list(dlg._clo_filters.keys()) == ["CLO_1", "CLO_2", "CLO_3"]
    assert list(dlg._difficulty_filters.keys()) == ["Nhớ", "Hiểu", "Vận dụng"]
    assert list(dlg._type_filters.keys()) == ["MC", "MA", "BLANK"]
    assert dlg._filters_table.rowCount() == 4
    assert dlg._filters_table.columnCount() >= 8
    assert dlg._filters_table.showGrid() is False
    assert dlg._filters_table.horizontalHeader().isVisible() is False
    assert dlg._filters_table.columnWidth(0) == 118
    assert dlg._filters_table.columnWidth(1) == 16
    assert dlg._filters_table.columnWidth(2) == 18
    assert dlg._filters_table.columnWidth(3) == 68
    assert dlg._filters_table.columnWidth(4) == 18
    assert dlg._filters_table.columnWidth(5) == 68
    assert dlg._filters_table.height() <= 120
    assert dlg._filters_table.item(0, 0).text() == "Chương:"
    assert dlg._filters_table.item(1, 0).text() == "CLO:"
    assert dlg._filters_table.item(2, 0).text() == "Mức độ:"
    assert dlg._filters_table.item(3, 0).text() == "Loại câu hỏi:"
    assert dlg._filters_table.item(0, 0).font().bold() is True
    assert dlg._filters_table.item(1, 0).font().bold() is True
    assert dlg._filters_table.item(2, 0).font().bold() is True
    assert dlg._filters_table.item(3, 0).font().bold() is True
    assert dlg._filters_table.cellWidget(0, 2) is not None
    assert dlg._filters_table.cellWidget(1, 2) is not None
    assert dlg._filters_table.cellWidget(2, 2) is not None
    assert dlg._filters_table.cellWidget(3, 2) is not None
    assert dlg._filters_table.item(3, 3).text() == "MC"
    assert dlg._filters_table.item(3, 5).text() == "MA"
    assert dlg._table.horizontalHeaderItem(4).text() == "Chương"
    assert dlg._table.horizontalHeaderItem(5).text() == "CLO"
    assert dlg._table.horizontalHeaderItem(6).text() == "Mức độ"
    assert dlg._table.horizontalHeaderItem(7).text() == "Loại câu hỏi"
