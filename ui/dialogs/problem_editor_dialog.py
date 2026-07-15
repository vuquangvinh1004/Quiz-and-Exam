"""Dialog for creating/editing problem-style essay questions with a rubric table."""
from __future__ import annotations

from PySide6.QtCore import QEvent, QPoint, Qt
from PySide6.QtGui import QAction, QPalette, QTextDocument
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QAbstractItemDelegate,
    QAbstractSpinBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QMenu,
    QStyledItemDelegate,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QTextBrowser,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QHeaderView,
)

from core.database.models import Question
from core.domain.services.question_service import ProblemRubricRow, QuestionEditData
from core.utils.constants import QuestionStatus, QuestionType
from core.utils.latex_rendering import render_inline_latex_html
from ui.facades.question_bank_facade import QuestionBankFacade
from ui.dialogs.problem_template_picker_dialog import ProblemTemplatePickerDialog

_LEVELS: tuple[str, ...] = ("Vận dụng", "Phân tích", "Đánh giá", "Sáng tạo")
_LEVEL_DEFAULT_SCORES: dict[str, float] = {
    "Vận dụng": 4.0,
    "Phân tích": 6.0,
    "Đánh giá": 8.0,
    "Sáng tạo": 10.0,
}
_WARNING_ICON = "&#9888;"
_CONTINUATION_ROLE = Qt.ItemDataRole.UserRole + 1
_LATEX_EXAMPLE = r"$t=\frac{\bar{x}-\mu_0}{s/\sqrt{n}}$"


class _RubricTextDelegate(QStyledItemDelegate):
    """Make table rows grow based on wrapped text content."""

    def __init__(self, on_add_row, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._on_add_row = on_add_row

    def sizeHint(self, option, index):  # noqa: N802
        hint = super().sizeHint(option, index)
        text = str(index.data() or "").strip()
        if not text:
            return hint
        width = max(option.rect.width(), 120)
        doc = QTextDocument()
        doc.setDefaultFont(option.font)
        doc.setPlainText(text)
        doc.setTextWidth(max(width - 12, 80))
        hint.setHeight(max(hint.height(), int(doc.size().height()) + 14))
        return hint

    def createEditor(self, parent, option, index):  # noqa: N802
        editor = super().createEditor(parent, option, index)
        if editor is not None:
            editor.installEventFilter(self)
        return editor

    def eventFilter(self, editor, event):  # noqa: N802
        if event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Escape:
                self.closeEditor.emit(editor, QAbstractItemDelegate.EndEditHint.RevertModelCache)
                return True
            if (
                event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
                and event.modifiers() & Qt.KeyboardModifier.ControlModifier
            ):
                self.commitData.emit(editor)
                self.closeEditor.emit(editor, QAbstractItemDelegate.EndEditHint.NoHint)
                self._on_add_row()
                return True
        return super().eventFilter(editor, event)


class _ScoreDelegate(QStyledItemDelegate):
    """Keep score cells centered and red, even when selected."""

    def initStyleOption(self, option, index):  # noqa: N802
        super().initStyleOption(option, index)
        option.displayAlignment = Qt.AlignmentFlag.AlignCenter
        option.palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.red)
        option.palette.setColor(QPalette.ColorGroup.Active, QPalette.ColorRole.Text, Qt.GlobalColor.red)
        option.palette.setColor(QPalette.ColorGroup.Inactive, QPalette.ColorRole.Text, Qt.GlobalColor.red)


def _render_template_preview_html(rows: list[ProblemRubricRow]) -> str:
    total = 0.0
    body_rows: list[str] = []
    for idx, row in enumerate(rows, start=1):
        score = float(row.score or 0.0)
        total += score
        marker = render_inline_latex_html(row.marker or "-") or "-"
        content = render_inline_latex_html(row.content or "")
        if not content:
            content = "<span style='color:#9ca3af;font-style:italic;'>(trống)</span>"
        body_rows.append(
            "<tr>"
            f"<td style='text-align:center;'>{idx}</td>"
            f"<td style='text-align:center;'>{marker}</td>"
            f"<td style='text-align:left;'>{content}</td>"
            f"<td style='text-align:center;color:#c0392b;font-weight:700;'>{ProblemEditorDialog._format_score(score)}</td>"
            "</tr>"
        )

    html_rows = "\n".join(body_rows) if body_rows else (
        "<tr><td colspan='4' style='text-align:center;color:#9ca3af;font-style:italic;'>"
        "Chưa có dữ liệu rubric."
        "</td></tr>"
    )
    return f"""
    <html>
    <head>
      <style>
        body {{
          font-family: 'Segoe UI', sans-serif;
          font-size: 11.5pt;
          color: #1f2937;
          margin: 0;
        }}
        .card {{
          border: 1px solid #dbe2ee;
          border-radius: 10px;
          padding: 12px;
          background: #ffffff;
        }}
        .title {{
          font-weight: 700;
          margin-bottom: 8px;
          color: #0f172a;
        }}
        .meta {{
          color: #6b7280;
          margin-bottom: 10px;
        }}
        table {{
          width: 100%;
          border-collapse: collapse;
        }}
        th, td {{
          border: 1px solid #dfe5ef;
          padding: 8px 10px;
          vertical-align: top;
        }}
        th {{
          background: #eef3f9;
          font-weight: 700;
          text-align: center;
        }}
        .total-row td {{
          font-weight: 700;
          background: #f8fafc;
        }}
        .total-score {{
          color: #c0392b;
        }}
        .math {{
          font-weight: 600;
          color: #111827;
        }}
      </style>
    </head>
    <body>
      <div class="card">
        <div class="title">Xem trước rubric mẫu</div>
        <div class="meta">Công thức trong nội dung sẽ được render trước khi lưu mẫu.</div>
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Mã</th>
              <th>Nội dung đáp án</th>
              <th>Điểm</th>
            </tr>
          </thead>
          <tbody>
            {''.join(body_rows) if body_rows else html_rows}
            <tr class="total-row">
              <td colspan="3" style="text-align:center;">TỔNG</td>
              <td class="total-score" style="text-align:center;">{ProblemEditorDialog._format_score(total)}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </body>
    </html>
    """


