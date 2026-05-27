"""Import view: pick a CSV/XLSX file, choose a question bank, preview and commit.

UI flow (QUIZ_APP_ARCHITECTURE.md §6.1):
    1. User picks a .csv or .xlsx file.
    2. User picks (or creates) a question bank.
    3. User clicks "Xem trước" → ImportPreviewDialog opens.
    4. Dialog shows ERROR / WARNING / INFO issues.
    5. If no ERRORs, user confirms → questions written to DB.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.utils.error_mapper import map_exception_to_user_message
from core.utils.exceptions import DatabaseError, ImportError, QuizAppError
from ui.dialogs.import_preview_dialog import ImportPreviewDialog
from ui.facades.import_facade import ImportFacade
from ui.utils.error_handler import show_critical_error


class ImportView(QWidget):
    """Import CSV / Excel file into a question bank."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._file_path: Path | None = None
        self._facade = ImportFacade()
        self._build_ui()
        self._load_banks()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        title = QLabel("Import câu hỏi từ file CSV / Excel")
        title.setObjectName("view_title")
        layout.addWidget(title)

        # Step 1 – File picker
        file_group = QGroupBox("Bước 1 – Chọn file import")
        file_vl = QVBoxLayout(file_group)
        file_hl = QHBoxLayout()
        self._file_edit = QLineEdit()
        self._file_edit.setReadOnly(True)
        self._file_edit.setPlaceholderText("Chưa chọn file…")
        browse_btn = QPushButton("Duyệt file…")
        browse_btn.clicked.connect(self._browse_file)
        file_hl.addWidget(self._file_edit, stretch=1)
        file_hl.addWidget(browse_btn)
        file_vl.addLayout(file_hl)
        hint_lbl = QLabel("Định dạng hỗ trợ: .csv (UTF-8 / UTF-8 BOM) và .xlsx")
        hint_lbl.setObjectName("muted_label")
        file_vl.addWidget(hint_lbl)
        layout.addWidget(file_group)

        # Step 2 – Bank selector
        bank_group = QGroupBox("Bước 2 – Chọn ngân hàng câu hỏi đích")
        bank_vl = QVBoxLayout(bank_group)
        bank_hl = QHBoxLayout()
        self._bank_combo = QComboBox()
        self._bank_combo.setMinimumWidth(240)
        self._bank_combo.currentIndexChanged.connect(self._update_preview_btn)
        new_bank_btn = QPushButton("＋ Tạo ngân hàng mới")
        new_bank_btn.clicked.connect(self._create_bank)
        bank_hl.addWidget(self._bank_combo, stretch=1)
        bank_hl.addWidget(new_bank_btn)
        bank_vl.addLayout(bank_hl)
        layout.addWidget(bank_group)

        # Action row
        action_hl = QHBoxLayout()
        self._preview_btn = QPushButton("🔍  Xem trước và kiểm tra file")
        self._preview_btn.setEnabled(False)
        self._preview_btn.setStyleSheet(
            "font-size: 15px; padding: 8px 28px; font-weight: bold;"
        )
        self._preview_btn.clicked.connect(self._on_preview)
        action_hl.addStretch()
        action_hl.addWidget(self._preview_btn)
        layout.addLayout(action_hl)

        # Status label
        self._status_lbl = QLabel("")
        self._status_lbl.setObjectName("muted_label")
        layout.addWidget(self._status_lbl)

        layout.addStretch()

        # Template download link
        tmpl_lbl = QLabel(
            'Tải template mẫu: <a href="#csv">questions_template.csv</a>'
        )
        tmpl_lbl.setTextFormat(Qt.TextFormat.RichText)
        tmpl_lbl.linkActivated.connect(self._export_template)
        layout.addWidget(tmpl_lbl)

    # ------------------------------------------------------------------
    # Data helpers
    # ------------------------------------------------------------------

    def _load_banks(self) -> None:
        """Reload bank combo from DB."""
        try:
            self._banks = self._facade.load_banks()
        except (DatabaseError, QuizAppError) as exc:
            self._status_lbl.setText(
                f"Lỗi tải ngân hàng câu hỏi: {map_exception_to_user_message(exc)}"
            )
            self._banks = []
        except Exception as exc:
            self._status_lbl.setText(
                f"Lỗi tải ngân hàng câu hỏi: {map_exception_to_user_message(exc)}"
            )
            self._banks = []

        self._bank_combo.blockSignals(True)
        self._bank_combo.clear()
        if self._banks:
            for bank_id, bank_name in self._banks:
                self._bank_combo.addItem(bank_name, userData=bank_id)
        else:
            self._bank_combo.addItem(
                "(Chưa có ngân hàng – hãy tạo mới)", userData=None
            )
        self._bank_combo.blockSignals(False)
        self._update_preview_btn()

    def _update_preview_btn(self) -> None:
        has_file = self._file_path is not None and self._file_path.exists()
        has_bank = self._bank_combo.currentData() is not None
        self._preview_btn.setEnabled(has_file and has_bank)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _browse_file(self) -> None:
        path_str, _ = QFileDialog.getOpenFileName(
            self,
            "Chọn file import câu hỏi",
            "",
            "File câu hỏi (*.csv *.xlsx);;CSV files (*.csv);;Excel files (*.xlsx)",
        )
        if path_str:
            self._file_path = Path(path_str)
            self._file_edit.setText(path_str)
            self._status_lbl.setText("")
            self._update_preview_btn()

    def _create_bank(self) -> None:
        name, ok = QInputDialog.getText(
            self,
            "Tạo ngân hàng câu hỏi",
            "Tên ngân hàng:",
        )
        if not ok or not name.strip():
            return
        name = name.strip()
        try:
            new_id = self._facade.create_bank(name)
            self._load_banks()
            # Select the newly created bank
            for i in range(self._bank_combo.count()):
                if self._bank_combo.itemData(i) == new_id:
                    self._bank_combo.setCurrentIndex(i)
                    break
        except Exception as exc:
            show_critical_error(self, "Lỗi", "Không thể tạo ngân hàng.", exc=exc)

    def _on_preview(self) -> None:
        if not self._file_path:
            return
        bank_id = self._bank_combo.currentData()
        if bank_id is None:
            QMessageBox.warning(
                self,
                "Chưa chọn ngân hàng",
                "Vui lòng chọn hoặc tạo ngân hàng câu hỏi trước.",
            )
            return

        self._status_lbl.setText("Đang phân tích file…")
        self._preview_btn.setEnabled(False)

        try:
            parse_result = self._facade.preview_file(self._file_path)
        except (ImportError, DatabaseError, QuizAppError) as exc:
            self._status_lbl.setText("Lỗi khi đọc file import.")
            show_critical_error(self, "Lỗi import", "Không thể phân tích file.", exc=exc)
            self._preview_btn.setEnabled(True)
            return
        except Exception as exc:
            self._status_lbl.setText("Lỗi hệ thống khi đọc file import.")
            show_critical_error(self, "Lỗi import", "Không thể phân tích file.", exc=exc)
            self._preview_btn.setEnabled(True)
            return

        dlg = ImportPreviewDialog(
            parse_result,
            bank_id,
            self._file_path,
            facade=self._facade,
            parent=self,
        )
        dlg.exec()

        if dlg.was_imported:
            self._status_lbl.setText(
                f"✓ Import hoàn thành từ {self._file_path.name}. "
                "Xem kết quả trong Ngân hàng câu hỏi."
            )
        else:
            self._status_lbl.setText("Import đã hủy hoặc bị chặn do lỗi.")

        self._preview_btn.setEnabled(True)

    def _export_template(self, _link: str = "") -> None:
        """Save an example CSV template to a user-chosen path."""
        path_str, _ = QFileDialog.getSaveFileName(
            self, "Lưu file template", "questions_template.csv", "CSV files (*.csv)"
        )
        if not path_str:
            return

        header = (
            "question_code,question_text,question_type,category,difficulty,score,"
            "hint,explanation,option_a,option_b,option_c,option_d,option_e,option_f,"
            "correct_answers,status,tags,case_sensitive,trim_whitespace\n"
        )
        examples = (
            # Multiple Choice example
            "MC001,Thủ đô của Việt Nam là gì?,multiple_choice,Địa lý,easy,1,"
            "Gợi ý: trung tâm chính trị,Đáp án: Hà Nội,"
            "Hà Nội,Hồ Chí Minh,Đà Nẵng,Cần Thơ,,,A,active,địa lý,false,true\n"
            # Multiple Answer example
            "MA001,Những ngôn ngữ nào là kiểu thông dịch?,multiple_answer,CNTT,medium,1.5,"
            "Nghĩ đến Python, JS,,Python,Java,C++,JavaScript,,,A||D,active,cntt,false,true\n"
            # Blank example
            "BL001,Thủ đô của Việt Nam là [[blank]].,blank,Địa lý,easy,1,"
            "Gợi ý: bắt đầu bằng H,,,,,,,,Hà Nội||Ha Noi,active,địa lý,false,true\n"
            # Short Answer example
            "SA001,Viết tắt của Economic Order Quantity là gì?,short_answer,Logistics,easy,1,"
            "Gợi ý: 3 chữ cái,,,,,,,,EOQ||Economic Order Quantity,active,logistics,false,true\n"
        )
        Path(path_str).write_text(header + examples, encoding="utf-8-sig")
        QMessageBox.information(self, "Template đã lưu", f"Template đã được lưu:\n{path_str}")

    def refresh(self) -> None:
        """Public refresh entrypoint for MainWindow F5 contract."""
        self._load_banks()
        self._update_preview_btn()
