"""Màn Ngân hàng câu hỏi - CRUD cho ngân hàng và câu hỏi, tìm kiếm, lọc.

Layout:
  Left panel  : danh sách ngân hàng với các nút CRUD
  Right panel : bảng câu hỏi với thanh công cụ (thêm, sửa, xóa, tìm kiếm, lọc)

Business rules in ARCHITECTURE §5.1 are enforced by QuestionService; this
file only orchestrates UI interactions.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.database.models import Question
from core.utils.constants import QuestionType
from core.utils.logger import get_logger
from ui.dialogs.bank_meta_dialog import BankMetaDialog
from ui.dialogs.question_editor_dialog import QuestionEditorDialog
from ui.facades.question_bank_facade import BankMetaData, QuestionBankFacade
from ui.utils.error_handler import show_critical_error

_logger = get_logger(__name__)

_TYPE_LABEL = {
    "MC": "Trắc nghiệm 1 đáp án",
    "MA": "Trắc nghiệm nhiều đáp án",
    "TF": "Đúng/Sai",
    "BLANK": "Điền vào chỗ trống",
    "SA": "Trả lời ngắn",
    "ES": "Tự luận",
}
_TYPE_TABLE_LABEL = {
    "MC": "MC",
    "MA": "MA",
    "TF": "T/F",
    "BLANK": "Blank",
    "SA": "SA",
    "ES": "ES",
}
_QUESTION_LEVELS: tuple[str, ...] = (
    "Nhớ",
    "Hiểu",
    "Vận dụng",
    "Phân tích",
    "Đánh giá",
    "Sáng tạo",
)
_LEGACY_DIFFICULTY_TO_LEVEL: dict[str, str] = {
    "easy": "Nhớ",
    "medium": "Hiểu",
    "hard": "Vận dụng",
}


class QuestionBankView(QWidget):
    """Quản lý ngân hàng câu hỏi - CRUD, tìm kiếm, lọc."""

    refresh_requested = Signal()   # emitted when user clicks 'Cập nhật'

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._facade = QuestionBankFacade()
        self._current_bank_id: int | None = None
        self._questions: list[Question] = []
        self._loaded: bool = False
        self._build_ui()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        if not self._loaded:
            self._loaded = True
            self._load_banks()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Ngân hàng câu hỏi")
        title.setObjectName("view_title")
        root.addWidget(title)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(splitter, stretch=1)

        splitter.addWidget(self._build_bank_panel())
        splitter.addWidget(self._build_question_panel())
        splitter.setSizes([220, 720])

    # ── Left: bank list ─────────────────────────────────────────────

    def _build_bank_panel(self) -> QWidget:
        w = QWidget()
        vl = QVBoxLayout(w)
        vl.setContentsMargins(8, 4, 4, 8)
        vl.setSpacing(6)

        hdr = QLabel("<b>Ngân hàng</b>")
        vl.addWidget(hdr)

        self._bank_list = QListWidget()
        self._bank_list.currentItemChanged.connect(self._on_bank_selected)
        vl.addWidget(self._bank_list, stretch=1)

        btn_hl = QHBoxLayout()
        add_btn = QPushButton("+ Thêm")
        add_btn.setToolTip("Thêm ngân hàng mới")
        add_btn.clicked.connect(self._add_bank)
        rename_btn = QPushButton("Sửa")
        rename_btn.setToolTip("Đổi tên ngân hàng")
        rename_btn.clicked.connect(self._rename_bank)
        del_btn = QPushButton("Xóa")
        del_btn.setToolTip("Xóa ngân hàng")
        del_btn.clicked.connect(self._delete_bank)
        add_btn.setFixedWidth(80)
        for b in (rename_btn, del_btn):
            b.setFixedWidth(58)
        btn_hl.addWidget(add_btn)
        btn_hl.addWidget(rename_btn)
        btn_hl.addWidget(del_btn)
        btn_hl.addStretch()
        vl.addLayout(btn_hl)
        return w

    # ── Right: question table ────────────────────────────────────────

    def _build_question_panel(self) -> QWidget:
        w = QWidget()
        vl = QVBoxLayout(w)
        vl.setContentsMargins(4, 4, 8, 8)
        vl.setSpacing(6)

        # Toolbar row
        tb_hl = QHBoxLayout()

        add_q_btn = QPushButton("+ Thêm câu hỏi")
        add_q_btn.clicked.connect(self._add_question)
        edit_q_btn = QPushButton("Sửa")
        edit_q_btn.clicked.connect(self._edit_question)
        del_q_btn = QPushButton("Xóa")
        del_q_btn.clicked.connect(self._delete_questions)
        refresh_btn = QPushButton("Cập nhật")
        refresh_btn.setToolTip("Làm mới dữ liệu ngân hàng và đồng bộ với Tạo bài kiểm tra")
        refresh_btn.clicked.connect(self._on_refresh_clicked)

        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("Tìm kiếm câu hỏi…")
        self._search_edit.setMinimumWidth(180)
        self._search_edit.textChanged.connect(self._refresh_questions)

        self._type_filter = QComboBox()
        self._type_filter.addItem("Tất cả loại câu hỏi", userData=None)
        for qt in QuestionType:
            self._type_filter.addItem(_TYPE_LABEL.get(qt.value, qt.value), userData=qt.value)
        self._type_filter.currentIndexChanged.connect(self._refresh_questions)

        self._diff_filter = QComboBox()
        self._diff_filter.addItem("Tất cả mức độ", userData=None)
        for level in _QUESTION_LEVELS:
            self._diff_filter.addItem(level, userData=level)
        self._diff_filter.currentIndexChanged.connect(self._refresh_questions)

        tb_hl.addWidget(add_q_btn)
        tb_hl.addWidget(edit_q_btn)
        tb_hl.addWidget(del_q_btn)
        tb_hl.addWidget(refresh_btn)
        tb_hl.addStretch()
        tb_hl.addWidget(QLabel("🔍"))
        tb_hl.addWidget(self._search_edit)
        tb_hl.addWidget(self._type_filter)
        tb_hl.addWidget(self._diff_filter)
        vl.addLayout(tb_hl)

        # Table
        self._q_table = QTableWidget(0, 9)
        self._q_table.setHorizontalHeaderLabels(
            ["STT", "Mã", "Nội dung", "Chương", "CLO", "Mức độ", "Loại", "Điểm", "Trạng thái"]
        )
        self._q_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self._q_table.horizontalHeader().setDefaultSectionSize(90)
        self._q_table.setColumnWidth(0, 44)
        self._q_table.setColumnWidth(1, 82)
        self._q_table.setColumnWidth(3, 78)
        self._q_table.setColumnWidth(4, 96)
        self._q_table.setColumnWidth(5, 82)
        self._q_table.setColumnWidth(6, 84)
        self._q_table.setColumnWidth(7, 54)
        self._q_table.setColumnWidth(8, 100)
        self._q_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._q_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._q_table.setAlternatingRowColors(True)
        self._q_table.setWordWrap(True)
        self._q_table.setTextElideMode(Qt.TextElideMode.ElideRight)
        self._q_table.verticalHeader().setVisible(False)
        self._q_table.verticalHeader().setDefaultSectionSize(58)
        self._q_table.verticalHeader().setMinimumSectionSize(54)
        self._q_table.horizontalHeader().setSortIndicatorShown(True)
        self._q_table.setSortingEnabled(True)
        self._q_table.doubleClicked.connect(self._edit_question)
        vl.addWidget(self._q_table, stretch=1)

        self._status_lbl = QLabel("")
        self._status_lbl.setObjectName("muted_label")
        vl.addWidget(self._status_lbl)
        return w

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def _load_banks(self) -> None:
        prev_bank_id = self._current_bank_id
        self._bank_list.blockSignals(True)
        self._bank_list.clear()
        try:
            bank_data = self._facade.list_bank_overview_items()
        except Exception:
            bank_data = []
        for row in bank_data:
            item = QListWidgetItem(
                f"{row['name']}\n{self._format_bank_context(row)}"
            )
            item.setData(Qt.ItemDataRole.UserRole, row["id"])
            item.setData(Qt.ItemDataRole.UserRole + 1, row["name"])
            item.setData(Qt.ItemDataRole.UserRole + 2, self._format_bank_context(row))
            item.setToolTip(self._format_bank_tooltip(row))
            self._bank_list.addItem(item)
        self._bank_list.blockSignals(False)

        # Restore selection
        restored = False
        if prev_bank_id is not None:
            for i in range(self._bank_list.count()):
                if self._bank_list.item(i).data(Qt.ItemDataRole.UserRole) == prev_bank_id:
                    self._bank_list.setCurrentRow(i)
                    restored = True
                    break
        if not restored and self._bank_list.count() > 0:
            self._bank_list.setCurrentRow(0)

    def _on_bank_selected(self, current: QListWidgetItem | None, _prev) -> None:
        if current is None:
            self._current_bank_id = None
            self._questions = []
            self._populate_table([])
            return
        self._current_bank_id = current.data(Qt.ItemDataRole.UserRole)
        self._refresh_questions()

    def _refresh_questions(self) -> None:
        search = self._search_edit.text()
        qtype = self._type_filter.currentData()
        diff = self._diff_filter.currentData()
        try:
            self._questions = self._facade.list_questions(
                bank_id=self._current_bank_id,
                search=search,
                question_type=qtype,
                difficulty=diff,
            )
        except Exception as exc:
            _logger.error(f"_refresh_questions failed: {exc}", exc_info=True)
            self._questions = []
        self._populate_table(self._questions)

    def _populate_table(self, questions: list[Question]) -> None:
        self._q_table.setSortingEnabled(False)  # disable during populate to avoid Qt sort-insert bug
        self._q_table.setRowCount(len(questions))
        for r, q in enumerate(questions):
            self._q_table.setItem(r, 0, _cell(str(r + 1), center=True))
            self._q_table.setItem(r, 1, _cell(q.question_code or ""))
            preview = (q.content or "")[:180]
            content_item = _cell(preview)
            content_item.setToolTip(q.content or "")
            self._q_table.setItem(r, 2, content_item)
            self._q_table.setItem(
                r, 3, _cell(q.category or "", center=True)
            )
            self._q_table.setItem(
                r, 4, _cell(q.learning_outcome_code or "", center=True)
            )
            self._q_table.setItem(
                r, 5, _cell(self._display_level(q.difficulty), center=True)
            )
            self._q_table.setItem(
                r, 6, _cell(_TYPE_TABLE_LABEL.get(q.question_type, q.question_type), center=True)
            )
            self._q_table.setItem(r, 7, _cell(str(q.point_value or 1.0), center=True))
            # Trạng thái
            if q.is_active:
                status_item = _cell("✓ Đang dùng", center=True)
                status_item.setForeground(QColor("#27ae60"))   # green
            else:
                status_item = _cell("✗ Không dùng", center=True)
                status_item.setForeground(QColor("#c0392b"))
            status_item.setToolTip(status_item.text())
            self._q_table.setItem(r, 8, status_item)
            # Store question id in column 0 (displayed as STT)
            self._q_table.item(r, 0).setData(
                Qt.ItemDataRole.UserRole, q.id
            )
        bank_label = ""
        if self._current_bank_id:
            item = self._bank_list.currentItem()
            if item:
                bank_label = f"「{item.data(Qt.ItemDataRole.UserRole + 1) or item.text()}」 – "
        self._status_lbl.setText(
            f"{bank_label}{len(questions)} câu hỏi"
            + (" (đang lọc)" if self._search_edit.text()
               or self._type_filter.currentData()
               or self._diff_filter.currentData()
               else "")
        )
        self._q_table.setSortingEnabled(True)

    # ------------------------------------------------------------------
    # Bank CRUD slots
    # ------------------------------------------------------------------

    def _add_bank(self) -> None:
        dlg = BankMetaDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        data = dlg.get_data()
        if not data["name"]:
            return
        try:
            new_id = self._facade.create_bank(
                BankMetaData(
                    name=data["name"],
                    school=data["school"],
                    department=data["department"],
                    subject=data["subject"],
                    course_code=data["course_code"],
                    exam_title=data["exam_title"],
                    assessment_type=data["assessment_type"],
                    course_learning_outcomes=data["course_learning_outcomes"],
                )
            )
            self._load_banks()
            # Select new
            for i in range(self._bank_list.count()):
                if self._bank_list.item(i).data(Qt.ItemDataRole.UserRole) == new_id:
                    self._bank_list.setCurrentRow(i)
                    break
        except ValueError as exc:
            QMessageBox.warning(self, "Lỗi", str(exc))

    def _rename_bank(self) -> None:
        item = self._bank_list.currentItem()
        if item is None:
            QMessageBox.information(self, "Thông báo", "Chưa chọn ngân hàng.")
            return
        bid = item.data(Qt.ItemDataRole.UserRole)
        # Load current bank metadata for pre-filling
        try:
            bank = self._facade.get_bank_metadata(bid)
            if bank is None:
                QMessageBox.warning(self, "Lỗi", "Không tìm thấy ngân hàng.")
                return
            initial = {
                "name": bank.name,
                "school": bank.school,
                "department": bank.department,
                "subject": bank.subject,
                "course_code": bank.course_code,
                "exam_title": bank.exam_title,
                "assessment_type": bank.assessment_type,
                "course_learning_outcomes": bank.course_learning_outcomes,
            }
        except Exception as exc:
            show_critical_error(self, "Lỗi", "Không thể tải thông tin ngân hàng.", exc=exc)
            return
        dlg = BankMetaDialog(self, initial_data=initial, edit_mode=True)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        data = dlg.get_data()
        if not data["name"]:
            return
        try:
            self._facade.update_bank(
                bid,
                BankMetaData(
                    name=data["name"],
                    school=data["school"],
                    department=data["department"],
                    subject=data["subject"],
                    course_code=data["course_code"],
                    exam_title=data["exam_title"],
                    assessment_type=data["assessment_type"],
                    course_learning_outcomes=data["course_learning_outcomes"],
                ),
            )
            self._load_banks()
        except ValueError as exc:
            QMessageBox.warning(self, "Lỗi", str(exc))

    def _delete_bank(self) -> None:
        item = self._bank_list.currentItem()
        if item is None:
            QMessageBox.information(self, "Thông báo", "Chưa chọn ngân hàng.")
            return
        bid = item.data(Qt.ItemDataRole.UserRole)
        name = item.data(Qt.ItemDataRole.UserRole + 1) or item.text()
        ans = QMessageBox.question(
            self,
            "Xác nhận xóa ngân hàng",
            f"Xóa ngân hàng «{name}»?\n\nTất cả câu hỏi bên trong cũng sẽ bị xóa. Không thể hoàn tác.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ans != QMessageBox.StandardButton.Yes:
            return
        try:
            self._facade.delete_bank(bid)
            self._current_bank_id = None
            self._load_banks()
        except ValueError as exc:
            QMessageBox.warning(self, "Lỗi", str(exc))

    # ------------------------------------------------------------------
    # Question CRUD slots
    # ------------------------------------------------------------------

    def _add_question(self) -> None:
        if self._current_bank_id is None:
            QMessageBox.information(
                self, "Thông báo", "Vui lòng chọn ngân hàng trước."
            )
            return
        dlg = QuestionEditorDialog(self._current_bank_id, parent=self)
        if dlg.exec() == QuestionEditorDialog.DialogCode.Accepted:
            self._refresh_questions()

    def _edit_question(self) -> None:
        q = self._selected_question()
        if q is None:
            return
        dlg = QuestionEditorDialog(self._current_bank_id or q.bank_id, q, parent=self)
        if dlg.exec() == QuestionEditorDialog.DialogCode.Accepted:
            self._refresh_questions()

    def _delete_questions(self) -> None:
        ids = self._selected_question_ids()
        if not ids:
            QMessageBox.information(self, "Thông báo", "Chưa chọn câu hỏi nào.")
            return
        ans = QMessageBox.question(
            self,
            "Xác nhận xóa câu hỏi",
            f"Xóa {len(ids)} câu hỏi đã chọn? Không thể hoàn tác.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ans != QMessageBox.StandardButton.Yes:
            return
        try:
            deleted = self._facade.delete_questions_bulk(ids)
            self._refresh_questions()
            QMessageBox.information(self, "Đã xóa", f"Đã xóa {deleted} câu hỏi.")
        except Exception as exc:
            show_critical_error(self, "Lỗi", "Không thể xóa câu hỏi đã chọn.", exc=exc)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _selected_question(self) -> Question | None:
        row = self._q_table.currentRow()
        if row < 0 or row >= len(self._questions):
            QMessageBox.information(self, "Thông báo", "Chưa chọn câu hỏi.")
            return None
        qid = self._q_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        try:
            return self._facade.get_question_for_edit(qid)
        except Exception as exc:
            _logger.error(f"_selected_question failed for id={qid}: {exc}")
            return None

    def _selected_question_ids(self) -> list[int]:
        rows = self._q_table.selectionModel().selectedRows()
        ids = []
        for idx in rows:
            item = self._q_table.item(idx.row(), 0)
            if item:
                ids.append(item.data(Qt.ItemDataRole.UserRole))
        return ids

    # ------------------------------------------------------------------
    # Public refresh (called from main window after import)
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        self._load_banks()

    def _on_refresh_clicked(self) -> None:
        """Reload bank data and notify quiz builder to sync."""
        self.refresh()
        self.refresh_requested.emit()

    def _format_bank_context(self, row: dict) -> str:
        assessment = str(row.get("assessment_type", "") or "").strip() or "Chưa chọn loại"
        clos = row.get("course_learning_outcomes", []) or []
        clo_codes = [str(item.get("code", "")).strip() for item in clos if str(item.get("code", "")).strip()]
        clo_text = ", ".join(clo_codes[:3]) if clo_codes else "Chưa gắn CLO"
        if len(clo_codes) > 3:
            clo_text = f"{clo_text}, +{len(clo_codes) - 3}"
        question_count = int(row.get("question_count", 0) or 0)
        return f"{assessment} | {clo_text} | {question_count} câu hỏi"

    def _format_bank_tooltip(self, row: dict) -> str:
        clos = row.get("course_learning_outcomes", []) or []
        clo_lines = [
            f"{str(item.get('code', '')).strip()}: {str(item.get('description', '')).strip()}"
            for item in clos
            if str(item.get("code", "")).strip()
        ]
        if not clo_lines:
            clo_lines = ["Chưa khai báo CLO"]
        return (
            f"Ngân hàng: {row.get('name', '')}\n"
            f"Loại đánh giá: {row.get('assessment_type', '') or 'Chưa chọn'}\n"
            f"Số câu hỏi: {int(row.get('question_count', 0) or 0)}\n"
            f"CLO:\n- " + "\n- ".join(clo_lines)
        )

    def _display_level(self, difficulty: str | None) -> str:
        raw = str(difficulty or "").strip()
        if not raw:
            return ""
        return _LEGACY_DIFFICULTY_TO_LEVEL.get(raw, raw)

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _cell(text: str, center: bool = False) -> QTableWidgetItem:
    item = QTableWidgetItem(text)
    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    if center:
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    return item
