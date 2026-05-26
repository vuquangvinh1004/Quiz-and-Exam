from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)


class BankMetaDialog(QDialog):
    """Dialog to create/update question bank metadata."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        initial_data: dict | None = None,
        edit_mode: bool = False,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Sửa ngân hàng câu hỏi" if edit_mode else "Thêm ngân hàng câu hỏi")
        self.setMinimumWidth(420)
        d = initial_data or {}

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.DontWrapRows)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self._name = QLineEdit()
        self._name.setPlaceholderText("Bắt buộc")
        self._name.setText(d.get("name", ""))
        form.addRow("Tên ngân hàng *:", self._name)

        self._school = QLineEdit()
        self._school.setPlaceholderText("Tùy chọn")
        self._school.setText(d.get("school", ""))
        form.addRow("Trường:", self._school)

        self._department = QLineEdit()
        self._department.setPlaceholderText("Tùy chọn")
        self._department.setText(d.get("department", ""))
        form.addRow("Khoa / Đơn vị:", self._department)

        self._subject = QLineEdit()
        self._subject.setPlaceholderText("Tùy chọn")
        self._subject.setText(d.get("subject", ""))
        form.addRow("Môn học:", self._subject)

        self._course_code = QLineEdit()
        self._course_code.setPlaceholderText("Tùy chọn")
        self._course_code.setText(d.get("course_code", ""))
        form.addRow("Mã học phần:", self._course_code)

        self._exam_title = QLineEdit()
        self._exam_title.setPlaceholderText("Tùy chọn")
        self._exam_title.setText(d.get("exam_title", ""))
        form.addRow("Tiêu đề bài thi:", self._exam_title)

        ok_label = "Lưu" if edit_mode else "Thêm"
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(ok_label)
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Hủy")
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _validate_and_accept(self) -> None:
        if not self._name.text().strip():
            QMessageBox.warning(self, "Lỗi", "Tên ngân hàng không được để trống.")
            self._name.setFocus()
            return
        self.accept()

    def get_data(self) -> dict:
        return {
            "name": self._name.text().strip(),
            "school": self._school.text().strip(),
            "department": self._department.text().strip(),
            "subject": self._subject.text().strip(),
            "course_code": self._course_code.text().strip(),
            "exam_title": self._exam_title.text().strip(),
        }
