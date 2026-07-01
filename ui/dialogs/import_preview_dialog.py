"""Hộp thoại xem trước nhập dữ liệu.

Hiển thị kết quả phân tích (tóm tắt + bảng vấn đề) và cho phép người dùng
ghi nhận một lần nhập hợp lệ vào ngân hàng câu hỏi đã chọn.

Rules enforced here (QUIZ_APP_IMPORT_FORMAT.md §12):
  - Nút nhập chỉ được bật khi has_errors là False.
  - Cancel is always available.
  - No silent error swallowing – every issue shown with line number.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from core.utils.error_mapper import map_exception_to_user_message
from core.utils.exceptions import DatabaseError, ImportError, QuizAppError
from modules.question_bank.importer import ParseResult
from ui.facades.import_facade import ImportFacade


class ImportPreviewDialog(QDialog):
    """Xem trước kết quả phân tích và tùy chọn ghi vào cơ sở dữ liệu."""

    _SEVERITY_BG: dict[str, str] = {
        "ERROR": "#c0392b",
        "WARNING": "#e67e22",
        "INFO": "#27ae60",
    }
    _SEVERITY_FG: dict[str, str] = {
        "ERROR": "#ffffff",
        "WARNING": "#ffffff",
        "INFO": "#ffffff",
    }

    def __init__(
        self,
        parse_result: ParseResult,
        bank_id: int,
        file_path: Path,
        facade: ImportFacade,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._result = parse_result
        self._bank_id = bank_id
        self._file_path = file_path
        self._facade = facade
        self._was_imported = False

        self.setWindowTitle("Xem trước nhập dữ liệu – " + file_path.name)
        self.setMinimumSize(820, 520)
        self._build_ui()

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    @property
    def was_imported(self) -> bool:
        return self._was_imported

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(14, 14, 14, 14)

        layout.addWidget(self._build_summary_group())

        if self._result.issues:
            layout.addWidget(QLabel("<b>Chi tiết vấn đề phát hiện:</b>"))
            layout.addWidget(self._build_issues_table(), stretch=1)
        else:
            ok_lbl = QLabel("✓ Không có vấn đề nào – file đã sẵn sàng để nhập.")
            ok_lbl.setStyleSheet("color: #27ae60; font-weight: bold; font-size: 14px;")
            layout.addWidget(ok_lbl)

        layout.addWidget(self._build_button_bar())

    def _build_summary_group(self) -> QGroupBox:
        box = QGroupBox("Tóm tắt phân tích file")
        vl = QVBoxLayout(box)

        valid = len(self._result.parsed_questions)
        total = self._result.total_rows
        err_c = self._result.error_count
        warn_c = self._result.warning_count
        info_c = self._result.info_count

        html = (
            f"<b>Tổng số dòng dữ liệu:</b> {total} &nbsp;|&nbsp; "
            f"<b>Hợp lệ:</b> {valid} &nbsp;|&nbsp; "
            f"<b style='color:{self._SEVERITY_BG['ERROR']}'>Lỗi (ERROR):</b> {err_c}"
            f" &nbsp;|&nbsp; "
            f"<b style='color:{self._SEVERITY_BG['WARNING']}'>Cảnh báo:</b> {warn_c}"
            f" &nbsp;|&nbsp; "
            f"<b style='color:{self._SEVERITY_BG['INFO']}'>Thông tin:</b> {info_c}"
        )
        summary_lbl = QLabel(html)
        summary_lbl.setTextFormat(Qt.TextFormat.RichText)
        vl.addWidget(summary_lbl)

        if self._result.has_errors:
            warn_lbl = QLabel(
                "⚠  File có lỗi nghiêm trọng. Vui lòng sửa file và thử lại; "
                "nút nhập đã bị vô hiệu hóa."
            )
            warn_lbl.setStyleSheet(
                f"color: {self._SEVERITY_BG['ERROR']}; font-weight: bold;"
            )
            vl.addWidget(warn_lbl)

        return box

    def _build_issues_table(self) -> QTableWidget:
        issues = self._result.issues
        tbl = QTableWidget(len(issues), 4)
        tbl.setHorizontalHeaderLabels(["Dòng", "Mức độ", "Cột", "Thông báo"])
        tbl.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.Stretch
        )
        tbl.horizontalHeader().setDefaultSectionSize(90)
        tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        tbl.setAlternatingRowColors(True)
        tbl.verticalHeader().setVisible(False)

        for r_idx, issue in enumerate(issues):
            row_text = str(issue.row) if issue.row > 0 else "Header"
            row_item = QTableWidgetItem(row_text)
            row_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            sev_item = QTableWidgetItem(issue.severity)
            sev_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            bg = self._SEVERITY_BG.get(issue.severity, "#888888")
            fg = self._SEVERITY_FG.get(issue.severity, "#ffffff")
            sev_item.setBackground(QColor(bg))
            sev_item.setForeground(QColor(fg))

            tbl.setItem(r_idx, 0, row_item)
            tbl.setItem(r_idx, 1, sev_item)
            tbl.setItem(r_idx, 2, QTableWidgetItem(issue.column))
            tbl.setItem(r_idx, 3, QTableWidgetItem(issue.message))

        tbl.resizeRowsToContents()
        return tbl

    def _build_button_bar(self) -> QDialogButtonBox:
        btn_box = QDialogButtonBox()

        self._import_btn = QPushButton("⬇  Nhập câu hỏi")
        self._import_btn.setEnabled(not self._result.has_errors)
        self._import_btn.setDefault(not self._result.has_errors)
        self._import_btn.clicked.connect(self._on_import)
        btn_box.addButton(self._import_btn, QDialogButtonBox.ButtonRole.AcceptRole)

        cancel_btn = btn_box.addButton(
            "Hủy", QDialogButtonBox.ButtonRole.RejectRole
        )
        cancel_btn.clicked.connect(self.reject)

        return btn_box

    # ------------------------------------------------------------------
    # Slot
    # ------------------------------------------------------------------

    def _on_import(self) -> None:
        self._import_btn.setEnabled(False)
        self._import_btn.setText("Đang nhập...")

        try:
            summary = self._facade.commit_preview(self._result, self._bank_id)
            self._was_imported = True

            msg = (
                f"Nhập dữ liệu thành công!\n\n"
                f"{summary.inserted} câu hỏi đã được thêm vào ngân hàng."
            )
            if summary.skipped_rows:
                msg += (
                    f"\n{len(summary.skipped_rows)} dòng bị bỏ qua do trùng "
                    "với dữ liệu đã có trong cơ sở dữ liệu."
                )
            QMessageBox.information(self, "Nhập dữ liệu hoàn tất", msg)
            self.accept()

        except (ImportError, DatabaseError, QuizAppError) as exc:
            self._import_btn.setEnabled(True)
            self._import_btn.setText("⬇  Nhập câu hỏi")
            QMessageBox.critical(
                self,
                "Lỗi nhập dữ liệu",
                f"Nhập dữ liệu thất bại:\n{map_exception_to_user_message(exc)}",
            )

        except Exception as exc:
            self._import_btn.setEnabled(True)
            self._import_btn.setText("⬇  Nhập câu hỏi")
            QMessageBox.critical(
                self,
                "Lỗi nhập dữ liệu",
                f"Nhập dữ liệu thất bại:\n{map_exception_to_user_message(exc)}",
            )
