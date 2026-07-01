"""Dialog to collect submitter name and ID before starting a bài kiểm tra attempt.

Only shown in Kiểm tra mode (ARCHITECTURE §7.2). Luyện tập and Ôn tập modes do not
require submitter identification.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)


class SubmitterInfoDialog(QDialog):
    """Collect 'Họ và tên' and 'ID / Mã số' before a bài kiểm tra starts."""

    def __init__(self, quiz_title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Thông tin người làm bài")
        self.setMinimumWidth(400)
        self.setModal(True)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint
        )
        self._build_ui(quiz_title)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self, quiz_title: str) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Intro label
        intro = QLabel(
            f"<b>{quiz_title}</b><br><br>"
            "Bài kiểm tra ở <b>chế độ Kiểm tra</b>.<br>"
            "Vui lòng điền đầy đủ thông tin trước khi bắt đầu làm bài."
        )
        intro.setWordWrap(True)
        intro.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(intro)

        # Form
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("Nhập họ và tên đầy đủ")
        self._name_edit.setMinimumWidth(240)

        self._id_edit = QLineEdit()
        self._id_edit.setPlaceholderText("Mã số sinh viên / Mã nhân viên...")

        form.addRow("Họ và tên: *", self._name_edit)
        form.addRow("ID / Mã số: *", self._id_edit)
        layout.addLayout(form)

        # Validation note (hidden until needed)
        self._error_label = QLabel(
            '<span style="color: #c0392b;">⚠ Vui lòng điền đầy đủ Họ tên và ID.</span>'
        )
        self._error_label.hide()
        layout.addWidget(self._error_label)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Bắt đầu làm bài")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Hủy")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _on_accept(self) -> None:
        name = self._name_edit.text().strip()
        id_ = self._id_edit.text().strip()
        if not name or not id_:
            self._error_label.show()
            if not name:
                self._name_edit.setFocus()
            else:
                self._id_edit.setFocus()
            return
        self._error_label.hide()
        self.accept()

    # ------------------------------------------------------------------
    # Public properties
    # ------------------------------------------------------------------

    @property
    def submitter_name(self) -> str:
        return self._name_edit.text().strip()

    @property
    def submitter_id(self) -> str:
        return self._id_edit.text().strip()
