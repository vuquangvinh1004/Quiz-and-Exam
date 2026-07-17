from __future__ import annotations

from types import SimpleNamespace

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QDialog,
    QLineEdit,
    QMessageBox,
)

from core.database.models import Question
from ui.dialogs.problem_editor_dialog import (
    ProblemEditorDialog,
    _ProblemTemplateSaveDialog,
    _render_template_preview_html,
)
from ui.dialogs.problem_template_picker_dialog import ProblemTemplatePickerDialog
from ui.facades.question_bank_facade import BankMetaData, QuestionBankFacade


def _bank_meta() -> BankMetaData:
    return BankMetaData(
        name="Ngân hàng bài toán",
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


def test_problem_editor_dialog_defaults(monkeypatch, qtbot) -> None:
    monkeypatch.setattr(
        QuestionBankFacade,
        "get_bank_metadata",
        lambda self, bank_id: _bank_meta(),
    )

    dlg = ProblemEditorDialog(bank_id=1)
    qtbot.addWidget(dlg)

    assert dlg.windowTitle() == "Thêm CRQ"
    assert dlg._question_preview_browser is not None
    assert dlg._question_preview_toggle.isChecked() is True
    assert dlg._question_preview_toggle.text() == "Thu gọn"
    assert dlg._question_preview_browser.minimumHeight() <= 120
    assert dlg._formula_preview_browser is not None
    assert dlg._formula_preview_hint.text() == "Hiển thị nhanh rubric đang chọn và công thức hiển thị."
    assert dlg._difficulty_combo.count() == 4
    assert dlg._difficulty_combo.itemText(0) == "Vận dụng"
    assert dlg._data_row_count() == 2
    assert dlg._score_spin.value() == 4.0
    assert dlg._add_marker_btn.text() == "+ Thêm #"
    assert dlg._add_row_btn.text() == "+ Thêm hàng"
    assert dlg._delete_row_btn.text() == "Xóa hàng"
    assert dlg._delete_marker_btn.text() == "Xóa #"
    assert dlg._save_template_btn.text() == "Thêm MẪU"
    assert dlg._load_template_btn.text() == "Dùng MẪU"
    assert dlg._rubric_table.columnWidth(0) >= 80
    assert dlg._rubric_table.columnWidth(2) >= 100
    assert "Ctrl+Enter" in dlg._shortcut_hint_lbl.text()
    assert hasattr(dlg, "_formula_preview_browser")


def test_problem_editor_dialog_preview_renders_latex(monkeypatch, qtbot) -> None:
    monkeypatch.setattr(
        QuestionBankFacade,
        "get_bank_metadata",
        lambda self, bank_id: _bank_meta(),
    )

    dlg = ProblemEditorDialog(bank_id=1)
    qtbot.addWidget(dlg)

    dlg._content_edit.setPlainText("Kiểm tra $t=\\frac{\\bar{x}-\\mu_0}{s/\\sqrt{n}}$")
    dlg._rubric_table.item(0, 0).setText("B1")
    dlg._rubric_table.item(0, 1).setText("Áp dụng $\\sqrt{n}$ và $\\mu_0$")
    dlg._rubric_table.item(0, 2).setText("0.125")
    dlg._rubric_table.setCurrentCell(0, 1)
    dlg._refresh_formula_preview()

    preview = dlg._formula_preview_browser.toPlainText()
    assert "\\frac" not in preview
    assert "\\sqrt" not in preview
    assert "μ0" in preview
    assert "√" in preview
    assert "Mã nhóm:" in preview
    assert "Điểm:" in preview
    assert "Rubric đang chọn" in preview

    question_preview = dlg._question_preview_browser.toPlainText()
    assert "Nội dung CRQ" in question_preview
    assert "Kiểm tra" in question_preview


def test_problem_editor_dialog_copy_formula_button_uses_selected_formula(monkeypatch, qtbot) -> None:
    monkeypatch.setattr(
        QuestionBankFacade,
        "get_bank_metadata",
        lambda self, bank_id: _bank_meta(),
    )

    dlg = ProblemEditorDialog(bank_id=1)
    qtbot.addWidget(dlg)

    dlg._content_edit.setPlainText("")
    dlg._rubric_table.item(0, 1).setText("Áp dụng $\\sqrt{n}$")
    dlg._rubric_table.setCurrentCell(0, 1)
    dlg._copy_formula_snippet()

    assert QApplication.clipboard().text() == "Áp dụng $\\sqrt{n}$"


def test_problem_editor_dialog_shows_warning_when_rubric_exceeds_score(monkeypatch, qtbot) -> None:
    monkeypatch.setattr(
        QuestionBankFacade,
        "get_bank_metadata",
        lambda self, bank_id: _bank_meta(),
    )

    dlg = ProblemEditorDialog(bank_id=1)
    qtbot.addWidget(dlg)

    dlg._rubric_table.item(0, 1).setText("Bước 1")
    dlg._rubric_table.item(0, 2).setText("3")
    dlg._rubric_table.item(1, 1).setText("Bước 2")
    dlg._rubric_table.item(1, 2).setText("3")
    dlg._score_spin.setValue(5.0)
    dlg._refresh_rubric_summary()

    assert dlg._rubric_warning_lbl.isHidden() is False
    assert dlg._rubric_table.item(0, 2).foreground().color() == dlg._rubric_table.item(1, 2).foreground().color()
    assert dlg._rubric_table.item(0, 2).textAlignment() == int(Qt.AlignmentFlag.AlignCenter)


def test_problem_editor_dialog_loads_existing_problem(monkeypatch, qtbot) -> None:
    monkeypatch.setattr(
        QuestionBankFacade,
        "get_bank_metadata",
        lambda self, bank_id: _bank_meta(),
    )

    question = Question(
        bank_id=1,
        question_type="ES",
        content="Giải bài toán",
        difficulty="Đánh giá",
        point_value=8.0,
        is_active=True,
    )
    question.set_accepted_answers(
        {
            "kind": "problem",
            "answers": ["Bước 1", "Bước 2"],
            "rubric": [
                {"marker": "B1", "content": "Bước 1", "score": 3.0},
                {"marker": "B2", "content": "Bước 2", "score": 5.0},
            ],
        }
    )

    dlg = ProblemEditorDialog(bank_id=1, question=question)
    qtbot.addWidget(dlg)

    assert dlg._basic_info_toggle.isChecked() is False
    assert dlg._basic_info_content.isVisible() is False
    assert dlg._difficulty_combo.currentData() == "Đánh giá"
    assert dlg._score_spin.value() == 8.0
    assert dlg._rubric_table.item(0, 0).text() == "B1"
    assert dlg._rubric_table.item(1, 1).text() == "Bước 2"


def test_problem_editor_dialog_adds_content_row_inside_selected_marker(monkeypatch, qtbot) -> None:
    monkeypatch.setattr(
        QuestionBankFacade,
        "get_bank_metadata",
        lambda self, bank_id: _bank_meta(),
    )

    dlg = ProblemEditorDialog(bank_id=1)
    qtbot.addWidget(dlg)
    dlg._rubric_table.item(0, 0).setText("a")
    dlg._rubric_table.setCurrentCell(0, 1)

    dlg._add_content_row()

    assert dlg._data_row_count() == 3
    assert dlg._rubric_table.rowSpan(0, 0) == 2
    assert dlg._rubric_table.item(1, 0).text() == ""


def test_problem_editor_dialog_adds_new_marker_row(monkeypatch, qtbot) -> None:
    monkeypatch.setattr(
        QuestionBankFacade,
        "get_bank_metadata",
        lambda self, bank_id: _bank_meta(),
    )

    dlg = ProblemEditorDialog(bank_id=1)
    qtbot.addWidget(dlg)

    dlg._add_marker_row()

    assert dlg._data_row_count() == 3
    assert dlg._rubric_table.rowSpan(0, 0) == 1


def test_problem_editor_dialog_resizes_long_content_rows(monkeypatch, qtbot) -> None:
    monkeypatch.setattr(
        QuestionBankFacade,
        "get_bank_metadata",
        lambda self, bank_id: _bank_meta(),
    )

    dlg = ProblemEditorDialog(bank_id=1)
    qtbot.addWidget(dlg)

    dlg._rubric_table.item(0, 1).setText(
        "Đây là một nội dung đáp án khá dài để kiểm tra việc tự xuống dòng và tự tăng chiều cao hàng."
    )
    dlg._refresh_rubric_summary()

    assert dlg._rubric_table.rowHeight(0) > 38


def test_problem_editor_dialog_deletes_selected_content_row(monkeypatch, qtbot) -> None:
    monkeypatch.setattr(
        QuestionBankFacade,
        "get_bank_metadata",
        lambda self, bank_id: _bank_meta(),
    )

    dlg = ProblemEditorDialog(bank_id=1)
    qtbot.addWidget(dlg)
    dlg._rubric_table.item(0, 0).setText("a")
    dlg._rubric_table.item(0, 1).setText("Dòng 1")
    dlg._rubric_table.setCurrentCell(0, 1)
    dlg._add_content_row()
    dlg._rubric_table.item(1, 1).setText("Dòng 2")
    dlg._rubric_table.setCurrentCell(1, 1)

    dlg._delete_content_row()

    assert dlg._data_row_count() == 2
    assert dlg._rubric_table.rowSpan(0, 0) == 1
    assert dlg._rubric_table.item(0, 1).text() == "Dòng 1"


def test_problem_editor_dialog_deletes_selected_marker_group(monkeypatch, qtbot) -> None:
    monkeypatch.setattr(
        QuestionBankFacade,
        "get_bank_metadata",
        lambda self, bank_id: _bank_meta(),
    )
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
    )

    dlg = ProblemEditorDialog(bank_id=1)
    qtbot.addWidget(dlg)
    dlg._rubric_table.item(0, 0).setText("a")
    dlg._rubric_table.item(0, 1).setText("A1")
    dlg._rubric_table.setCurrentCell(0, 1)
    dlg._add_content_row()
    dlg._rubric_table.item(1, 1).setText("A2")
    dlg._add_marker_row()
    dlg._rubric_table.item(2, 0).setText("b")
    dlg._rubric_table.item(2, 1).setText("B1")
    dlg._rubric_table.setCurrentCell(0, 1)

    dlg._delete_marker_group()

    assert dlg._data_row_count() == 2
    assert dlg._rubric_table.item(0, 0).text() == "b"
    assert dlg._rubric_table.item(0, 1).text() == "B1"


