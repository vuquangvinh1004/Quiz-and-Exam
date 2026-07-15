"""Answer rendering component for quiz runner.

Encapsulates UI rendering and answer payload extraction for MC/MA/TF/BLANK/SA/ES/PR.
"""
from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QLineEdit, QRadioButton, QVBoxLayout, QWidget

from core.domain.services.quiz_service import QuizQuestionSnapshot
from core.utils.validators import count_blank_placeholders


class QuizAnswerRenderer:
    """Render answer widgets and transform user input into payload dicts."""

    def __init__(self, parent: QWidget | None = None) -> None:
        self._options_container = QWidget(parent)
        self._options_layout = QVBoxLayout(self._options_container)
        self._options_layout.setContentsMargins(0, 4, 0, 4)
        self._options_layout.setSpacing(2)
        self._options_container.hide()

        self._text_answer = QLineEdit(parent)
        self._text_answer.setFixedHeight(36)
        self._text_answer.setStyleSheet("font-size: 15px; padding: 4px 8px;")
        self._text_answer.hide()

        self._radio_pool: list[QRadioButton] = []
        self._check_pool: list[QCheckBox] = []
        self._radio_keys: list[str] = []
        self._check_keys: list[str] = []

        self._build_option_pools()

    def attach(self, layout: QVBoxLayout) -> None:
        """Attach renderer widgets into the question content layout."""
        layout.addWidget(self._options_container)
        layout.addWidget(self._text_answer)

    def render_question(self, qq: QuizQuestionSnapshot) -> None:
        """Re-render answer area for one QuizQuestionSnapshot."""
        qtype = qq.type
        opts = qq.options or []

        if qtype in ("MC", "TF"):
            self._options_container.show()
            self._text_answer.hide()
            self._radio_keys = []

            for cb in self._check_pool:
                cb.hide()

            for i, rb in enumerate(self._radio_pool):
                if i < len(opts):
                    rb.setText(opts[i]["text"])
                    rb.setChecked(False)
                    rb.show()
                    self._radio_keys.append(opts[i]["key"])
                else:
                    rb.hide()
            return

        if qtype == "MA":
            self._options_container.show()
            self._text_answer.hide()
            self._check_keys = []

            for rb in self._radio_pool:
                rb.hide()

            for i, cb in enumerate(self._check_pool):
                if i < len(opts):
                    cb.setText(opts[i]["text"])
                    cb.setChecked(False)
                    cb.show()
                    self._check_keys.append(opts[i]["key"])
                else:
                    cb.hide()
            return

        self._options_container.hide()
        self._text_answer.show()
        self._text_answer.setReadOnly(False)

        blank_count = count_blank_placeholders(qq.content)
        placeholder = (
            f"Điền vào {blank_count} chỗ trống, phân cách bằng || (VD: đáp án 1||đáp án 2)"
            if blank_count > 1
            else "Điền vào chỗ trống..."
        ) if qtype == "BLANK" else "Nhập câu trả lời..."
        self._text_answer.setPlaceholderText(placeholder)
        self._text_answer.clear()

    def current_payload(self, qtype: str) -> dict:
        """Read current UI input and convert to answer payload."""
        if qtype in ("MC", "TF"):
            for i, rb in enumerate(self._radio_pool):
                if rb.isVisible() and rb.isChecked() and i < len(self._radio_keys):
                    return {"selected": self._radio_keys[i]}
            return {}

        if qtype == "MA":
            selected = [
                self._check_keys[i]
                for i, cb in enumerate(self._check_pool)
                if cb.isVisible() and cb.isChecked() and i < len(self._check_keys)
            ]
            return {"selected": selected} if selected else {}

        text = self._text_answer.text().strip()
        return {"text": text} if text else {}

    def restore_answer(self, qtype: str, payload: dict) -> None:
        """Restore persisted answer payload into rendered widgets."""
        if qtype in ("MC", "TF"):
            key = payload.get("selected", "")
            for i, rb in enumerate(self._radio_pool):
                if rb.isVisible() and i < len(self._radio_keys):
                    rb.setChecked(self._radio_keys[i] == key)
            return

        if qtype == "MA":
            selected = set(payload.get("selected", []))
            for i, cb in enumerate(self._check_pool):
                if cb.isVisible() and i < len(self._check_keys):
                    cb.setChecked(self._check_keys[i] in selected)
            return

        self._text_answer.setText(payload.get("text", ""))

    def set_input_enabled(self, enabled: bool) -> None:
        """Enable/disable all answer inputs for lock/unlock behavior."""
        for rb in self._radio_pool:
            rb.setEnabled(enabled)
        for cb in self._check_pool:
            cb.setEnabled(enabled)
        self._text_answer.setReadOnly(not enabled)

    def _build_option_pools(self) -> None:
        opt_style = (
            "font-size: 15px;"
            "padding: 10px 14px;"
            "border: 1px solid #ced4da;"
            "border-radius: 6px;"
            "background: #ffffff;"
            "color: #212529;"
            "margin: 2px 0;"
        )
        opt_checked = (
            "font-size: 15px;"
            "padding: 10px 14px;"
            "border: 2px solid #2980b9;"
            "border-radius: 6px;"
            "background: #eaf4fb;"
            "color: #1a5276;"
            "margin: 2px 0;"
        )
        rb_style = (
            f"QRadioButton {{ {opt_style} }}"
            f"QRadioButton:checked {{ {opt_checked} }}"
            "QRadioButton::indicator { width: 18px; height: 18px; }"
            "QRadioButton::indicator:unchecked { border: 2px solid #aaa; border-radius: 9px; background: #fff; }"
            "QRadioButton::indicator:checked { border: 2px solid #2980b9; border-radius: 9px; background: #2980b9; }"
        )
        cb_style = (
            f"QCheckBox {{ {opt_style} }}"
            f"QCheckBox:checked {{ {opt_checked} }}"
            "QCheckBox::indicator { width: 18px; height: 18px; }"
            "QCheckBox::indicator:unchecked { border: 2px solid #aaa; border-radius: 3px; background: #fff; }"
            "QCheckBox::indicator:checked { border: 2px solid #2980b9; border-radius: 3px; background: #2980b9; }"
        )

        for idx in range(6):
            rb = QRadioButton()
            rb.setAutoExclusive(False)
            rb.setStyleSheet(rb_style)
            rb.hide()
            rb.toggled.connect(
                lambda checked, i=idx: self._on_mc_toggled(i, checked)
            )
            self._options_layout.addWidget(rb)
            self._radio_pool.append(rb)

            cb = QCheckBox()
            cb.setStyleSheet(cb_style)
            cb.hide()
            self._options_layout.addWidget(cb)
            self._check_pool.append(cb)

    def _on_mc_toggled(self, toggled_idx: int, checked: bool) -> None:
        if not checked:
            return
        for i, rb in enumerate(self._radio_pool):
            if i != toggled_idx and rb.isChecked():
                rb.setChecked(False)
