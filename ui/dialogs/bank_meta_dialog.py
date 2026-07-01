from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class _CloRowWidget(QFrame):
    """One editable row for course learning outcome metadata."""

    def __init__(
        self,
        *,
        code: str = "",
        description: str = "",
        on_remove,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._on_remove = on_remove
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self._code = QLineEdit()
        self._code.setPlaceholderText("Ví dụ: CLO_1")
        self._code.setText(code)
        self._code.setFixedWidth(140)
        layout.addWidget(self._code)

        self._description = QLineEdit()
        self._description.setPlaceholderText("Mô tả chuẩn đầu ra học phần")
        self._description.setText(description)
        layout.addWidget(self._description, stretch=1)

        remove_btn = QPushButton("Bớt")
        remove_btn.setFixedWidth(72)
        remove_btn.clicked.connect(self._handle_remove)
        layout.addWidget(remove_btn)

    def _handle_remove(self) -> None:
        self._on_remove(self)

    def get_data(self) -> dict[str, str]:
        return {
            "code": self._code.text().strip(),
            "description": self._description.text().strip(),
        }


class BankMetaDialog(QDialog):
    """Dialog to create/update question bank metadata."""

    _ASSESSMENT_TYPES: tuple[tuple[str, str], ...] = (
        ("Tùy chọn", ""),
        ("Thường xuyên", "Thường xuyên"),
        ("Định kỳ", "Định kỳ"),
        ("Tổng kết", "Tổng kết"),
    )

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        initial_data: dict | None = None,
        edit_mode: bool = False,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Sửa ngân hàng câu hỏi" if edit_mode else "Thêm ngân hàng câu hỏi")
        self.setMinimumWidth(760)
        self.setMinimumHeight(520)
        self._clo_rows: list[_CloRowWidget] = []
        d = initial_data or {}
        self._legacy_exam_title = str(d.get("exam_title", ""))

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
        form.addRow("Học phần:", self._subject)

        self._course_code = QLineEdit()
        self._course_code.setPlaceholderText("Tùy chọn")
        self._course_code.setText(d.get("course_code", ""))
        form.addRow("Mã học phần:", self._course_code)

        self._assessment_type = QComboBox()
        for label, value in self._ASSESSMENT_TYPES:
            self._assessment_type.addItem(label, userData=value)
        initial_assessment_type = str(d.get("assessment_type", ""))
        for idx in range(self._assessment_type.count()):
            if self._assessment_type.itemData(idx) == initial_assessment_type:
                self._assessment_type.setCurrentIndex(idx)
                break
        form.addRow("Loại đánh giá:", self._assessment_type)

        clo_box = QVBoxLayout()
        clo_header = QHBoxLayout()
        clo_header.setContentsMargins(0, 0, 0, 0)
        clo_title = QLabel("<b>Chuẩn đầu ra học phần</b>")
        clo_header.addWidget(clo_title)
        clo_header.addStretch()
        add_clo_btn = QPushButton("Thêm CLO")
        add_clo_btn.clicked.connect(self._add_clo_row)
        clo_header.addWidget(add_clo_btn)
        clo_box.addLayout(clo_header)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        code_header = QLabel("Mã CLO")
        code_header.setFixedWidth(140)
        desc_header = QLabel("Mô tả CLO")
        action_header = QLabel("Thao tác")
        action_header.setFixedWidth(72)
        header_row.addWidget(code_header)
        header_row.addWidget(desc_header, stretch=1)
        header_row.addWidget(action_header)
        clo_box.addLayout(header_row)

        self._clo_container = QWidget()
        self._clo_container_layout = QVBoxLayout(self._clo_container)
        self._clo_container_layout.setContentsMargins(0, 0, 0, 0)
        self._clo_container_layout.setSpacing(8)
        self._clo_container_layout.addStretch()

        clo_scroll = QScrollArea()
        clo_scroll.setWidgetResizable(True)
        clo_scroll.setFrameShape(QFrame.Shape.NoFrame)
        clo_scroll.setWidget(self._clo_container)
        clo_scroll.setMinimumHeight(220)
        clo_box.addWidget(clo_scroll)

        initial_clos = d.get("course_learning_outcomes", []) or []
        if initial_clos:
            for row in initial_clos:
                self._add_clo_row(
                    code=str(row.get("code", "")),
                    description=str(row.get("description", "")),
                )
        else:
            self._add_clo_row()

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
        layout.addSpacing(8)
        layout.addLayout(clo_box, stretch=1)
        layout.addWidget(buttons)

    def _add_clo_row(self, checked: bool = False, *, code: str = "", description: str = "") -> None:
        del checked
        row = _CloRowWidget(
            code=code,
            description=description,
            on_remove=self._remove_clo_row,
            parent=self._clo_container,
        )
        self._clo_rows.append(row)
        self._clo_container_layout.insertWidget(len(self._clo_rows) - 1, row)

    def _remove_clo_row(self, row: _CloRowWidget) -> None:
        if row not in self._clo_rows:
            return
        if len(self._clo_rows) == 1:
            row_data = row.get_data()
            if not row_data["code"] and not row_data["description"]:
                return
        self._clo_rows.remove(row)
        row.setParent(None)
        row.deleteLater()
        if not self._clo_rows:
            self._add_clo_row()

    def _validate_and_accept(self) -> None:
        if not self._name.text().strip():
            QMessageBox.warning(self, "Lỗi", "Tên ngân hàng không được để trống.")
            self._name.setFocus()
            return

        for row in self._clo_rows:
            row_data = row.get_data()
            has_code = bool(row_data["code"])
            has_description = bool(row_data["description"])
            if has_code != has_description:
                QMessageBox.warning(
                    self,
                    "Lỗi",
                    "Mỗi chuẩn đầu ra học phần phải có đủ Mã CLO và Mô tả CLO.",
                )
                return
        self.accept()

    def get_data(self) -> dict:
        clos: list[dict[str, str]] = []
        for row in self._clo_rows:
            row_data = row.get_data()
            if not row_data["code"] and not row_data["description"]:
                continue
            clos.append(row_data)
        return {
            "name": self._name.text().strip(),
            "school": self._school.text().strip(),
            "department": self._department.text().strip(),
            "subject": self._subject.text().strip(),
            "course_code": self._course_code.text().strip(),
            "assessment_type": str(self._assessment_type.currentData() or ""),
            "course_learning_outcomes": clos,
            "exam_title": self._legacy_exam_title,
        }