def test_problem_editor_dialog_cancel_delete_marker_group(monkeypatch, qtbot) -> None:
    monkeypatch.setattr(
        QuestionBankFacade,
        "get_bank_metadata",
        lambda self, bank_id: _bank_meta(),
    )
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.No,
    )

    dlg = ProblemEditorDialog(bank_id=1)
    qtbot.addWidget(dlg)
    dlg._rubric_table.item(0, 0).setText("a")
    dlg._rubric_table.item(0, 1).setText("A1")
    dlg._rubric_table.setCurrentCell(0, 1)
    dlg._add_content_row()
    dlg._rubric_table.item(1, 1).setText("A2")

    dlg._delete_marker_group()

    assert dlg._data_row_count() == 3
    assert dlg._rubric_table.item(0, 1).text() == "A1"


def test_problem_editor_dialog_save_template_uses_current_rows(monkeypatch, qtbot) -> None:
    monkeypatch.setattr(
        QuestionBankFacade,
        "get_bank_metadata",
        lambda self, bank_id: _bank_meta(),
    )
    saved = {}

    def _save_problem_template(self, bank_id, name, rows):
        saved["bank_id"] = bank_id
        saved["name"] = name
        saved["rows"] = rows
        return SimpleNamespace(name=name, row_count=len(rows))

    monkeypatch.setattr(QuestionBankFacade, "save_problem_template", _save_problem_template)
    monkeypatch.setattr(
        _ProblemTemplateSaveDialog,
        "exec",
        lambda self: QDialog.DialogCode.Accepted,
    )
    monkeypatch.setattr(
        QMessageBox,
        "information",
        lambda *args, **kwargs: QMessageBox.StandardButton.Ok,
    )

    dlg = ProblemEditorDialog(bank_id=1)
    qtbot.addWidget(dlg)
    dlg._code_edit.setText("Mẫu 1")
    dlg._rubric_table.item(0, 0).setText("a")
    dlg._rubric_table.item(0, 1).setText("A1")
    dlg._rubric_table.item(0, 2).setText("1")

    dlg._save_problem_template()

    assert saved["bank_id"] == 1
    assert saved["name"] == "Mẫu 1"
    assert saved["rows"][0].content == "A1"


