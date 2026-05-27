"""Question Editor Dialog – create or edit a single question.

Supports all four question types (MC, MA, BLANK, SA) with a dynamic
form that switches sections based on the selected type.

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
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.database.models import Question
from core.domain.services.question_service import QuestionEditData
from core.utils.constants import (
    BLANK_PLACEHOLDER,
    VALID_OPTION_LABELS,
    Difficulty,
    QuestionStatus,
    QuestionType,
)
from ui.facades.question_bank_facade import QuestionBankFacade
from ui.styles import apply_checkbox_style

_TYPE_LABELS = {
    QuestionType.MULTIPLE_CHOICE: "Multiple Choice (1 đáp án đúng)",
    QuestionType.MULTIPLE_ANSWER: "Multiple Answer (nhiều đáp án đúng)",
    QuestionType.BLANK: "Điền vào chỗ trống (Blank)",
    QuestionType.SHORT_ANSWER: "Trả lời ngắn (Short Answer)",
}
_TYPE_FROM_INDEX = list(_TYPE_LABELS.keys())


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
        basic = QGroupBox("Thông tin cơ bản")
        fl = QFormLayout(basic)
        fl.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)

        self._type_combo = QComboBox()
        for qt in _TYPE_FROM_INDEX:
            self._type_combo.addItem(_TYPE_LABELS[qt], userData=qt)
        self._type_combo.currentIndexChanged.connect(self._on_type_changed)
        fl.addRow("Loại câu hỏi *:", self._type_combo)

        self._content_edit = QTextEdit()
        self._content_edit.setPlaceholderText(
            "Nhập nội dung câu hỏi…\n"
            "Với loại Blank, dùng ________ để đánh dấu chỗ trống."
        )
        self._content_edit.setFixedHeight(90)
        fl.addRow("Nội dung *:", self._content_edit)

        self._code_edit = QLineEdit()
        self._code_edit.setPlaceholderText("Tự động nếu để trống")
        fl.addRow("Mã câu hỏi:", self._code_edit)

        self._category_edit = QLineEdit()
        fl.addRow("Chương:", self._category_edit)

        self._difficulty_combo = QComboBox()
        for d in Difficulty:
            self._difficulty_combo.addItem(d.value.capitalize(), userData=d.value)
        self._difficulty_combo.setCurrentIndex(
            self._difficulty_combo.findData(Difficulty.MEDIUM.value)
        )
        fl.addRow("Độ khó:", self._difficulty_combo)

        self._score_spin = QDoubleSpinBox()
        self._score_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self._score_spin.setRange(0.01, 100.0)
        self._score_spin.setSingleStep(0.5)
        self._score_spin.setValue(1.0)
        fl.addRow("Điểm:", self._score_spin)

        self._status_combo = QComboBox()
        for s in QuestionStatus:
            self._status_combo.addItem(s.value.capitalize(), userData=s.value)
        fl.addRow("Trạng thái:", self._status_combo)

        self._tags_edit = QLineEdit()
        self._tags_edit.setPlaceholderText("tag1, tag2, tag3")
        fl.addRow("Tags:", self._tags_edit)

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
            cb = QCheckBox("Đúng")
            apply_checkbox_style(cb)
            cb.setFixedWidth(60)
            row_hl.addWidget(lbl)
            row_hl.addWidget(edit, stretch=1)
            row_hl.addWidget(cb)
            opt_vl.addLayout(row_hl)
            self._option_rows.append((lbl, edit, cb))

        mc_note = QLabel(
            "<i>Multiple Choice: chọn đúng 1 ô 'Đúng'. "
            "Multiple Answer: chọn ít nhất 2 ô 'Đúng'.</i>"
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
        ans_fl.addRow("Đáp án (*):", self._answers_edit)

        self._case_sensitive_cb = QCheckBox("Phân biệt hoa thường")
        apply_checkbox_style(self._case_sensitive_cb)
        ans_fl.addRow("", self._case_sensitive_cb)

        self._trim_whitespace_cb = QCheckBox("Bỏ khoảng trắng đầu/cuối")
        apply_checkbox_style(self._trim_whitespace_cb)
        self._trim_whitespace_cb.setChecked(True)
        ans_fl.addRow("", self._trim_whitespace_cb)

        blank_hint = QLabel(
            f"<i>Blank: Câu hỏi phải chứa ít nhất một <b>{BLANK_PLACEHOLDER}</b> làm chỗ trống "
            f"(có thể dùng nhiều {BLANK_PLACEHOLDER} cho nhiều chỗ điền).</i>"
        )
        blank_hint.setTextFormat(Qt.TextFormat.RichText)
        blank_hint.setWordWrap(True)
        ans_fl.addRow(blank_hint)
        form_layout.addWidget(self._answers_group)

        # ── Hint / Explanation ───────────────────────────────────────
        aux = QGroupBox("Gợi ý và giải thích")
        aux_fl = QFormLayout(aux)
        self._hint_edit = QLineEdit()
        self._hint_edit.setPlaceholderText("Hiển thị trong chế độ Luyện tập / Học tập")
        aux_fl.addRow("Gợi ý:", self._hint_edit)
        self._explanation_edit = QTextEdit()
        self._explanation_edit.setPlaceholderText("Giải thích sau khi kết thúc bài…")
        self._explanation_edit.setFixedHeight(70)
        aux_fl.addRow("Giải thích:", self._explanation_edit)
        form_layout.addWidget(aux)

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

    # ------------------------------------------------------------------
    # Dynamic type switching
    # ------------------------------------------------------------------

    def _on_type_changed(self, _index: int) -> None:
        qt = self._type_combo.currentData()
        is_mc_ma = qt in (QuestionType.MULTIPLE_CHOICE, QuestionType.MULTIPLE_ANSWER)
        is_blank_sa = qt in (QuestionType.BLANK, QuestionType.SHORT_ANSWER)
        self._options_group.setVisible(is_mc_ma)
        self._answers_group.setVisible(is_blank_sa)

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
        self._category_edit.setText(q.category or "")
        self._hint_edit.setText(q.hint or "")
        self._explanation_edit.setPlainText(q.explanation or "")
        self._score_spin.setValue(q.point_value or 1.0)
        self._case_sensitive_cb.setChecked(q.case_sensitive)
        self._trim_whitespace_cb.setChecked(q.trim_whitespace)

        diff_idx = self._difficulty_combo.findData(q.difficulty or "medium")
        if diff_idx >= 0:
            self._difficulty_combo.setCurrentIndex(diff_idx)

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

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def _on_save(self) -> None:
        qt: QuestionType = self._type_combo.currentData()

        # Build options list for MC/MA
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
            difficulty=self._difficulty_combo.currentData() or "medium",
            score=self._score_spin.value(),
            hint=self._hint_edit.text(),
            explanation=self._explanation_edit.toPlainText(),
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
