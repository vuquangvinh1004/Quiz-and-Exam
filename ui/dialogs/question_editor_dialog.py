"""Question Editor Dialog – create or edit a single question.

Supports MC, MA, TF, BLANK and SA with a dynamic form that switches
sections based on the selected type.

Design rules (ARCHITECTURE §2):
  - No business logic here; validation delegated to QuestionService.
  - UI only builds/submits QuestionEditData DTOs.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QCheckBox,
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
    QScrollArea,
    QTextBrowser,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from core.database.models import Question
from core.domain.services.question_service import QuestionEditData
from core.utils.constants import (
    BLANK_PLACEHOLDER,
    VALID_OPTION_LABELS,
    QuestionStatus,
    QuestionType,
)
from core.utils.latex_rendering import render_inline_latex_html
from ui.facades.question_bank_facade import QuestionBankFacade
from ui.styles import apply_checkbox_style

_LEVELS_BY_TYPE: dict[QuestionType, tuple[str, ...]] = {
    QuestionType.TRUE_FALSE: ("Nhớ", "Hiểu"),
    QuestionType.MULTIPLE_CHOICE: ("Nhớ", "Hiểu", "Vận dụng"),
    QuestionType.MULTIPLE_ANSWER: ("Nhớ", "Hiểu", "Vận dụng", "Phân tích"),
    QuestionType.BLANK: ("Nhớ", "Hiểu", "Vận dụng", "Phân tích", "Đánh giá", "Sáng tạo"),
    QuestionType.SHORT_ANSWER: ("Vận dụng", "Phân tích", "Đánh giá"),
}
_DEFAULT_LEVEL_BY_TYPE: dict[QuestionType, str] = {
    QuestionType.TRUE_FALSE: "Nhớ",
    QuestionType.MULTIPLE_CHOICE: "Nhớ",
    QuestionType.MULTIPLE_ANSWER: "Nhớ",
    QuestionType.BLANK: "Nhớ",
    QuestionType.SHORT_ANSWER: "Vận dụng",
}
_LEVELS_ALL: tuple[str, ...] = (
    "Nhớ",
    "Hiểu",
    "Vận dụng",
    "Phân tích",
    "Đánh giá",
    "Sáng tạo",
)
_LEVEL_DEFAULT_SCORES: dict[str, float] = {
    "Nhớ": 1.0,
    "Hiểu": 2.0,
    "Vận dụng": 4.0,
    "Phân tích": 6.0,
    "Đánh giá": 8.0,
    "Sáng tạo": 10.0,
}
_LEGACY_DIFFICULTY_TO_LEVEL: dict[str, str] = {
    "easy": "Nhớ",
    "medium": "Hiểu",
    "hard": "Vận dụng",
}
_TYPE_LABELS = {
    QuestionType.MULTIPLE_CHOICE: "Trắc nghiệm 1 đáp án",
    QuestionType.MULTIPLE_ANSWER: "Trắc nghiệm nhiều đáp án",
    QuestionType.TRUE_FALSE: "Đúng/Sai",
    QuestionType.BLANK: "Điền vào chỗ trống",
    QuestionType.SHORT_ANSWER: "Trả lời ngắn",
}
_TYPE_FROM_INDEX = [
    QuestionType.MULTIPLE_CHOICE,
    QuestionType.MULTIPLE_ANSWER,
    QuestionType.TRUE_FALSE,
    QuestionType.BLANK,
    QuestionType.SHORT_ANSWER,
]


class QuestionEditorDialog(QDialog):
    """Modal dialog to create or edit a single question."""

    def __init__(
        self,
        bank_id: int,
        question: Question | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._bank_id = bank_id
        self._question = question          # None → create mode
        self._facade = QuestionBankFacade()
        self._saved_id: int | None = None
        self._bank_metadata = self._facade.get_bank_metadata(bank_id)
        self._bank_clos = list(self._bank_metadata.course_learning_outcomes or []) if self._bank_metadata else []
        self._syncing_score = False
        self._syncing_level = False

        title = "Thêm câu hỏi" if question is None else "Sửa câu hỏi"
        self.setWindowTitle(title)
        self.setMinimumSize(680, 560)
        self._build_ui()

        if question:
            self._load_question(question)

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    @property
    def saved_question_id(self) -> int | None:
        """Returns the id of the saved question after dialog.exec() → Accepted."""
        return self._saved_id

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 10)
        root.setSpacing(10)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        form_layout = QVBoxLayout(container)
        form_layout.setSpacing(10)
        scroll.setWidget(container)
        root.addWidget(scroll, stretch=1)

        # ── Basic info ──────────────────────────────────────────────
        def _build_basic_form(parent: QWidget) -> QFormLayout:
            fl = QFormLayout(parent)
            fl.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)

            self._type_combo = QComboBox()
            for qt in _TYPE_FROM_INDEX:
                self._type_combo.addItem(_TYPE_LABELS[qt], userData=qt)
            self._type_combo.currentIndexChanged.connect(self._on_type_changed)
            fl.addRow("Loại câu hỏi *:", self._type_combo)

            self._content_edit = QTextEdit()
            self._content_edit.setPlaceholderText(
                "Nhập nội dung câu hỏi…\n"
                f"Với loại Điền vào chỗ trống, dùng {BLANK_PLACEHOLDER} để đánh dấu chỗ trống."
            )
            self._content_edit.setFixedHeight(90)
            self._content_edit.textChanged.connect(self._refresh_formula_preview)
            fl.addRow("Nội dung *:", self._content_edit)

            self._code_edit = QLineEdit()
            self._code_edit.setPlaceholderText("Tự động nếu để trống")
            fl.addRow("Mã câu hỏi:", self._code_edit)

            self._learning_outcome_combo = QComboBox()
            self._learning_outcome_combo.addItem("Không gắn CLO", userData="")
            for row in self._bank_clos:
                code = str(row.get("code", "")).strip()
                description = str(row.get("description", "")).strip()
                if not code:
                    continue
                self._learning_outcome_combo.addItem(code, userData=code)
                idx = self._learning_outcome_combo.count() - 1
                self._learning_outcome_combo.setItemData(
                    idx,
                    description,
                    Qt.ItemDataRole.ToolTipRole,
                )
            fl.addRow("Chuẩn đầu ra:", self._learning_outcome_combo)

            self._category_edit = QLineEdit()
            fl.addRow("Chương:", self._category_edit)

            self._difficulty_combo = QComboBox()
            self._difficulty_combo.currentIndexChanged.connect(self._apply_default_score_for_level)
            self._difficulty_combo.currentIndexChanged.connect(self._refresh_formula_preview)
            fl.addRow("Mức độ:", self._difficulty_combo)

            self._score_spin = QDoubleSpinBox()
            self._score_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
            self._score_spin.setRange(0.01, 100.0)
            self._score_spin.setSingleStep(0.5)
            self._score_spin.setValue(_LEVEL_DEFAULT_SCORES["Nhớ"])
            self._score_spin.valueChanged.connect(self._refresh_formula_preview)
            fl.addRow("Điểm:", self._score_spin)

            self._status_combo = QComboBox()
            for s in QuestionStatus:
                self._status_combo.addItem(s.value.capitalize(), userData=s.value)
            fl.addRow("Trạng thái:", self._status_combo)

            self._tags_edit = QLineEdit()
            self._tags_edit.setPlaceholderText("tag1, tag2, tag3")
            fl.addRow("Tags:", self._tags_edit)
            return fl

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
            form_layout.addWidget(basic)
        else:
            basic = QGroupBox("Thông tin cơ bản")
            _build_basic_form(basic)
            form_layout.addWidget(basic)

        # ── Options section (MC / MA) ────────────────────────────────
        self._options_group = QGroupBox("Các lựa chọn")
        opt_vl = QVBoxLayout(self._options_group)

        self._option_rows: list[tuple[QLabel, QLineEdit, QCheckBox]] = []
        for label in VALID_OPTION_LABELS:
            row_hl = QHBoxLayout()
            lbl = QLabel(f"{label}.")
            lbl.setFixedWidth(20)
            edit = QLineEdit()
            edit.setPlaceholderText(f"Lựa chọn {label}…")
            edit.textChanged.connect(self._refresh_formula_preview)
            cb = QCheckBox("Đúng")
            apply_checkbox_style(cb)
            cb.setFixedWidth(60)
            cb.stateChanged.connect(self._refresh_formula_preview)
            row_hl.addWidget(lbl)
            row_hl.addWidget(edit, stretch=1)
            row_hl.addWidget(cb)
            opt_vl.addLayout(row_hl)
            self._option_rows.append((lbl, edit, cb))

        mc_note = QLabel(
            "<i>Trắc nghiệm 1 đáp án: chọn đúng 1 ô 'Đúng'. "
            "Trắc nghiệm nhiều đáp án: chọn ít nhất 2 ô 'Đúng'. "
            "Đúng/Sai: chỉ dùng 2 lựa chọn Đúng/Sai.</i>"
        )
        mc_note.setTextFormat(Qt.TextFormat.RichText)
        mc_note.setWordWrap(True)
        opt_vl.addWidget(mc_note)
        form_layout.addWidget(self._options_group)

        # ── Accepted answers section (BLANK / SA) ───────────────────
        self._answers_group = QGroupBox("Đáp án chấp nhận (phân tách bằng ||)")
        ans_fl = QFormLayout(self._answers_group)

        self._answers_edit = QLineEdit()
        self._answers_edit.setPlaceholderText("Đáp án 1||Đáp án 2||…")
        self._answers_edit.textChanged.connect(self._refresh_formula_preview)
        ans_fl.addRow("Đáp án (*):", self._answers_edit)

        self._case_sensitive_cb = QCheckBox("Phân biệt hoa thường")
        apply_checkbox_style(self._case_sensitive_cb)
        self._case_sensitive_cb.stateChanged.connect(self._refresh_formula_preview)
        ans_fl.addRow("", self._case_sensitive_cb)

        self._trim_whitespace_cb = QCheckBox("Bỏ khoảng trắng đầu/cuối")
        apply_checkbox_style(self._trim_whitespace_cb)
        self._trim_whitespace_cb.setChecked(True)
        self._trim_whitespace_cb.stateChanged.connect(self._refresh_formula_preview)
        ans_fl.addRow("", self._trim_whitespace_cb)

        blank_hint = QLabel(
            f"<i>Điền vào chỗ trống: câu hỏi phải chứa ít nhất một <b>{BLANK_PLACEHOLDER}</b> "
            f"làm chỗ trống (có thể dùng nhiều {BLANK_PLACEHOLDER} cho nhiều chỗ điền).</i>"
        )
        blank_hint.setTextFormat(Qt.TextFormat.RichText)
        blank_hint.setWordWrap(True)
        ans_fl.addRow(blank_hint)
        form_layout.addWidget(self._answers_group)

        # ── Hint / Explanation ───────────────────────────────────────
        aux = QGroupBox("Gợi ý và giải thích")
        aux_fl = QFormLayout(aux)
        self._hint_edit = QLineEdit()
        self._hint_edit.setPlaceholderText("Hiển thị trong chế độ Luyện tập / Ôn tập")
        self._hint_edit.textChanged.connect(self._refresh_formula_preview)
        aux_fl.addRow("Gợi ý:", self._hint_edit)
        self._explanation_edit = QTextEdit()
        self._explanation_edit.setPlaceholderText("Giải thích sau khi kết thúc bài…")
        self._explanation_edit.setFixedHeight(70)
        self._explanation_edit.textChanged.connect(self._refresh_formula_preview)
        aux_fl.addRow("Giải thích:", self._explanation_edit)
        form_layout.addWidget(aux)

        self._formula_preview_group = QGroupBox("Xem trước câu hỏi")
        preview_layout = QVBoxLayout(self._formula_preview_group)
        self._formula_preview_toggle = QToolButton()
        self._formula_preview_toggle.setCheckable(True)
        self._formula_preview_toggle.setChecked(True)
        self._formula_preview_toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self._formula_preview_toggle.setArrowType(Qt.ArrowType.DownArrow)
        self._formula_preview_toggle.setText("Thu gọn")
        self._formula_preview_toggle.toggled.connect(self._toggle_formula_preview)
        preview_layout.addWidget(self._formula_preview_toggle)

        self._formula_preview_content = QWidget()
        preview_content_layout = QVBoxLayout(self._formula_preview_content)
        preview_content_layout.setContentsMargins(0, 0, 0, 0)
        preview_content_layout.setSpacing(6)

        self._formula_preview_browser = QTextBrowser()
        self._formula_preview_browser.setOpenExternalLinks(False)
        self._formula_preview_browser.setMinimumHeight(280)
        self._formula_preview_browser.setStyleSheet(
            "QTextBrowser { background-color: #ffffff; border: 1px solid #d6dbe6; }"
            "QTextBrowser viewport { background-color: #ffffff; }"
            "QTextBrowser .math { font-weight: 600; }"
        )
        preview_content_layout.addWidget(self._formula_preview_browser)
        self._formula_preview_hint = QLabel(
            "Xem nhanh nội dung và công thức đang nhập theo định dạng render."
        )
        self._formula_preview_hint.setStyleSheet("color: #666;")
        self._formula_preview_hint.setWordWrap(True)
        preview_content_layout.addWidget(self._formula_preview_hint)
        preview_layout.addWidget(self._formula_preview_content)
        form_layout.addWidget(self._formula_preview_group)

        # ── Buttons ──────────────────────────────────────────────────
        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.button(QDialogButtonBox.StandardButton.Save).setText("Lưu")
        btn_box.button(QDialogButtonBox.StandardButton.Cancel).setText("Hủy")
        btn_box.accepted.connect(self._on_save)
        btn_box.rejected.connect(self.reject)
        root.addWidget(btn_box)

        # Initial visibility
        self._on_type_changed(0)
        self._refresh_formula_preview()

    # ------------------------------------------------------------------
    # Dynamic type switching
    # ------------------------------------------------------------------

    def _on_type_changed(self, _index: int) -> None:
        qt = self._type_combo.currentData()
        is_mc_ma = qt in (
            QuestionType.MULTIPLE_CHOICE,
            QuestionType.MULTIPLE_ANSWER,
            QuestionType.TRUE_FALSE,
        )
        is_blank_sa = qt in (
            QuestionType.BLANK,
            QuestionType.SHORT_ANSWER,
        )
        self._options_group.setVisible(is_mc_ma)
        self._answers_group.setVisible(is_blank_sa)
        self._sync_option_rows(qt)
        self._populate_level_options(qt, preferred=self._difficulty_combo.currentData())
        self._refresh_formula_preview()

    # ------------------------------------------------------------------
    # Load existing question
    # ------------------------------------------------------------------

    def _load_question(self, q: Question) -> None:
        # Type
        try:
            qt = QuestionType(q.question_type)
            idx = _TYPE_FROM_INDEX.index(qt)
            self._type_combo.setCurrentIndex(idx)
        except (ValueError, IndexError):
            pass

        self._content_edit.setPlainText(q.content or "")
        self._code_edit.setText(q.question_code or "")
        clo_idx = self._learning_outcome_combo.findData(q.learning_outcome_code or "")
        if clo_idx >= 0:
            self._learning_outcome_combo.setCurrentIndex(clo_idx)
        self._category_edit.setText(q.category or "")
        self._hint_edit.setText(q.hint or "")
        self._explanation_edit.setPlainText(q.explanation or "")
        self._case_sensitive_cb.setChecked(bool(q.case_sensitive))
        self._trim_whitespace_cb.setChecked(True if q.trim_whitespace is None else bool(q.trim_whitespace))

        diff_value = self._normalize_level_value(q.difficulty)
        diff_idx = self._difficulty_combo.findData(diff_value)
        if diff_idx >= 0:
            self._difficulty_combo.setCurrentIndex(diff_idx)
        self._score_spin.setValue(q.point_value or 1.0)

        status_val = "active" if q.is_active else "inactive"
        st_idx = self._status_combo.findData(status_val)
        if st_idx >= 0:
            self._status_combo.setCurrentIndex(st_idx)

        self._tags_edit.setText(q.tags or "")

        # Options
        for _, edit, cb in self._option_rows:
            edit.clear()
            cb.setChecked(False)
        for opt in q.options:
            try:
                row_idx = list(VALID_OPTION_LABELS).index(opt.option_key.upper())
                _, edit, cb = self._option_rows[row_idx]
                edit.setText(opt.option_text)
                cb.setChecked(opt.is_correct)
            except (ValueError, IndexError):
                pass

        # Accepted answers
        if q.accepted_answers:
            try:
                answers = q.get_accepted_answers()
                self._answers_edit.setText("||".join(answers))
            except Exception:
                self._answers_edit.setText(q.accepted_answers)

        self._refresh_formula_preview()

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def _on_save(self) -> None:
        qt: QuestionType = self._type_combo.currentData()

        # Build options list for option-based types
        options: list[tuple[str, str, bool]] = []
        for label, (_, edit, cb) in zip(
            VALID_OPTION_LABELS,
            self._option_rows,
            strict=False,
        ):
            options.append((label, edit.text(), cb.isChecked()))

        # Build accepted answers for BLANK/SA
        raw_answers = self._answers_edit.text()
        accepted = [
            a.strip()
            for a in raw_answers.split("||")
            if a.strip()
        ]

        data = QuestionEditData(
            bank_id=self._bank_id,
            question_type=qt,
            content=self._content_edit.toPlainText(),
            difficulty=self._difficulty_combo.currentData() or "Nhớ",
            score=self._score_spin.value(),
            hint=self._hint_edit.text(),
            explanation=self._explanation_edit.toPlainText(),
            learning_outcome_code=str(self._learning_outcome_combo.currentData() or ""),
            category=self._category_edit.text(),
            tags=self._tags_edit.text(),
            status=self._status_combo.currentData() or "active",
            case_sensitive=self._case_sensitive_cb.isChecked(),
            trim_whitespace=self._trim_whitespace_cb.isChecked(),
            question_code=self._code_edit.text(),
            options=options,
            accepted_answers=accepted,
        )

        try:
            if self._question is None:
                q = self._facade.create_question(data)
            else:
                q = self._facade.update_question(self._question.id, data)
            self._saved_id = q.id
            self.accept()
        except ValueError as exc:
            QMessageBox.warning(self, "Lỗi nhập liệu", str(exc))
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi lưu", f"Không thể lưu câu hỏi:\n{exc}")

    def _apply_default_score_for_level(self, _index: int) -> None:
        level = str(self._difficulty_combo.currentData() or "")
        if level not in _LEVEL_DEFAULT_SCORES:
            return
        self._syncing_score = True
        try:
            self._score_spin.setValue(_LEVEL_DEFAULT_SCORES[level])
        finally:
            self._syncing_score = False

    def _populate_level_options(
        self,
        question_type: QuestionType | None,
        *,
        preferred: str | None = None,
    ) -> None:
        levels = _LEVELS_BY_TYPE.get(question_type or QuestionType.BLANK, _LEVELS_ALL)
        preferred_level = self._normalize_level_value(preferred) or _DEFAULT_LEVEL_BY_TYPE.get(
            question_type or QuestionType.BLANK,
            levels[0],
        )
        self._syncing_level = True
        try:
            self._difficulty_combo.blockSignals(True)
            self._difficulty_combo.clear()
            for level in levels:
                self._difficulty_combo.addItem(level, userData=level)
            idx = self._difficulty_combo.findData(preferred_level)
            if idx < 0:
                idx = 0
            self._difficulty_combo.setCurrentIndex(idx)
        finally:
            self._difficulty_combo.blockSignals(False)
            self._syncing_level = False
        self._apply_default_score_for_level(self._difficulty_combo.currentIndex())

    def _sync_option_rows(self, question_type: QuestionType | None) -> None:
        visible_count = 6
        labels = list(VALID_OPTION_LABELS)
        if question_type == QuestionType.TRUE_FALSE:
            visible_count = 2
            labels = ["Đúng", "Sai"]
        elif question_type == QuestionType.MULTIPLE_ANSWER:
            visible_count = 6

        for idx, (label_widget, edit, cb) in enumerate(self._option_rows):
            is_visible = idx < visible_count
            label_widget.setVisible(is_visible)
            edit.setVisible(is_visible)
            cb.setVisible(is_visible)
            if is_visible:
                label_widget.setText(f"{labels[idx]}.")
                if question_type == QuestionType.TRUE_FALSE:
                    edit.setPlaceholderText(f"Lựa chọn {labels[idx]}…")
                else:
                    edit.setPlaceholderText(f"Lựa chọn {VALID_OPTION_LABELS[idx]}…")
            else:
                edit.clear()
                cb.setChecked(False)

    @staticmethod
    def _normalize_level_value(value: str | None) -> str:
        raw = str(value or "").strip()
        return _LEGACY_DIFFICULTY_TO_LEVEL.get(raw, raw)

    def _refresh_formula_preview(self, *_args) -> None:
        if not hasattr(self, "_formula_preview_browser"):
            return

        qt = self._type_combo.currentData()
        content = self._content_edit.toPlainText().strip()
        explanation = self._explanation_edit.toPlainText().strip()
        hint = self._hint_edit.text().strip()
        difficulty = str(self._difficulty_combo.currentData() or "").strip()
        score = self._score_spin.value()

        def _render_text(text: str, *, empty: str) -> str:
            if text:
                return f"<div class='text'>{render_inline_latex_html(text)}</div>"
            return f"<div class='empty'>{empty}</div>"

        html_parts = [
            "<html><head><style>",
            "body { font-family: 'Segoe UI', sans-serif; font-size: 12pt; color: #1f2937; margin: 0; }",
            ".panel { border: 1px solid #e3e8f3; border-radius: 8px; padding: 12px; background: #fff; }",
            ".section { margin-bottom: 12px; }",
            ".heading { font-weight: 700; color: #0f172a; margin-bottom: 6px; }",
            ".meta { color: #6b7280; font-size: 10.5pt; margin-bottom: 8px; line-height: 1.45; }",
            ".label { font-weight: 700; color: #111827; margin-bottom: 4px; }",
            ".text { white-space: pre-wrap; line-height: 1.5; }",
            ".empty { color: #9ca3af; font-style: italic; }",
            ".score { color: #c0392b; font-weight: 700; }",
            ".answer-list { margin: 0 0 0 20px; padding: 0; }",
            ".answer-list li { margin-bottom: 4px; }",
            ".math { font-weight: 600; color: #111827; }",
            "</style></head><body><div class='panel'>",
            "<div class='section'>",
            "<div class='heading'>Nội dung câu hỏi</div>",
            _render_text(content, empty="Chưa nhập nội dung."),
            "</div>",
        ]

        meta_bits: list[str] = []
        if qt:
            meta_bits.append(f"Loại: {render_inline_latex_html(_TYPE_LABELS.get(qt, str(qt)))}")
        if difficulty:
            meta_bits.append(f"Mức độ: {render_inline_latex_html(difficulty)}")
        meta_bits.append(f"<span class='score'>Điểm: {score:.2f}</span>")
        html_parts.extend(
            [
                "<div class='section'>",
                "<div class='heading'>Thông tin đang chọn</div>",
                f"<div class='meta'>{' &nbsp;|&nbsp; '.join(meta_bits)}</div>",
                _render_text(hint, empty="Chưa có gợi ý."),
                "</div>",
            ]
        )

        if qt in (QuestionType.MULTIPLE_CHOICE, QuestionType.MULTIPLE_ANSWER, QuestionType.TRUE_FALSE):
            option_items: list[str] = []
            for label, (_, edit, cb) in zip(VALID_OPTION_LABELS, self._option_rows, strict=False):
                if not edit.isVisible():
                    continue
                option_text = edit.text().strip()
                mark = "✓" if cb.isChecked() else "✗"
                rendered = (
                    render_inline_latex_html(option_text)
                    if option_text
                    else "<span class='empty'>(trống)</span>"
                )
                option_items.append(f"<li><b>{label}.</b> [{mark}] {rendered}</li>")
            html_parts.extend(
                [
                    "<div class='section'>",
                    "<div class='heading'>Phương án</div>",
                    "<ul class='answer-list'>",
                    "".join(option_items) if option_items else "<li class='empty'>Chưa có phương án.</li>",
                    "</ul>",
                    "</div>",
                ]
            )
        else:
            accepted = [a.strip() for a in self._answers_edit.text().split("||") if a.strip()]
            if accepted:
                items = "".join(f"<li>{render_inline_latex_html(a)}</li>" for a in accepted)
                accepted_html = f"<ol class='answer-list'>{items}</ol>"
            else:
                accepted_html = "<div class='empty'>Chưa có đáp án chấp nhận.</div>"
            html_parts.extend(
                [
                    "<div class='section'>",
                    "<div class='heading'>Đáp án chấp nhận</div>",
                    accepted_html,
                    "</div>",
                ]
            )

        if explanation:
            html_parts.extend(
                [
                    "<div class='section'>",
                    "<div class='heading'>Giải thích</div>",
                    _render_text(explanation, empty=""),
                    "</div>",
                ]
            )

        html_parts.append("</div></body></html>")
        self._formula_preview_browser.setHtml("".join(html_parts))

    def _toggle_basic_info_panel(self, expanded: bool) -> None:
        if not hasattr(self, "_basic_info_content") or self._basic_info_content is None:
            return
        self._basic_info_content.setVisible(expanded)
        if hasattr(self, "_basic_info_toggle") and self._basic_info_toggle is not None:
            self._basic_info_toggle.setArrowType(
                Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow
            )
            self._basic_info_toggle.setText("Thu gọn" if expanded else "Mở rộng")

    def _toggle_formula_preview(self, expanded: bool) -> None:
        self._formula_preview_content.setVisible(expanded)
        self._formula_preview_toggle.setArrowType(
            Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow
        )
        self._formula_preview_toggle.setText("Thu gọn" if expanded else "Mở rộng")