def test_problem_template_save_dialog_renders_formula_preview(monkeypatch, qtbot) -> None:
    monkeypatch.setattr(
        QuestionBankFacade,
        "get_bank_metadata",
        lambda self, bank_id: _bank_meta(),
    )

    rows = [
        SimpleNamespace(marker="B1", content=r"$f(x)=\begin{cases}x^2 & x<0 \\ x & x\ge 0\end{cases}$", score=0.25),
        SimpleNamespace(marker="", content=r"$\begin{pmatrix}1 & 2 \\ 3 & 4\end{pmatrix}$", score=0.75),
    ]
    dlg = _ProblemTemplateSaveDialog(rows, default_name="Mẫu thử")
    qtbot.addWidget(dlg)

    html = _render_template_preview_html(rows)
    assert "\\begin" not in html
    assert "if" in html
    assert "1" in html and "4" in html
    assert "TỔNG" in html


def test_problem_template_save_dialog_uses_subscript_html(monkeypatch, qtbot) -> None:
    rows = [
        SimpleNamespace(marker="", content=r"$t_{\alpha; n-1}$", score=1.0),
    ]
    dlg = _ProblemTemplateSaveDialog(rows, default_name="Mẫu thử")
    qtbot.addWidget(dlg)

    html = _render_template_preview_html(rows)
    assert "<sub>" in html
    assert "α; n-1" in html


