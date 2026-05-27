"""Result History View – list and detail of quiz attempt records."""
from __future__ import annotations

import os
from datetime import datetime

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.database.session import get_session
from core.domain.services.history_service import HistoryService
from modules.analytics.history_loader import load_attempts_and_pending_count
from ui.utils.error_handler import show_warning_error

_MODE_LABELS = {
    "EXAM": "Kiểm tra",
    "PRACTICE": "Luyện tập",
    "STUDY": "Học tập",
}
_STATUS_LABELS = {
    "IN_PROGRESS": "Đang làm",
    "SUBMITTED": "Đã nộp bài",
    "TIME_UP": "Hết giờ",
    "COMPLETED": "Hoàn thành",
}


class _HistoryLoadWorker(QObject):
    finished = Signal(object, int, object)

    def run(self) -> None:
        try:
            attempts, pending_count = load_attempts_and_pending_count()
            self.finished.emit(attempts, pending_count, None)
        except (RuntimeError, ValueError, OSError) as exc:  # pragma: no cover
            self.finished.emit([], 0, exc)
def _format_duration(seconds: int) -> str:
    """Return a human-readable duration string."""
    if seconds < 60:
        return f"{seconds} giây"
    m, s = divmod(int(seconds), 60)
    if m < 60:
        return f"{m} phút {s} giây" if s else f"{m} phút"
    h, m = divmod(m, 60)
    return f"{h} giờ {m} phút {s} giây" if s else f"{h} giờ {m} phút"
