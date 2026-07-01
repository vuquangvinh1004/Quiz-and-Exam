from __future__ import annotations

from ui.dialogs.bank_meta_dialog import BankMetaDialog


def test_bank_meta_dialog_uses_new_labels_and_fields(qtbot) -> None:
    dlg = BankMetaDialog()
    qtbot.addWidget(dlg)

    assert dlg.windowTitle() == "Thêm ngân hàng câu hỏi"
    assert dlg._assessment_type.count() >= 4
    assert dlg._assessment_type.itemText(1) == "Thường xuyên"
    assert dlg._subject.placeholderText() == "Tùy chọn"
    assert len(dlg._clo_rows) == 1


def test_bank_meta_dialog_round_trips_assessment_type_and_clos(qtbot) -> None:
    dlg = BankMetaDialog(
        initial_data={
            "name": "NHCH 1",
            "subject": "Lập trình Python",
            "assessment_type": "Định kỳ",
            "course_learning_outcomes": [
                {"code": "CLO_1", "description": "Mô tả 1"},
            ],
            "exam_title": "Legacy title",
        }
    )
    qtbot.addWidget(dlg)

    dlg._add_clo_row(code="CLO_2", description="Mô tả 2")
    data = dlg.get_data()

    assert data["subject"] == "Lập trình Python"
    assert data["assessment_type"] == "Định kỳ"
    assert data["exam_title"] == "Legacy title"
    assert data["course_learning_outcomes"] == [
        {"code": "CLO_1", "description": "Mô tả 1"},
        {"code": "CLO_2", "description": "Mô tả 2"},
    ]