def test_problem_template_picker_dialog_renders_latex_preview(monkeypatch, qtbot) -> None:
    monkeypatch.setattr(
        QuestionBankFacade,
        "get_bank_metadata",
        lambda self, bank_id: _bank_meta(),
    )
    monkeypatch.setattr(
        QuestionBankFacade,
        "get_problem_template",
        lambda self, template_id: SimpleNamespace(
            template_id=template_id,
            bank_id=1,
            name="Mẫu với công thức",
            rows=[
                SimpleNamespace(marker="B1", content=r"$t_{\alpha; n-1}$", score=0.25),
                SimpleNamespace(marker="", content=r"$\begin{pmatrix}1 & 2 \\ 3 & 4\end{pmatrix}$", score=0.75),
            ],
        ),
    )

    templates = [
        SimpleNamespace(template_id=77, name="Mẫu với công thức", row_count=2, total_score=1.0)
    ]
    dlg = ProblemTemplatePickerDialog(templates, facade=QuestionBankFacade(), bank_id=1)
    qtbot.addWidget(dlg)

    html = dlg._format_preview(templates[0])
    assert "<table" in html
    assert "<sub>" in html
    assert "α; n-1" in html
    assert "1" in html and "4" in html


def test_problem_editor_dialog_use_template_applies_rows(monkeypatch, qtbot) -> None:
    monkeypatch.setattr(
        QuestionBankFacade,
        "get_bank_metadata",
        lambda self, bank_id: _bank_meta(),
    )
    monkeypatch.setattr(
        QuestionBankFacade,
        "list_problem_templates",
        lambda self, bank_id: [
            SimpleNamespace(template_id=101, name="Mẫu 1", row_count=2, total_score=3.0)
        ],
    )
    monkeypatch.setattr(
        QuestionBankFacade,
        "get_problem_template",
        lambda self, template_id: SimpleNamespace(
            template_id=template_id,
            bank_id=1,
            name="Mẫu 1",
            rows=[
                SimpleNamespace(marker="B1", content="Nội dung 1", score=1.0),
                SimpleNamespace(marker="", content="Nội dung 2", score=2.0),
            ],
        ),
    )
    monkeypatch.setattr(
        QMessageBox,
        "information",
        lambda *args, **kwargs: QMessageBox.StandardButton.Ok,
    )

    class _FakePicker:
        def __init__(self, templates, parent=None, **kwargs):
            self.selected_template_id = 101

        def exec(self):
            return ProblemEditorDialog.DialogCode.Accepted

    monkeypatch.setattr(
        "ui.dialogs.problem_editor_dialog.ProblemTemplatePickerDialog",
        _FakePicker,
    )

    dlg = ProblemEditorDialog(bank_id=1)
    qtbot.addWidget(dlg)
    dlg._use_problem_template()

    assert dlg._rubric_table.item(0, 0).text() == "B1"
    assert dlg._rubric_table.item(0, 1).text() == "Nội dung 1"
    assert dlg._rubric_table.item(1, 1).text() == "Nội dung 2"