class ResultHistoryView(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._attempts: list[dict] = []
        self._refresh_thread: QThread | None = None
        self._refresh_worker: _HistoryLoadWorker | None = None
        self.destroyed.connect(self._stop_refresh_thread)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("Lịch sử làm bài")
        title.setObjectName("view_title")
        layout.addWidget(title)

        # Filter bar
        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)

        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("Tìm theo tên bài kiểm tra…")
        self._search_edit.setClearButtonEnabled(True)
        self._search_edit.textChanged.connect(self._apply_filter)

        self._mode_filter = QComboBox()
        self._mode_filter.addItem("Tất cả chế độ", None)
        for k, v in _MODE_LABELS.items():
            self._mode_filter.addItem(v, k)
        self._mode_filter.currentIndexChanged.connect(self._apply_filter)

        self._status_filter = QComboBox()
        self._status_filter.addItem("Tất cả trạng thái", None)
        for k, v in _STATUS_LABELS.items():
            self._status_filter.addItem(v, k)
        self._status_filter.currentIndexChanged.connect(self._apply_filter)

        clear_btn = QPushButton("✕ Bỏ lọc")
        clear_btn.setMinimumWidth(104)
        clear_btn.setToolTip("Xóa tất cả bộ lọc")
        clear_btn.clicked.connect(self._clear_filter)

        filter_row.addWidget(self._search_edit, stretch=1)
        filter_row.addWidget(self._mode_filter)
        filter_row.addWidget(self._status_filter)
        filter_row.addWidget(clear_btn)
        layout.addLayout(filter_row)

        # Attempt table
        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels(
            ["#", "Tên bài kiểm tra", "Chế độ", "Trạng thái", "Điểm", "Ngày làm"]
        )
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self._table.horizontalHeader().setSortIndicatorShown(True)
        self._table.setSortingEnabled(True)
        self._table.setColumnWidth(0, 40)
        self._table.setColumnWidth(2, 90)
        self._table.setColumnWidth(3, 100)
        self._table.setColumnWidth(4, 120)
        self._table.doubleClicked.connect(self._on_detail_clicked)
        layout.addWidget(self._table)

        # Button row
        btn_row = QHBoxLayout()

        self._btn_refresh = QPushButton("Làm mới")
        self._btn_refresh.setFixedHeight(34)
        self._btn_refresh.clicked.connect(self.refresh)
        btn_row.addWidget(self._btn_refresh)

        self._btn_detail = QPushButton("Xem chi tiết")
        self._btn_detail.setFixedHeight(34)
        self._btn_detail.setEnabled(False)
        self._btn_detail.clicked.connect(self._on_detail_clicked)
        btn_row.addWidget(self._btn_detail)

        self._btn_delete = QPushButton("Xóa bài làm")
        self._btn_delete.setFixedHeight(34)
        self._btn_delete.setEnabled(False)
        self._btn_delete.clicked.connect(self._on_delete_clicked)
        btn_row.addWidget(self._btn_delete)

        self._btn_pending_gsheets = QPushButton("Nộp lại GSheets")
        self._btn_pending_gsheets.setFixedHeight(34)
        self._btn_pending_gsheets.setToolTip(
            "Mở hàng chờ nộp Google Sheets — danh sách bài chưa ghi được vào Sheet"
        )
        self._btn_pending_gsheets.clicked.connect(self._on_pending_gsheets_clicked)
        btn_row.addWidget(self._btn_pending_gsheets)

        btn_row.addStretch()

        self._lbl_count = QLabel("")
        self._lbl_count.setObjectName("muted_label")
        btn_row.addWidget(self._lbl_count)
        layout.addLayout(btn_row)

        self._table.selectionModel().selectionChanged.connect(
            self._on_selection_changed
        )

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self.refresh()

    def closeEvent(self, event) -> None:  # noqa: N802
        self._stop_refresh_thread()
        super().closeEvent(event)

    def _stop_refresh_thread(self) -> None:
        if self._refresh_thread is not None and self._refresh_thread.isRunning():
            self._refresh_thread.quit()
            self._refresh_thread.wait(1000)

    def _refresh(self) -> None:
        if "PYTEST_CURRENT_TEST" in os.environ:
            try:
                self._attempts, n = load_attempts_and_pending_count()
                self._set_pending_count_label(n)
            except (RuntimeError, ValueError, OSError) as exc:
                show_warning_error(self, "Lỗi", "Không thể tải lịch sử.", exc=exc)
                self._attempts = []
                self._set_pending_count_label(0)
            self._apply_filter()
            return

        if self._refresh_thread is not None and self._refresh_thread.isRunning():
            return

        self._btn_refresh.setEnabled(False)
        self._lbl_count.setText("Đang tải lịch sử...")

        self._refresh_thread = QThread()
        self._refresh_worker = _HistoryLoadWorker()
        self._refresh_worker.moveToThread(self._refresh_thread)
        self._refresh_thread.started.connect(self._refresh_worker.run)
        self._refresh_worker.finished.connect(self._on_refresh_finished)
        self._refresh_worker.finished.connect(self._refresh_thread.quit)
        self._refresh_worker.finished.connect(self._refresh_worker.deleteLater)
        self._refresh_thread.finished.connect(self._on_refresh_thread_finished)
        self._refresh_thread.finished.connect(self._refresh_thread.deleteLater)
        self._refresh_thread.start()

    def _on_refresh_finished(
        self,
        attempts: object,
        pending_count: int,
        error: object | None,
    ) -> None:
        self._btn_refresh.setEnabled(True)

        if error is not None:
            show_warning_error(self, "Lỗi", "Không thể tải lịch sử.", exc=error)
            self._attempts = []
            self._set_pending_count_label(0)
        else:
            self._attempts = attempts if isinstance(attempts, list) else []
            self._set_pending_count_label(pending_count)

        self._apply_filter()

    def _on_refresh_thread_finished(self) -> None:
        """Clear thread/worker references only after thread has fully stopped."""
        self._refresh_worker = None
        self._refresh_thread = None

    def _refresh_pending_count(self) -> None:
        """Update the 'Nộp lại GSheets' button label with pending queue count."""
        try:
            from modules.google_sheets.pending_queue import PendingGSheetsQueue
            n = PendingGSheetsQueue().count()
        except Exception:
            n = 0
        self._set_pending_count_label(n)

    def _set_pending_count_label(self, count: int) -> None:
        """Render pending count text for the queue button."""
        n = max(0, int(count))
        label = f"Nộp lại GSheets ({n})" if n > 0 else "Nộp lại GSheets"
        self._btn_pending_gsheets.setText(label)

    def refresh(self) -> None:
        """Public interface for the Refreshable protocol (F5 shortcut)."""
        self._refresh()

    def _apply_filter(self) -> None:
        """Filter self._attempts by current search/mode/status inputs."""
        search = self._search_edit.text().strip().lower()
        mode = self._mode_filter.currentData()
        status = self._status_filter.currentData()

        filtered = []
        for a in self._attempts:
            if search and search not in a["quiz_title"].lower():
                continue
            if mode and a["mode"] != mode:
                continue
            if status and a["status"] != status:
                continue
            filtered.append(a)

        self._populate_table(filtered)
        total = len(self._attempts)
        shown = len(filtered)
        if shown < total:
            self._lbl_count.setText(f"Hiển thị {shown}/{total} bài")
        else:
            self._lbl_count.setText(f"Tổng: {total} bài")

    def _clear_filter(self) -> None:
        self._search_edit.blockSignals(True)
        self._mode_filter.blockSignals(True)
        self._status_filter.blockSignals(True)
        self._search_edit.clear()
        self._mode_filter.setCurrentIndex(0)
        self._status_filter.setCurrentIndex(0)
        self._search_edit.blockSignals(False)
        self._mode_filter.blockSignals(False)
        self._status_filter.blockSignals(False)
        self._apply_filter()

    def _populate_table(self, attempts: list[dict]) -> None:
        self._table.setSortingEnabled(False)  # disable during populate to avoid Qt sort-insert bug
        self._table.setUpdatesEnabled(False)
        self._table.setRowCount(len(attempts))
        for row_idx, a in enumerate(attempts):

            score_str = (
                f"{a['score']:.1f}/{a['max_score']:.1f} ({a['score_pct']}%)"
                if a["max_score"] > 0
                else "—"
            )
            started = a["started_at"]
            date_str = (
                started.strftime("%d/%m/%Y %H:%M")
                if isinstance(started, datetime)
                else str(started or "—")
            )
            values = [
                str(row_idx + 1),
                a["quiz_title"],
                _MODE_LABELS.get(a["mode"], a["mode"]),
                _STATUS_LABELS.get(a["status"], a["status"]),
                score_str,
                date_str,
            ]
            for col, v in enumerate(values):
                item = QTableWidgetItem(v)
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
                )
                if col in (0, 2, 3, 4):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                # Store the attempt id in the first column item for retrieval
                item.setData(Qt.ItemDataRole.UserRole, a["id"])
                self._table.setItem(row_idx, col, item)

        self._btn_detail.setEnabled(False)
        self._btn_delete.setEnabled(False)
        self._table.setUpdatesEnabled(True)
        self._table.setSortingEnabled(True)

    def _on_selection_changed(self) -> None:
        selected = bool(self._table.selectedItems())
        self._btn_detail.setEnabled(selected)
        self._btn_delete.setEnabled(selected)

    def _selected_attempt_id(self) -> int | None:
        row = self._table.currentRow()
        if row < 0:
            return None
        item = self._table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _on_detail_clicked(self) -> None:
        attempt_id = self._selected_attempt_id()
        if attempt_id is None:
            return
        try:
            with get_session() as session:
                data = HistoryService.get_attempt_detail(session, attempt_id)
        except Exception as exc:
            show_warning_error(self, "Lỗi", "Không thể tải chi tiết.", exc=exc)
            return
        if data is None:
            QMessageBox.warning(self, "Lỗi", "Không tìm thấy bài làm.")
            return
        dlg = AttemptDetailDialog(data, parent=self)
        dlg.exec()

    def _on_delete_clicked(self) -> None:
        attempt_id = self._selected_attempt_id()
        if attempt_id is None:
            return
        row = self._table.currentRow()
        quiz_title_item = self._table.item(row, 1)
        quiz_title = quiz_title_item.text() if quiz_title_item else "?"
        confirm = QMessageBox.question(
            self,
            "Xác nhận xóa",
            f"Xóa bài làm\n«{quiz_title}»?\n\nThao tác này không thể hoàn tác.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            with get_session() as session:
                HistoryService.delete_attempt(session, attempt_id)
        except Exception as exc:
            show_warning_error(self, "Lỗi", "Không thể xóa bài làm.", exc=exc)
            return
        self.refresh()

    def _on_pending_gsheets_clicked(self) -> None:
        """Open the pending GSheets queue dialog."""
        from ui.dialogs.pending_gsheets_dialog import PendingGSheetsDialog
        dlg = PendingGSheetsDialog(parent=self)
        dlg.exec()
        # Refresh button count after user may have retried/deleted items
        self._refresh_pending_count()
class AttemptDetailDialog(QDialog):
    """Shows attempt detail; presentation varies by mode.

    EXAM     – summary stats only; per-question table NOT shown.
    PRACTICE – summary totals (correct / wrong / skipped).
    STUDY    – per-question table with ✓ / ✗ / – per row.

    ARCHITECTURE §5.5 compliance.
    """

    def __init__(self, data: dict, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._data = data
        self.setWindowTitle(f"Chi tiết: {data['quiz_title']}")
        self.setMinimumWidth(580)
        self.setMinimumHeight(300)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        mode = self._data["mode"]
        mode_label = _MODE_LABELS.get(mode, mode)
        status_label = _STATUS_LABELS.get(self._data["status"], self._data["status"])
        score = self._data["score"]
        max_score = self._data["max_score"]
        score_str = (
            f"{score:.1f}/{max_score:.1f} ({self._data['score_pct']}%)"
            if max_score > 0
            else "—"
        )
        dur = self._data.get("duration_seconds")
        dur_str = _format_duration(dur) if dur else "—"

        def _row(html: str) -> None:
            lbl = QLabel(html)
            lbl.setTextFormat(Qt.TextFormat.RichText)
            lbl.setWordWrap(True)
            layout.addWidget(lbl)

        _row(f"<b>Bài kiểm tra:</b> {self._data['quiz_title']}")
        _row(
            f"<b>Chế độ:</b> {mode_label}&nbsp;&nbsp;&nbsp;"
            f"<b>Trạng thái:</b> {status_label}"
        )
        _row(
            f"<b>Điểm:</b> {score_str}&nbsp;&nbsp;&nbsp;"
            f"<b>Thời gian làm:</b> {dur_str}"
        )
        _row(f"<b>Đã trả lời:</b> {self._data['answered_count']} câu")

        if mode != "EXAM":
            _row(
                f"<b>✓ Đúng:</b> {self._data['correct_count']}&nbsp;&nbsp;"
                f"<b>✗ Sai:</b> {self._data['incorrect_count']}&nbsp;&nbsp;"
                f"<b>– Bỏ qua:</b> {self._data['skipped_count']}"
            )

        # Per-question table only for STUDY
        if mode == "STUDY":
            layout.addWidget(self._build_answers_table())
        elif mode == "EXAM":
            note = QLabel(
                "<i>Chi tiết từng câu không được hiển thị trong chế độ Kiểm tra.</i>"
            )
            note.setTextFormat(Qt.TextFormat.RichText)
            note.setStyleSheet("color: #888;")
            layout.addWidget(note)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _build_answers_table(self) -> QTableWidget:
        answers = self._data.get("answers", [])
        tbl = QTableWidget(len(answers), 4)
        tbl.setHorizontalHeaderLabels(["#", "Nội dung câu hỏi", "Kết quả", "Điểm"])
        tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        tbl.verticalHeader().setVisible(False)
        tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        tbl.setAlternatingRowColors(True)
        tbl.setMinimumHeight(220)

        for row, aa in enumerate(answers):
            content = aa["question_content"]
            short = content[:60] + "…" if len(content) > 60 else content
            state = aa["feedback_state"]
            result_str = (
                "✓ Đúng" if state == "correct"
                else "✗ Sai" if state == "incorrect"
                else "– Bỏ qua"
            )
            cells = [
                str(aa["question_order"] + 1),
                short,
                result_str,
                f"{aa['score_awarded']:.1f}",
            ]
            for col, val in enumerate(cells):
                item = QTableWidgetItem(val)
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
                )
                if col in (0, 2, 3):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                tbl.setItem(row, col, item)
        return tbl