class _ProblemTemplateSaveDialog(QDialog):
    """Preview and name dialog used before saving a template."""

    def __init__(
        self,
        rows: list[ProblemRubricRow],
        *,
        default_name: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._rows = rows
        self._template_name = default_name.strip()
        self.setWindowTitle("Thêm MẪU")
        self.setMinimumSize(820, 560)
        self._build_ui(default_name)

    @property
    def template_name(self) -> str:
        return self._name_edit.text().strip()

    def _build_ui(self, default_name: str) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(10)

        name_row = QHBoxLayout()
        name_lbl = QLabel("Tên mẫu:")
        name_row.addWidget(name_lbl)
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("Nhập tên mẫu rubric...")
        self._name_edit.setText(default_name.strip())
        name_row.addWidget(self._name_edit, stretch=1)
        root.addLayout(name_row)

        self._preview_browser = QTextBrowser()
        self._preview_browser.setOpenExternalLinks(False)
        self._preview_browser.setHtml(_render_template_preview_html(self._rows))
        self._preview_browser.setStyleSheet(
            "QTextBrowser { background-color: #ffffff; border: 1px solid #d7ddea; }"
            "QTextBrowser viewport { background-color: #ffffff; }"
            "QTextBrowser .math { font-weight: 600; }"
        )
        root.addWidget(self._preview_browser, stretch=1)

        hint = QLabel("Xem trước giúp kiểm tra lại công thức và phân bố điểm trước khi lưu.")
        hint.setStyleSheet("color: #666;")
        hint.setWordWrap(True)
        root.addWidget(hint)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.button(QDialogButtonBox.StandardButton.Save).setText("Lưu mẫu")
        button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("Hủy")
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        root.addWidget(button_box)


class ProblemEditorDialog(QDialog):
    """Modal dialog specialized for problem-bank entries."""

    def __init__(
        self,
        bank_id: int,
        question: Question | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._bank_id = bank_id
        self._question = question
        self._facade = QuestionBankFacade()
        self._saved_id: int | None = None
        self._bank_metadata = self._facade.get_bank_metadata(bank_id)
        self._bank_clos = list(self._bank_metadata.course_learning_outcomes or []) if self._bank_metadata else []
        self._syncing_rubric = False
        self._problem_template_id: int | None = None
        self._problem_template_name: str = ""

        self.setWindowTitle("Thêm bài toán" if question is None else "Sửa bài toán")
        self.setMinimumSize(940, 680)
        self._build_ui()

        if question is not None:
            self._load_question(question)
        else:
            self._ensure_minimum_rubric_rows()
            self._refresh_rubric_summary()
            self._refresh_formula_preview()

    @property
    def saved_question_id(self) -> int | None:
        return self._saved_id

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 10)
        root.setSpacing(10)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        content_layout = QVBoxLayout(container)
        content_layout.setSpacing(10)
        scroll.setWidget(container)
        root.addWidget(scroll, stretch=1)

        def _build_basic_form(parent: QWidget) -> QFormLayout:
            basic_layout = QFormLayout(parent)
            basic_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)

            self._content_edit = QTextEdit()
            self._content_edit.setPlaceholderText("Nhập nội dung bài toán...")
            self._content_edit.setFixedHeight(110)
            self._content_edit.textChanged.connect(self._refresh_formula_preview)
            basic_layout.addRow("Nội dung *:", self._content_edit)

            self._code_edit = QLineEdit()
            self._code_edit.setPlaceholderText("Tự động nếu để trống")
            basic_layout.addRow("Mã bài toán:", self._code_edit)

            self._learning_outcome_combo = QComboBox()
            self._learning_outcome_combo.addItem("Không gắn CLO", userData="")
            for row in self._bank_clos:
                code = str(row.get("code", "")).strip()
                description = str(row.get("description", "")).strip()
                if not code:
                    continue
                self._learning_outcome_combo.addItem(code, userData=code)
                idx = self._learning_outcome_combo.count() - 1
                self._learning_outcome_combo.setItemData(idx, description, Qt.ItemDataRole.ToolTipRole)
            basic_layout.addRow("Chuẩn đầu ra:", self._learning_outcome_combo)

            self._category_edit = QLineEdit()
            basic_layout.addRow("Chương:", self._category_edit)

            self._difficulty_combo = QComboBox()
            for level in _LEVELS:
                self._difficulty_combo.addItem(level, userData=level)
            self._difficulty_combo.currentIndexChanged.connect(self._apply_default_score_for_level)
            basic_layout.addRow("Mức độ:", self._difficulty_combo)

            self._score_spin = QDoubleSpinBox()
            self._score_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
            self._score_spin.setRange(0.01, 100.0)
            self._score_spin.setSingleStep(0.5)
            self._score_spin.setValue(_LEVEL_DEFAULT_SCORES["Vận dụng"])
            self._score_spin.valueChanged.connect(self._refresh_rubric_summary)
            basic_layout.addRow("Điểm:", self._score_spin)

            self._status_combo = QComboBox()
            for status in QuestionStatus:
                self._status_combo.addItem(status.value.capitalize(), userData=status.value)
            self._status_combo.setCurrentIndex(self._status_combo.findData(QuestionStatus.ACTIVE.value))
            basic_layout.addRow("Trạng thái:", self._status_combo)

            self._tags_edit = QLineEdit()
            self._tags_edit.setPlaceholderText("tag1, tag2, tag3")
            basic_layout.addRow("Tags:", self._tags_edit)
            return basic_layout

        if self._question is not None:
            basic = QGroupBox("Thông tin cơ bản")
            basic_layout = QVBoxLayout(basic)
            basic_layout.setContentsMargins(8, 8, 8, 8)
            basic_layout.setSpacing(6)
            self._basic_info_toggle = QToolButton()
            self._basic_info_toggle.setCheckable(True)
            self._basic_info_toggle.setChecked(False)
            self._basic_info_toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            self._basic_info_toggle.setArrowType(Qt.ArrowType.RightArrow)
            self._basic_info_toggle.setText("Mở rộng")
            basic_layout.addWidget(self._basic_info_toggle)

            self._basic_info_content = QWidget()
            _build_basic_form(self._basic_info_content)
            self._basic_info_content.setVisible(False)
            basic_layout.addWidget(self._basic_info_content)
            self._basic_info_toggle.toggled.connect(self._toggle_basic_info_panel)
            content_layout.addWidget(basic)
        else:
            basic = QGroupBox("Thông tin cơ bản")
            _build_basic_form(basic)
            content_layout.addWidget(basic)

        question_preview_group = QGroupBox("Xem trước câu hỏi")
        question_preview_layout = QVBoxLayout(question_preview_group)
        self._question_preview_toggle = QToolButton()
        self._question_preview_toggle.setCheckable(True)
        self._question_preview_toggle.setChecked(True)
        self._question_preview_toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self._question_preview_toggle.setArrowType(Qt.ArrowType.DownArrow)
        self._question_preview_toggle.setText("Thu gọn")
        self._question_preview_toggle.toggled.connect(self._toggle_question_preview)
        question_preview_layout.addWidget(self._question_preview_toggle)

        self._question_preview_content = QWidget()
        question_preview_content_layout = QVBoxLayout(self._question_preview_content)
        question_preview_content_layout.setContentsMargins(0, 0, 0, 0)
        question_preview_content_layout.setSpacing(4)

        self._question_preview_browser = QTextBrowser()
        self._question_preview_browser.setOpenExternalLinks(False)
        self._question_preview_browser.setMinimumHeight(115)
        self._question_preview_browser.setStyleSheet(
            "QTextBrowser { background-color: #ffffff; border: 1px solid #d6dbe6; }"
            "QTextBrowser viewport { background-color: #ffffff; }"
            "QTextBrowser .math { font-weight: 600; }"
        )
        question_preview_content_layout.addWidget(self._question_preview_browser)
        question_preview_hint = QLabel("Hiển thị nhanh nội dung bài toán đang nhập.")
        question_preview_hint.setStyleSheet("color: #666;")
        question_preview_hint.setWordWrap(True)
        question_preview_content_layout.addWidget(question_preview_hint)
        question_preview_layout.addWidget(self._question_preview_content)
        content_layout.addWidget(question_preview_group)

        preview_group = QGroupBox("Chọn rubric và xem trước")
        preview_layout = QVBoxLayout(preview_group)
        self._formula_preview_browser = QTextBrowser()
        self._formula_preview_browser.setOpenExternalLinks(False)
        self._formula_preview_browser.setMinimumHeight(180)
        self._formula_preview_browser.setStyleSheet(
            "QTextBrowser { background-color: #ffffff; border: 1px solid #d6dbe6; }"
            "QTextBrowser viewport { background-color: #ffffff; }"
            "QTextBrowser .math { font-weight: 600; }"
        )
        preview_layout.addWidget(self._formula_preview_browser)
        preview_controls = QHBoxLayout()
        self._formula_preview_hint = QLabel(
            "Hiển thị nhanh rubric đang chọn và công thức hiển thị."
        )
        self._formula_preview_hint.setStyleSheet("color: #666;")
        self._formula_preview_hint.setWordWrap(True)
        preview_controls.addWidget(self._formula_preview_hint, stretch=1)

        self._copy_formula_btn = QPushButton("Copy công thức")
        self._copy_formula_btn.setToolTip(
            "Sao chép công thức ví dụ hoặc nội dung đang chọn.\n"
            f"Ví dụ: {_LATEX_EXAMPLE}"
        )
        self._copy_formula_btn.clicked.connect(self._copy_formula_snippet)
        preview_controls.addWidget(self._copy_formula_btn)
        preview_layout.addLayout(preview_controls)
        content_layout.addWidget(preview_group)

        rubric_group = QGroupBox("Đáp án chấp nhận")
        rubric_layout = QVBoxLayout(rubric_group)

        self._rubric_table = QTableWidget(0, 3)
        self._rubric_table.setHorizontalHeaderLabels(["#", "Nội dung đáp án", "Điểm"])
        self._rubric_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self._rubric_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._rubric_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self._rubric_table.setColumnWidth(0, 90)
        self._rubric_table.setColumnWidth(2, 110)
        self._rubric_table.horizontalHeader().setMinimumSectionSize(80)
        self._rubric_table.verticalHeader().setVisible(False)
        self._rubric_table.verticalHeader().setDefaultSectionSize(38)
        self._rubric_table.setMinimumHeight(360)
        self._rubric_table.setAlternatingRowColors(True)
        self._rubric_table.setWordWrap(True)
        self._rubric_table.setTextElideMode(Qt.TextElideMode.ElideNone)
        self._rubric_delegate = _RubricTextDelegate(self._add_content_row, self._rubric_table)
        self._rubric_table.setItemDelegate(self._rubric_delegate)
        self._rubric_table.setItemDelegateForColumn(2, _ScoreDelegate(self._rubric_table))
        self._rubric_table.setHorizontalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        self._rubric_table.setVerticalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        self._rubric_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._rubric_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._rubric_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._rubric_table.customContextMenuRequested.connect(self._show_rubric_context_menu)
        self._rubric_table.installEventFilter(self)
        self._rubric_table.itemChanged.connect(self._on_rubric_item_changed)
        self._rubric_table.itemSelectionChanged.connect(self._refresh_formula_preview)
        rubric_layout.addWidget(self._rubric_table)

        self._shortcut_hint_lbl = QLabel(
            "<span style='color:#666;'>Mẹo: <b>Ctrl+Enter</b> thêm hàng nhanh, "
            "<b>Delete</b> xóa dòng, <b>Esc</b> thoát ô đang sửa.</span>"
        )
        self._shortcut_hint_lbl.setTextFormat(Qt.TextFormat.RichText)
        self._shortcut_hint_lbl.setWordWrap(True)
        self._shortcut_hint_lbl.setToolTip("Ctrl+Enter thêm hàng, Delete xóa dòng, Esc hủy chỉnh sửa ô.")
        rubric_layout.addWidget(self._shortcut_hint_lbl)

        self._create_rubric_actions()

        control_layout = QHBoxLayout()
        self._add_marker_btn = QPushButton("+ Thêm #")
        self._add_marker_btn.clicked.connect(self._add_marker_row)
        control_layout.addWidget(self._add_marker_btn)

        self._add_row_btn = QPushButton("+ Thêm hàng")
        self._add_row_btn.clicked.connect(self._add_content_row)
        control_layout.addWidget(self._add_row_btn)

        self._delete_row_btn = QPushButton("Xóa hàng")
        self._delete_row_btn.clicked.connect(self._delete_content_row)
        control_layout.addWidget(self._delete_row_btn)

        self._delete_marker_btn = QPushButton("Xóa #")
        self._delete_marker_btn.clicked.connect(self._delete_marker_group)
        control_layout.addWidget(self._delete_marker_btn)

        self._save_template_btn = QPushButton("Thêm MẪU")
        self._save_template_btn.clicked.connect(self._save_problem_template)
        self._save_template_btn.setStyleSheet(
            "QPushButton { background-color: #c0392b; color: white; font-weight: 600; }"
            "QPushButton:hover { background-color: #a93226; }"
        )
        self._save_template_btn.setToolTip("Lưu cấu trúc rubric hiện tại thành một mẫu.")
        control_layout.addWidget(self._save_template_btn)

        self._load_template_btn = QPushButton("Dùng MẪU")
        self._load_template_btn.clicked.connect(self._use_problem_template)
        self._load_template_btn.setStyleSheet(
            "QPushButton { background-color: #8e44ad; color: white; font-weight: 600; }"
            "QPushButton:hover { background-color: #7d3c98; }"
        )
        self._load_template_btn.setToolTip("Chọn và áp dụng một mẫu rubric đã lưu cho ngân hàng này.")
        control_layout.addWidget(self._load_template_btn)
        control_layout.addStretch()

        self._rubric_warning_lbl = QLabel("")
        self._rubric_warning_lbl.setTextFormat(Qt.TextFormat.RichText)
        self._rubric_warning_lbl.setStyleSheet("color: #c0392b; font-weight: 600;")
        self._rubric_warning_lbl.hide()
        control_layout.addWidget(self._rubric_warning_lbl)
        rubric_layout.addLayout(control_layout)
        content_layout.addWidget(rubric_group)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.button(QDialogButtonBox.StandardButton.Save).setText("Lưu")
        button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("Hủy")
        button_box.accepted.connect(self._on_save)
        button_box.rejected.connect(self.reject)
        root.addWidget(button_box)

    def _add_marker_row(self) -> None:
        self._insert_rubric_row()
        self._refresh_rubric_summary()
        self._sync_rubric_action_states()

    def _add_content_row(self) -> None:
        anchor_row = self._selected_data_row()
        if anchor_row < 0:
            self._insert_rubric_row()
        else:
            insert_at = self._group_end_row(anchor_row) + 1
            self._insert_rubric_row(insert_at=insert_at, is_continuation=True)
            self._rubric_table.setCurrentCell(insert_at, 1)
        self._refresh_rubric_summary()
        self._sync_rubric_action_states()

    def _delete_content_row(self) -> None:
        row = self._selected_data_row()
        if row < 0:
            return
        if self._data_row_count() <= 1:
            self._clear_data_row(row)
            self._refresh_rubric_summary()
            return
        self._syncing_rubric = True
        try:
            self._rubric_table.removeRow(row)
            self._ensure_total_row()
            self._promote_group_head_if_needed(row)
            self._ensure_minimum_rubric_rows()
            self._normalize_group_markers()
            self._rebuild_marker_spans()
            self._resize_rubric_rows()
        finally:
            self._syncing_rubric = False
        self._refresh_rubric_summary()
        self._sync_rubric_action_states()

    def _delete_marker_group(self) -> None:
        row = self._selected_data_row()
        if row < 0:
            return
        group_start = self._group_start_row(row)
        group_end = self._group_end_row(group_start)
        span_size = group_end - group_start + 1
        if not self._confirm_delete_marker_group(span_size):
            return
        if self._data_row_count() <= span_size:
            for data_row in range(self._data_row_count()):
                self._clear_data_row(data_row)
            self._refresh_rubric_summary()
            return
        self._syncing_rubric = True
        try:
            for _ in range(span_size):
                self._rubric_table.removeRow(group_start)
            self._ensure_total_row()
            self._ensure_minimum_rubric_rows()
            self._normalize_group_markers()
            self._rebuild_marker_spans()
            self._resize_rubric_rows()
        finally:
            self._syncing_rubric = False
        self._refresh_rubric_summary()
        self._sync_rubric_action_states()

    def _save_problem_template(self) -> None:
        rows = self._collect_template_rows()
        if not rows:
            QMessageBox.information(self, "Chưa có dữ liệu", "Vui lòng nhập ít nhất một dòng để lưu làm mẫu.")
            return

        dlg = _ProblemTemplateSaveDialog(
            rows,
            default_name=self._code_edit.text().strip() or "Mẫu rubric",
            parent=self,
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        name = dlg.template_name
        if not name:
            QMessageBox.warning(self, "Lỗi lưu mẫu", "Tên mẫu không được để trống.")
            return

        try:
            summary = self._facade.save_problem_template(self._bank_id, name, rows)
        except ValueError as exc:
            QMessageBox.warning(self, "Lỗi lưu mẫu", str(exc))
            return
        except (RuntimeError, OSError) as exc:
            QMessageBox.critical(self, "Lỗi lưu mẫu", f"Không thể lưu mẫu:\n{exc}")
            return

        QMessageBox.information(
            self,
            "Đã lưu mẫu",
            f"Đã lưu mẫu '{summary.name}' với {summary.row_count} hàng.",
        )

    def _use_problem_template(self) -> None:
        try:
            templates = self._facade.list_problem_templates(self._bank_id)
        except (RuntimeError, OSError) as exc:
            QMessageBox.critical(self, "Lỗi nạp mẫu", f"Không thể tải danh sách mẫu:\n{exc}")
            return
        if not templates:
            QMessageBox.information(self, "Chưa có mẫu", "Ngân hàng này chưa có mẫu rubric nào.")
            return

        dlg = ProblemTemplatePickerDialog(
            templates,
            parent=self,
            facade=self._facade,
            bank_id=self._bank_id,
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        template_id = dlg.selected_template_id
        if template_id is None:
            return

        try:
            template = self._facade.get_problem_template(template_id)
        except (RuntimeError, OSError) as exc:
            QMessageBox.critical(self, "Lỗi nạp mẫu", f"Không thể nạp mẫu:\n{exc}")
            return

        if template is None:
            QMessageBox.warning(self, "Không tìm thấy", "Mẫu đã chọn không còn tồn tại.")
            return

        self._apply_problem_template(
            template.rows,
            template_id=template.template_id,
            template_name=template.name,
        )
        QMessageBox.information(self, "Đã áp dụng", f"Đã áp dụng mẫu '{template.name}'.")

    def _insert_rubric_row(
        self,
        *,
        insert_at: int | None = None,
        marker: str = "",
        content: str = "",
        score: float | None = None,
        is_continuation: bool = False,
    ) -> None:
        if insert_at is None:
            insert_at = self._data_row_count()
        self._syncing_rubric = True
        try:
            self._rubric_table.insertRow(insert_at)
            marker_item = QTableWidgetItem("" if is_continuation else marker)
            marker_item.setData(_CONTINUATION_ROLE, is_continuation)
            marker_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._rubric_table.setItem(insert_at, 0, marker_item)
            self._rubric_table.setItem(insert_at, 1, QTableWidgetItem(content))
            self._rubric_table.setItem(insert_at, 2, self._score_item(score))
            self._ensure_total_row()
            self._rebuild_marker_spans()
            self._resize_rubric_rows()
        finally:
            self._syncing_rubric = False

    def _ensure_minimum_rubric_rows(self) -> None:
        while self._data_row_count() < 2:
            self._insert_rubric_row()

    def _ensure_total_row(self) -> None:
        total_row = self._rubric_table.rowCount() - 1
        if total_row < 0 or not self._is_total_row(total_row):
            self._rubric_table.insertRow(self._rubric_table.rowCount())
            total_row = self._rubric_table.rowCount() - 1
        self._rubric_table.setSpan(total_row, 0, 1, 2)
        total_label = self._readonly_item("TỔNG", align_center=True)
        total_score = self._readonly_item("0", align_center=True)
        total_score.setForeground(Qt.GlobalColor.red)
        self._rubric_table.setItem(total_row, 0, total_label)
        self._rubric_table.setItem(total_row, 1, self._readonly_item(""))
        self._rubric_table.setItem(total_row, 2, total_score)

    def _rebuild_marker_spans(self) -> None:
        self._rubric_table.clearSpans()
        data_rows = self._data_row_count()
        row = 0
        while row < data_rows:
            group_end = self._group_end_row(row)
            span_size = group_end - row + 1
            if span_size > 1:
                self._rubric_table.setSpan(row, 0, span_size, 1)
            row = group_end + 1
        total_row = self._rubric_table.rowCount() - 1
        if total_row >= 0 and self._is_total_row(total_row):
            self._rubric_table.setSpan(total_row, 0, 1, 2)

    def _is_total_row(self, row: int) -> bool:
        item = self._rubric_table.item(row, 0)
        return item is not None and item.text() == "TỔNG"

    def _data_row_count(self) -> int:
        if self._rubric_table.rowCount() == 0:
            return 0
        return self._rubric_table.rowCount() - (1 if self._is_total_row(self._rubric_table.rowCount() - 1) else 0)

    def _on_rubric_item_changed(self, item: QTableWidgetItem) -> None:
        if self._syncing_rubric:
            return
        if self._is_total_row(item.row()):
            return
        if item.column() == 0:
            self._syncing_rubric = True
            try:
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            finally:
                self._syncing_rubric = False
        if item.column() == 2:
            text = item.text().strip()
            value = self._parse_score_text(text)
            self._syncing_rubric = True
            try:
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item.setForeground(Qt.GlobalColor.red)
                if value is not None and text:
                    item.setText(self._format_score(value))
            finally:
                self._syncing_rubric = False
        self._rebuild_marker_spans()
        self._normalize_group_markers()
        self._resize_rubric_rows()
        self._sync_rubric_action_states()
        self._refresh_rubric_summary()

    def _normalize_group_markers(self) -> None:
        self._syncing_rubric = True
        try:
            for row in range(self._data_row_count()):
                marker_item = self._rubric_table.item(row, 0)
                if marker_item is None:
                    continue
                if self._is_group_continuation(row):
                    marker_item.setData(_CONTINUATION_ROLE, True)
                    if marker_item.text():
                        marker_item.setText("")
                else:
                    marker_item.setData(_CONTINUATION_ROLE, False)
                marker_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        finally:
            self._syncing_rubric = False

    def _refresh_rubric_summary(self, *_args) -> None:
        total = self._rubric_total()
        self._ensure_total_row()
        self._rebuild_marker_spans()
        self._resize_rubric_rows()
        total_row = self._rubric_table.rowCount() - 1
        score_item = self._rubric_table.item(total_row, 2)
        if score_item is not None:
            score_item.setText(self._format_score(total))

        if total > self._score_spin.value():
            self._rubric_warning_lbl.setText(
                f"{_WARNING_ICON} Tổng điểm đáp án đang lớn hơn điểm của bài toán."
            )
            self._rubric_warning_lbl.show()
        else:
            self._rubric_warning_lbl.hide()
        self._refresh_formula_preview()

    def _rubric_total(self) -> float:
        total = 0.0
        for row in range(self._data_row_count()):
            item = self._rubric_table.item(row, 2)
            value = self._parse_score_text(item.text() if item is not None else "")
            if value is not None:
                total += value
        return total

    def _refresh_formula_preview(self) -> None:
        if not hasattr(self, "_formula_preview_browser"):
            return

        content = self._content_edit.toPlainText().strip()
        selected_row = self._selected_data_row()
        if selected_row < 0:
            for row in range(self._data_row_count()):
                if self._item_text(row, 1):
                    selected_row = row
                    break

        rubric_marker = self._effective_marker(selected_row) if selected_row >= 0 else ""
        rubric_content = self._item_text(selected_row, 1) if selected_row >= 0 else ""
        rubric_score = self._item_text(selected_row, 2) if selected_row >= 0 else ""

        question_html_parts = [
            "<html><head><style>",
            "body { font-family: 'Segoe UI', sans-serif; font-size: 12pt; color: #1f2937; }",
            ".block { margin-bottom: 12px; padding: 10px 12px; border: 1px solid #e3e8f3; border-radius: 8px; background: #fff; }",
            ".title { font-weight: 700; color: #0f172a; margin-bottom: 6px; }",
            ".content { margin-top: 8px; }",
            ".empty { color: #9ca3af; font-style: italic; }",
            ".math { font-weight: 600; color: #111827; }",
            "</style></head><body>",
            "<div class='block'>",
            "<div class='title'>Nội dung bài toán</div>",
        ]
        if content:
            question_html_parts.append(f"<div class='content'>{render_inline_latex_html(content)}</div>")
        else:
            question_html_parts.append("<div class='empty'>Chưa nhập nội dung bài toán.</div>")
        question_html_parts.append("</div></body></html>")
        self._question_preview_browser.setHtml("".join(question_html_parts))

        rubric_html_parts = [
            "<html><head><style>",
            "body { font-family: 'Segoe UI', sans-serif; font-size: 12pt; color: #1f2937; }",
            ".block { margin-bottom: 12px; padding: 10px 12px; border: 1px solid #e3e8f3; border-radius: 8px; background: #fff; }",
            ".title { font-weight: 700; color: #0f172a; margin-bottom: 6px; }",
            ".meta { color: #6b7280; font-size: 10.5pt; margin-bottom: 8px; line-height: 1.45; }",
            ".score { color: #c0392b; font-weight: 700; }",
            ".content { margin-top: 8px; }",
            ".empty { color: #9ca3af; font-style: italic; }",
            ".math { font-weight: 600; color: #111827; }",
            "</style></head><body>",
            "<div class='block'>",
            "<div class='title'>Rubric đang chọn</div>",
        ]
        if selected_row >= 0 and (rubric_marker or rubric_content or rubric_score):
            meta = []
            if rubric_marker:
                meta.append(f"Mã nhóm: {render_inline_latex_html(rubric_marker)}")
            if rubric_score:
                meta.append(f"<span class='score'>Điểm: {render_inline_latex_html(rubric_score)}</span>")
            if meta:
                rubric_html_parts.append(f"<div class='meta'>{' &nbsp;|&nbsp; '.join(meta)}</div>")
            if rubric_content:
                rubric_html_parts.append(f"<div class='content'>{render_inline_latex_html(rubric_content)}</div>")
            else:
                rubric_html_parts.append("<div class='empty'>Dòng rubric này chưa có nội dung.</div>")
        else:
            rubric_html_parts.append("<div class='empty'>Chọn một dòng rubric để xem công thức hiển thị.</div>")
        rubric_html_parts.append("</div></body></html>")
        self._formula_preview_browser.setHtml("".join(rubric_html_parts))

    def _toggle_question_preview(self, expanded: bool) -> None:
        self._question_preview_content.setVisible(expanded)
        self._question_preview_toggle.setArrowType(
            Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow
        )
        self._question_preview_toggle.setText("Thu gọn" if expanded else "Mở rộng")

    def _toggle_basic_info_panel(self, expanded: bool) -> None:
        if not hasattr(self, "_basic_info_content") or self._basic_info_content is None:
            return
        self._basic_info_content.setVisible(expanded)
        if hasattr(self, "_basic_info_toggle") and self._basic_info_toggle is not None:
            self._basic_info_toggle.setArrowType(
                Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow
            )
            self._basic_info_toggle.setText("Thu gọn" if expanded else "Mở rộng")

    def _copy_formula_snippet(self) -> None:
        snippet = self._content_edit.toPlainText().strip()
        selected_row = self._selected_data_row()
        if selected_row >= 0:
            selected_content = self._item_text(selected_row, 1)
            if selected_content:
                snippet = selected_content
        if not snippet:
            snippet = _LATEX_EXAMPLE
        clipboard = QApplication.clipboard()
        clipboard.setText(snippet)
        self._formula_preview_hint.setText("Đã copy công thức vào clipboard.")

    def _load_question(self, question: Question) -> None:
        self._problem_template_id = question.get_problem_template_id()
        self._problem_template_name = question.get_problem_template_name()
        self._content_edit.setPlainText(question.content or "")
        self._code_edit.setText(question.question_code or "")
        clo_idx = self._learning_outcome_combo.findData(question.learning_outcome_code or "")
        if clo_idx >= 0:
            self._learning_outcome_combo.setCurrentIndex(clo_idx)
        self._category_edit.setText(question.category or "")

        difficulty = str(question.difficulty or "").strip()
        diff_idx = self._difficulty_combo.findData(difficulty)
        if diff_idx < 0:
            diff_idx = self._difficulty_combo.findData("Phân tích")
        if diff_idx >= 0:
            self._difficulty_combo.setCurrentIndex(diff_idx)
        self._score_spin.setValue(question.point_value or _LEVEL_DEFAULT_SCORES["Vận dụng"])

        status_val = "active" if question.is_active else "inactive"
        status_idx = self._status_combo.findData(status_val)
        if status_idx >= 0:
            self._status_combo.setCurrentIndex(status_idx)
        self._tags_edit.setText(question.tags or "")

        self._syncing_rubric = True
        try:
            self._rubric_table.setRowCount(0)
        finally:
            self._syncing_rubric = False

        rubric = []
        if question.is_problem_question():
            rubric = question.get_problem_rubric()
        elif question.accepted_answers:
            rubric = [
                {"marker": "", "content": answer, "score": 0.0}
                for answer in question.get_accepted_answers()
            ]

        for row in rubric:
            self._insert_rubric_row(
                marker=str(row.get("marker", "")),
                content=str(row.get("content", "")),
                score=float(row.get("score", 0.0) or 0.0),
            )
        self._ensure_minimum_rubric_rows()
        self._normalize_loaded_groups()
        self._refresh_rubric_summary()
        self._refresh_formula_preview()
        self._sync_rubric_action_states()

    def _apply_problem_template(
        self,
        rows: list[ProblemRubricRow],
        *,
        template_id: int | None = None,
        template_name: str = "",
    ) -> None:
        self._problem_template_id = template_id
        self._problem_template_name = template_name.strip()
        self._syncing_rubric = True
        try:
            self._rubric_table.setRowCount(0)
        finally:
            self._syncing_rubric = False

        for row in rows:
            self._insert_rubric_row(
                marker=row.marker,
                content=row.content,
                score=row.score,
            )

        self._ensure_minimum_rubric_rows()
        self._normalize_loaded_groups()
        self._refresh_rubric_summary()
        self._refresh_formula_preview()
        self._sync_rubric_action_states()

    def _on_save(self) -> None:
        try:
            rubric_rows = self._collect_rubric_rows()
        except ValueError as exc:
            QMessageBox.warning(self, "Lỗi nhập liệu", str(exc))
            return

        data = QuestionEditData(
            bank_id=self._bank_id,
            question_type=QuestionType.ESSAY,
            content=self._content_edit.toPlainText(),
            difficulty=str(self._difficulty_combo.currentData() or "Vận dụng"),
            score=self._score_spin.value(),
            learning_outcome_code=str(self._learning_outcome_combo.currentData() or ""),
            category=self._category_edit.text(),
            tags=self._tags_edit.text(),
            status=self._status_combo.currentData() or QuestionStatus.ACTIVE.value,
            question_code=self._code_edit.text(),
            accepted_answers=[row.content for row in rubric_rows if row.content],
            editor_variant="problem",
            problem_rubric=rubric_rows,
            problem_template_id=self._problem_template_id,
            problem_template_name=self._problem_template_name,
        )

        try:
            if self._question is None:
                question = self._facade.create_question(data)
            else:
                question = self._facade.update_question(self._question.id, data)
            self._saved_id = question.id
            self.accept()
        except ValueError as exc:
            QMessageBox.warning(self, "Lỗi nhập liệu", str(exc))
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi lưu", f"Không thể lưu bài toán:\n{exc}")

    def _collect_rubric_rows(self) -> list[ProblemRubricRow]:
        rows: list[ProblemRubricRow] = []
        for row in range(self._data_row_count()):
            marker = self._effective_marker(row)
            content = self._item_text(row, 1)
            score_text = self._item_text(row, 2)
            if not marker and not content and not score_text:
                continue
            if not content:
                raise ValueError("Mỗi dòng đáp án của bài toán cần có nội dung đáp án.")
            score = self._parse_score_text(score_text)
            if score is None:
                raise ValueError("Điểm trong bảng đáp án phải là số hợp lệ.")
            rows.append(ProblemRubricRow(marker=marker, content=content, score=score))
        return rows

    def _collect_template_rows(self) -> list[ProblemRubricRow]:
        rows: list[ProblemRubricRow] = []
        for row in range(self._data_row_count()):
            marker = self._effective_marker(row)
            content = self._item_text(row, 1)
            score_text = self._item_text(row, 2)
            if not content:
                continue
            score = self._parse_score_text(score_text)
            if score is None:
                raise ValueError("Điểm trong bảng đáp án phải là số hợp lệ.")
            rows.append(ProblemRubricRow(marker=marker, content=content, score=score))
        return rows

    def _apply_default_score_for_level(self, _index: int) -> None:
        level = str(self._difficulty_combo.currentData() or "")
        default_score = _LEVEL_DEFAULT_SCORES.get(level)
        if default_score is None:
            return
        self._score_spin.setValue(default_score)

    def _item_text(self, row: int, column: int) -> str:
        item = self._rubric_table.item(row, column)
        return item.text().strip() if item is not None else ""

    def _selected_data_row(self) -> int:
        row = self._rubric_table.currentRow()
        if 0 <= row < self._data_row_count():
            return row
        return self._data_row_count() - 1 if self._data_row_count() > 0 else -1

    def _create_rubric_actions(self) -> None:
        self._add_marker_action = QAction("+ Thêm #", self)
        self._add_marker_action.triggered.connect(self._add_marker_row)
        self._add_row_action = QAction("+ Thêm hàng", self)
        self._add_row_action.triggered.connect(self._add_content_row)
        self._delete_row_action = QAction("Xóa hàng", self)
        self._delete_row_action.triggered.connect(self._delete_content_row)
        self._delete_group_action = QAction("Xóa #", self)
        self._delete_group_action.triggered.connect(self._delete_marker_group)
        self._sync_rubric_action_states()

    def _build_rubric_context_menu(self) -> QMenu:
        menu = QMenu(self)
        menu.addAction(self._add_marker_action)
        menu.addAction(self._add_row_action)
        menu.addSeparator()
        menu.addAction(self._delete_row_action)
        menu.addAction(self._delete_group_action)
        return menu

    def _show_rubric_context_menu(self, pos: QPoint) -> None:
        row = self._rubric_table.rowAt(pos.y())
        col = self._rubric_table.columnAt(pos.x())
        if 0 <= row < self._data_row_count() and col >= 0:
            self._rubric_table.setCurrentCell(row, max(col, 0))
        self._sync_rubric_action_states()
        menu = self._build_rubric_context_menu()
        menu.exec(self._rubric_table.viewport().mapToGlobal(pos))

    def _sync_rubric_action_states(self) -> None:
        has_selection = self._selected_data_row() >= 0
        for action in (
            getattr(self, "_delete_row_action", None),
            getattr(self, "_delete_group_action", None),
        ):
            if action is not None:
                action.setEnabled(has_selection)

    def _confirm_delete_marker_group(self, span_size: int) -> bool:
        answer = QMessageBox.question(
            self,
            "Xác nhận xóa #",
            f"Xóa nhóm rubric đang chọn gồm {span_size} hàng nội dung?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes

    def eventFilter(self, watched, event):  # noqa: N802
        if watched is self._rubric_table and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Delete:
                self._delete_content_row()
                event.accept()
                return True
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                self._add_content_row()
                event.accept()
                return True
        return super().eventFilter(watched, event)

    def _group_start_row(self, row: int) -> int:
        current = min(max(row, 0), max(self._data_row_count() - 1, 0))
        while current > 0 and self._is_group_continuation(current):
            current -= 1
        return current

    def _group_end_row(self, row: int) -> int:
        data_rows = self._data_row_count()
        current = row
        while current + 1 < data_rows and self._is_group_continuation(current + 1):
            current += 1
        return current

    def _is_group_continuation(self, row: int) -> bool:
        if row <= 0 or row >= self._data_row_count():
            return False
        marker_item = self._rubric_table.item(row, 0)
        return bool(marker_item and marker_item.data(_CONTINUATION_ROLE))

    def _effective_marker(self, row: int) -> str:
        current = row
        while current >= 0:
            marker = self._item_text(current, 0)
            if marker:
                return marker
            current -= 1
        return ""

    def _promote_group_head_if_needed(self, deleted_row: int) -> None:
        if deleted_row >= self._data_row_count():
            return
        marker_item = self._rubric_table.item(deleted_row, 0)
        if marker_item is None:
            return
        if marker_item.data(_CONTINUATION_ROLE):
            marker_item.setData(_CONTINUATION_ROLE, False)
            marker_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

    def _clear_data_row(self, row: int) -> None:
        self._syncing_rubric = True
        try:
            marker_item = self._rubric_table.item(row, 0)
            if marker_item is not None:
                marker_item.setData(_CONTINUATION_ROLE, False)
                marker_item.setText("")
            content_item = self._rubric_table.item(row, 1)
            if content_item is not None:
                content_item.setText("")
            score_item = self._rubric_table.item(row, 2)
            if score_item is not None:
                score_item.setText("")
        finally:
            self._syncing_rubric = False
        self._normalize_group_markers()
        self._rebuild_marker_spans()
        self._resize_rubric_rows()

    def _resize_rubric_rows(self) -> None:
        self._syncing_rubric = True
        try:
            self._rubric_table.resizeRowsToContents()
            for row in range(self._data_row_count()):
                height = max(self._rubric_table.rowHeight(row), 38)
                self._rubric_table.setRowHeight(row, height)
            total_row = self._rubric_table.rowCount() - 1
            if total_row >= 0 and self._is_total_row(total_row):
                self._rubric_table.setRowHeight(total_row, 38)
        finally:
            self._syncing_rubric = False

    def _normalize_loaded_groups(self) -> None:
        previous_marker = None
        self._syncing_rubric = True
        try:
            for row in range(self._data_row_count()):
                marker_item = self._rubric_table.item(row, 0)
                if marker_item is None:
                    continue
                marker = marker_item.text().strip()
                if marker and marker == previous_marker:
                    marker_item.setData(_CONTINUATION_ROLE, True)
                    marker_item.setText("")
                elif marker:
                    marker_item.setData(_CONTINUATION_ROLE, False)
                    previous_marker = marker
                else:
                    marker_item.setData(_CONTINUATION_ROLE, False)
                marker_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        finally:
            self._syncing_rubric = False

    @staticmethod
    def _parse_score_text(text: str) -> float | None:
        raw = text.strip().replace(",", ".")
        if not raw:
            return 0.0
        try:
            return float(raw)
        except ValueError:
            return None

    @staticmethod
    def _format_score(value: float) -> str:
        if abs(value - round(value)) < 1e-9:
            return str(int(round(value)))
        return f"{value:.3f}".rstrip("0").rstrip(".")

    @staticmethod
    def _readonly_item(text: str, *, align_center: bool = False) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        if align_center:
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        return item

    @staticmethod
    def _score_item(value: float | None) -> QTableWidgetItem:
        text = "" if value is None or abs(value) < 1e-9 else ProblemEditorDialog._format_score(value)
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item.setForeground(Qt.GlobalColor.red)
        return item


__all__ = ["ProblemEditorDialog"]