def test_problem_editor_dialog_delete_key_removes_selected_row(monkeypatch, qtbot) -> None:
    monkeypatch.setattr(
        QuestionBankFacade,
        "get_bank_metadata",
        lambda self, bank_id: _bank_meta(),
    )

    dlg = ProblemEditorDialog(bank_id=1)
    qtbot.addWidget(dlg)
    dlg._rubric_table.item(0, 0).setText("a")
    dlg._rubric_table.item(0, 1).setText("Dòng 1")
    dlg._rubric_table.setCurrentCell(0, 1)
    dlg._add_content_row()
    dlg._rubric_table.item(1, 1).setText("Dòng 2")
    dlg._rubric_table.setCurrentCell(1, 1)
    dlg._rubric_table.setFocus()

    qtbot.keyClick(dlg._rubric_table, Qt.Key.Key_Delete)

    assert dlg._data_row_count() == 2
    assert dlg._rubric_table.item(0, 1).text() == "Dòng 1"


def test_problem_editor_dialog_ctrl_enter_adds_content_row(monkeypatch, qtbot) -> None:
    monkeypatch.setattr(
        QuestionBankFacade,
        "get_bank_metadata",
        lambda self, bank_id: _bank_meta(),
    )

    dlg = ProblemEditorDialog(bank_id=1)
    qtbot.addWidget(dlg)
    dlg._rubric_table.item(0, 0).setText("a")
    dlg._rubric_table.setCurrentCell(0, 1)
    dlg._rubric_table.setFocus()

    qtbot.keyClick(dlg._rubric_table, Qt.Key.Key_Return, Qt.KeyboardModifier.ControlModifier)

    assert dlg._data_row_count() == 3
    assert dlg._rubric_table.rowSpan(0, 0) == 2
    assert dlg._rubric_table.currentRow() == 1


def test_problem_editor_dialog_esc_cancels_cell_edit(monkeypatch, qtbot) -> None:
    monkeypatch.setattr(
        QuestionBankFacade,
        "get_bank_metadata",
        lambda self, bank_id: _bank_meta(),
    )

    dlg = ProblemEditorDialog(bank_id=1)
    qtbot.addWidget(dlg)
    dlg._rubric_table.item(0, 1).setText("Dòng chỉnh sửa")
    dlg._rubric_table.editItem(dlg._rubric_table.item(0, 1))

    editor = dlg._rubric_table.findChild(QLineEdit)
    assert editor is not None
    qtbot.keyClick(editor, Qt.Key.Key_Escape)

    assert dlg._rubric_table.state() != QAbstractItemView.State.EditingState


def test_problem_editor_dialog_context_menu_contains_rubric_actions(monkeypatch, qtbot) -> None:
    monkeypatch.setattr(
        QuestionBankFacade,
        "get_bank_metadata",
        lambda self, bank_id: _bank_meta(),
    )

    dlg = ProblemEditorDialog(bank_id=1)
    qtbot.addWidget(dlg)

    menu = dlg._build_rubric_context_menu()
    labels = [action.text() for action in menu.actions() if action.text()]

    assert labels == ["+ Thêm #", "+ Thêm hàng", "Xóa hàng", "Xóa #"]
