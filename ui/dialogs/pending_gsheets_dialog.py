"""Dialog showing pending Google Sheets submissions and allowing retry/delete.

Opened from ResultHistoryView when the user clicks "Nộp lại GSheets".
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from modules.google_sheets.pending_queue import PendingGSheetsQueue


class PendingGSheetsDialog(QDialog):
    """Lists queued GSheets submissions with Retry and Delete actions."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Hàng chờ nộp Google Sheets")
        self.setMinimumSize(680, 380)
        self.setModal(True)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint
        )
        self._queue = PendingGSheetsQueue()
        self._build_ui()
        self._refresh()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        note = QLabel(
            "Danh sách bài chưa được ghi vào Google Sheets.\n"
            "Chọn một mục rồi nhấn Nộp lại hoặc Xóa."
        )
        note.setObjectName("muted_label")
        note.setWordWrap(True)
        layout.addWidget(note)

        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(
            ["Tên bài", "Học sinh", "Điểm", "Thời gian lưu", "URL Sheet"]
        )
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setColumnWidth(0, 160)
        self._table.setColumnWidth(1, 100)
        self._table.setColumnWidth(2, 80)
        self._table.setColumnWidth(3, 140)
        layout.addWidget(self._table)

        # Action buttons
        btn_row = QHBoxLayout()

        self._btn_retry = QPushButton("▶  Nộp lại")
        self._btn_retry.setFixedHeight(34)
        self._btn_retry.setEnabled(False)
        self._btn_retry.clicked.connect(self._on_retry)
        btn_row.addWidget(self._btn_retry)

        self._btn_delete = QPushButton("✕  Xóa")
        self._btn_delete.setFixedHeight(34)
        self._btn_delete.setEnabled(False)
        self._btn_delete.clicked.connect(self._on_delete)
        btn_row.addWidget(self._btn_delete)

        btn_row.addStretch()

        self._lbl_count = QLabel("")
        self._lbl_count.setObjectName("muted_label")
        btn_row.addWidget(self._lbl_count)
        layout.addLayout(btn_row)

        # Close button
        close_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_box.rejected.connect(self.reject)
        layout.addWidget(close_box)

        self._table.selectionModel().selectionChanged.connect(
            self._on_selection_changed
        )

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def _refresh(self) -> None:
        items = self._queue.get_all()
        self._table.setRowCount(0)

        for row_idx, item in enumerate(items):
            self._table.insertRow(row_idx)
            score_str = (
                f"{item.score:.1f}/{item.max_score:.1f}"
                if item.max_score > 0
                else "—"
            )
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(item.queued_at)
                dt_local = dt.astimezone()
                ts = dt_local.strftime("%d/%m/%Y %H:%M")
            except Exception:
                ts = item.queued_at

            cells = [
                item.quiz_title,
                item.submitter_name,
                score_str,
                ts,
                item.gsheets_url,
            ]
            for col, text in enumerate(cells):
                cell = QTableWidgetItem(text)
                cell.setData(Qt.ItemDataRole.UserRole, item.item_id)
                self._table.setItem(row_idx, col, cell)

        self._lbl_count.setText(f"Đang chờ: {len(items)} mục")
        self._btn_retry.setEnabled(False)
        self._btn_delete.setEnabled(False)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_selection_changed(self) -> None:
        has_sel = bool(self._table.selectedItems())
        self._btn_retry.setEnabled(has_sel)
        self._btn_delete.setEnabled(has_sel)

    def _current_item_id(self) -> str | None:
        row = self._table.currentRow()
        if row < 0:
            return None
        cell = self._table.item(row, 0)
        return cell.data(Qt.ItemDataRole.UserRole) if cell else None

    def _on_retry(self) -> None:
        item_id = self._current_item_id()
        if not item_id:
            return

        self._btn_retry.setEnabled(False)
        self._btn_retry.setText("Đang nộp…")
        try:
            self._queue.retry_one(item_id)
            QMessageBox.information(self, "Thành công", "Đã ghi vào Google Sheets thành công!")
            self._refresh()
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Nộp lại thất bại",
                f"Không thể ghi vào Google Sheets:\n{exc}",
            )
        finally:
            self._btn_retry.setText("▶  Nộp lại")
            row = self._table.currentRow()
            self._btn_retry.setEnabled(row >= 0)

    def _on_delete(self) -> None:
        item_id = self._current_item_id()
        if not item_id:
            return

        reply = QMessageBox.question(
            self,
            "Xác nhận xóa",
            "Xóa mục này khỏi hàng chờ?\nDữ liệu sẽ bị mất vĩnh viễn.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._queue.remove(item_id)
            self._refresh()
