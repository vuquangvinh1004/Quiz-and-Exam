from __future__ import annotations

from core.database.models import Question
from ui.dialogs.question_editor_dialog import QuestionEditorDialog
from ui.facades.question_bank_facade import BankMetaData, QuestionBankFacade


def _bank_meta() -> BankMetaData:
    return BankMetaData(
        name="Ngân hàng 1",
        school="",
        department="",
        subject="",
        course_code="",
        exam_title="",
        assessment_type="Thường xuyên",
        course_learning_outcomes=[
            {"code": "CLO_1", "description": "Mô tả 1"},
            {"code": "CLO_2", "description": "Mô tả 2"},
        ],
    )


def test_question_editor_dialog_uses_new_question_fields(monkeypatch, qtbot) -> None:
    monkeypatch.setattr(
        QuestionBankFacade,
        "get_bank_metadata",
        lambda self, bank_id: _bank_meta(),
    )

    dlg = QuestionEditorDialog(bank_id=1)
    qtbot.addWidget(dlg)

    assert dlg._formula_preview_group.title() == "Xem trước câu hỏi"
    assert dlg._formula_preview_toggle.isChecked() is True
    assert dlg._formula_preview_toggle.text() == "Thu gọn"
    assert dlg._formula_preview_browser.minimumHeight() >= 280
    assert dlg._type_combo.itemText(dlg._type_combo.count() - 1) == "Trả lời ngắn"
    assert dlg._type_combo.findData("ES") == -1
    assert dlg._learning_outcome_combo.count() == 3
    assert dlg._difficulty_combo.itemText(0) == "Nhớ"

    dlg._type_combo.setCurrentIndex(dlg._type_combo.findData("SA"))
    dlg._difficulty_combo.setCurrentIndex(dlg._difficulty_combo.findData("Sáng tạo"))
    assert dlg._score_spin.value() == 10.0

    dlg._score_spin.setValue(7.5)
    assert dlg._score_spin.value() == 7.5


def test_question_editor_dialog_loads_clo_and_legacy_difficulty(monkeypatch, qtbot) -> None:
    monkeypatch.setattr(
        QuestionBankFacade,
        "get_bank_metadata",
        lambda self, bank_id: _bank_meta(),
    )

    question = Question(
        bank_id=1,
        question_type="SA",
        content="Viết câu trả lời",
        difficulty="medium",
        learning_outcome_code="CLO_2",
        point_value=2.0,
        is_active=True,
    )

    dlg = QuestionEditorDialog(bank_id=1, question=question)
    qtbot.addWidget(dlg)

    assert dlg._basic_info_toggle.isChecked() is False
    assert dlg._basic_info_content.isVisible() is False
    assert dlg._learning_outcome_combo.currentData() == "CLO_2"
    assert dlg._difficulty_combo.currentData() == "Vận dụng"


def test_question_editor_dialog_renders_formula_preview(monkeypatch, qtbot) -> None:
    monkeypatch.setattr(
        QuestionBankFacade,
        "get_bank_metadata",
        lambda self, bank_id: _bank_meta(),
    )

    dlg = QuestionEditorDialog(bank_id=1)
    qtbot.addWidget(dlg)

    dlg._type_combo.setCurrentIndex(dlg._type_combo.findData("SA"))
    dlg._content_edit.setPlainText("Xác định $t_{\\alpha; n-1}$ và $H_0$")
    dlg._hint_edit.setText("Dùng $\\sqrt{n}$ để chuẩn hóa")
    dlg._explanation_edit.setPlainText("Kết luận với $\\mu_0$")
    dlg._answers_edit.setText("Đáp án $\\alpha$||Đáp án 2")
    dlg._refresh_formula_preview()

    html = dlg._formula_preview_browser.toHtml()
    assert "t_{\\alpha; n-1}" not in html
    assert "Xác định" in html
    assert "Dùng" in html
    assert "Kết luận" in html
    assert "Đáp án" in html
    assert "sub" in html or "math" in html
