"""Dashboard View – overview stat cards.

Displays: total banks, total questions, breakdown by type, recent banks.
All data fetched via QuestionService on show/refresh.
"""
from __future__ import annotations

import os

from PySide6.QtCore import QObject, QThread, QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ui.facades.dashboard_facade import DashboardFacade


class _DashboardOverviewWorker(QObject):
    """Load dashboard overview data in a background thread."""

    finished = Signal(object, object, object)

    def __init__(self, facade: DashboardFacade) -> None:
        super().__init__()
        self._facade = facade

    def run(self) -> None:
        try:
            overview = self._facade.load_overview()
            usage_banks = self._facade.load_usage_banks()
            self.finished.emit(overview, usage_banks, None)
        except (RuntimeError, ValueError, OSError) as exc:  # pragma: no cover
            self.finished.emit(None, [], str(exc))


class DashboardView(QWidget):
    """Dashboard overview with stat cards."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._facade = DashboardFacade()
        self._refresh_thread: QThread | None = None
        self._refresh_worker: _DashboardOverviewWorker | None = None
        self._usage_refresh_timer = QTimer(self)
        self._usage_refresh_timer.setSingleShot(True)
        self._usage_refresh_timer.setInterval(220)
        self._usage_refresh_timer.timeout.connect(self._refresh_usage_now)
        self.destroyed.connect(self._stop_refresh_thread)
        self._build_ui()

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

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        header_hl = QHBoxLayout()
        title = QLabel("Dashboard")
        title.setObjectName("view_title")
        self._refresh_btn = QPushButton("⟳ Làm mới")
        self._refresh_btn.setMinimumWidth(110)
        self._refresh_btn.clicked.connect(self.refresh)
        header_hl.addWidget(title)
        header_hl.addStretch()
        header_hl.addWidget(self._refresh_btn)
        outer.addLayout(header_hl)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        scroll.setWidget(content)
        outer.addWidget(scroll, stretch=1)

        self._content_vl = QVBoxLayout(content)
        self._content_vl.setContentsMargins(16, 8, 16, 16)
        self._content_vl.setSpacing(20)

        # Row 1: summary cards (2 cards)
        row1 = QHBoxLayout()
        self._card_banks = _StatCard("🗂 Ngân hàng", "0")
        self._card_questions = _StatCard("📋 Câu hỏi", "0")
        row1.addWidget(self._card_banks)
        row1.addWidget(self._card_questions)
        row1.addStretch()
        self._content_vl.addLayout(row1)

        # Row 2: type breakdown cards (4 cards)
        type_box = QGroupBox("Phân bố theo loại câu hỏi")
        type_box.setStyleSheet("QGroupBox { font-weight: bold; }")
        type_grid = QGridLayout(type_box)
        type_grid.setSpacing(12)
        self._card_mc = _StatCard("Multiple Choice", "0")
        self._card_ma = _StatCard("Multiple Answer", "0")
        self._card_blank = _StatCard("Blank", "0")
        self._card_sa = _StatCard("Short Answer", "0")
        type_grid.addWidget(self._card_mc, 0, 0)
        type_grid.addWidget(self._card_ma, 0, 1)
        type_grid.addWidget(self._card_blank, 0, 2)
        type_grid.addWidget(self._card_sa, 0, 3)
        self._content_vl.addWidget(type_box)

        # Row 3: bank stats table
        banks_box = QGroupBox("Ngân hàng gần đây")
        banks_box.setStyleSheet("QGroupBox { font-weight: bold; }")
        banks_vl = QVBoxLayout(banks_box)
        self._banks_label = QLabel("–")
        self._banks_label.setWordWrap(True)
        self._banks_label.setTextFormat(Qt.TextFormat.RichText)
        self._banks_label.setStyleSheet("padding: 4px; font-size: 14px;")
        banks_vl.addWidget(self._banks_label)
        self._content_vl.addWidget(banks_box)

        # Row 4: usage stats
        self._content_vl.addWidget(self._build_usage_section())

        self._content_vl.addStretch()

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def _apply_overview(self, overview: object | None) -> None:
        if overview is None:
            self._card_banks.set_value("0")
            self._card_questions.set_value("0")
            self._card_mc.set_value("0")
            self._card_ma.set_value("0")
            self._card_blank.set_value("0")
            self._card_sa.set_value("0")
            self._banks_label.setText("Chưa có ngân hàng nào.")
            return

        self._card_banks.set_value(str(overview.total_banks))
        self._card_questions.set_value(str(overview.total_questions))
        self._card_mc.set_value(str(overview.type_breakdown.mc))
        self._card_ma.set_value(str(overview.type_breakdown.ma))
        self._card_blank.set_value(str(overview.type_breakdown.blank))
        self._card_sa.set_value(str(overview.type_breakdown.sa))

        if overview.recent_banks:
            rows: list[str] = []
            for _bid, bname, qcount in overview.recent_banks:
                rows.append(
                    f"<tr><td style='padding:4px 12px 4px 4px;'>{bname}</td>"
                    f"<td style='padding:4px;color:#2468a8;font-weight:bold;'>{qcount} câu</td></tr>"
                )
            self._banks_label.setText(
                f"<table>{''.join(rows)}</table>"
            )
        else:
            self._banks_label.setText("Chưa có ngân hàng nào.")

    def _refresh(self) -> None:
        if "PYTEST_CURRENT_TEST" in os.environ:
            try:
                overview = self._facade.load_overview()
                self._apply_overview(overview)
                self._load_usage_banks(items=self._facade.load_usage_banks())
            except (RuntimeError, ValueError, OSError):
                self._apply_overview(None)
                self._load_usage_banks(items=[])
            return

        if self._refresh_thread is not None and self._refresh_thread.isRunning():
            return

        self._refresh_btn.setEnabled(False)
        self._banks_label.setText("Đang tải dashboard...")
        self._usage_summary_lbl.setText("Đang tải dữ liệu sử dụng câu hỏi...")

        self._refresh_thread = QThread()
        self._refresh_worker = _DashboardOverviewWorker(self._facade)
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
        overview: object | None,
        usage_banks: object,
        error_message: object | None,
    ) -> None:
        self._refresh_btn.setEnabled(True)
        self._apply_overview(overview)

        if error_message:
            self._usage_summary_lbl.setText(
                f"<b style='color:red;'>Lỗi tải dữ liệu:</b> {error_message}"
            )
            self._usage_table.setRowCount(0)
            self._load_usage_banks(items=[])
        else:
            self._load_usage_banks(items=usage_banks if isinstance(usage_banks, list) else None)

    def _on_refresh_thread_finished(self) -> None:
        """Clear thread/worker references only after thread has fully stopped."""
        self._refresh_worker = None
        self._refresh_thread = None

    # Public
    def refresh(self) -> None:
        self._refresh()

    # ------------------------------------------------------------------
    # Usage stats section
    # ------------------------------------------------------------------

    def _build_usage_section(self) -> QGroupBox:
        box = QGroupBox("Thống kê sử dụng câu hỏi")
        box.setStyleSheet("QGroupBox { font-weight: bold; }")
        vl = QVBoxLayout(box)
        vl.setSpacing(8)

        sel_hl = QHBoxLayout()
        sel_hl.addWidget(QLabel("Ngân hàng:"))
        self._usage_bank_combo = QComboBox()
        self._usage_bank_combo.setMinimumWidth(200)
        self._usage_bank_combo.currentIndexChanged.connect(self._schedule_usage_refresh)
        sel_hl.addWidget(self._usage_bank_combo)
        sel_hl.addStretch()
        vl.addLayout(sel_hl)

        self._usage_summary_lbl = QLabel("Chọn ngân hàng để xem thống kê.")
        self._usage_summary_lbl.setTextFormat(Qt.TextFormat.RichText)
        self._usage_summary_lbl.setWordWrap(True)
        self._usage_summary_lbl.setStyleSheet("color: #444; padding: 4px 0;")
        vl.addWidget(self._usage_summary_lbl)

        self._usage_table = QTableWidget(0, 7)
        self._usage_table.setHorizontalHeaderLabels(
            ["Mã", "Loại", "Độ khó", "Điểm", "Số lần được dùng", "Số lần trả lời đúng", "Sửa câu hỏi"]
        )
        _hdr = self._usage_table.horizontalHeader()
        for _col in range(7):
            _hdr.setSectionResizeMode(_col, QHeaderView.ResizeMode.Stretch)
        self._usage_table.verticalHeader().setDefaultSectionSize(36)
        self._usage_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._usage_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._usage_table.setAlternatingRowColors(True)
        self._usage_table.verticalHeader().setVisible(False)
        self._usage_table.setMinimumHeight(200)
        self._usage_table.cellClicked.connect(self._on_usage_cell_clicked)
        vl.addWidget(self._usage_table)
        return box

    def _load_usage_banks(self, items: list[tuple[int, str]] | None = None) -> None:
        """Reload bank list in the usage combo, preserving selection."""
        self._usage_bank_combo.blockSignals(True)
        prev = self._usage_bank_combo.currentData()
        self._usage_bank_combo.clear()
        self._usage_bank_combo.addItem("— Chọn ngân hàng —", userData=None)
        if items is None:
            try:
                items = self._facade.load_usage_banks()
            except Exception:
                items = []
        for bid, bname in items:
            self._usage_bank_combo.addItem(bname, userData=bid)
        for i in range(self._usage_bank_combo.count()):
            if self._usage_bank_combo.itemData(i) == prev:
                self._usage_bank_combo.setCurrentIndex(i)
                break
        self._usage_bank_combo.blockSignals(False)
        self._schedule_usage_refresh()

    def _schedule_usage_refresh(self) -> None:
        self._usage_refresh_timer.start()

    def _refresh_usage_now(self) -> None:
        """Query and display per-question usage stats for the selected bank."""
        bank_id = self._usage_bank_combo.currentData()
        if bank_id is None:
            self._usage_summary_lbl.setText("Chọn ngân hàng để xem thống kê.")
            self._usage_table.setRowCount(0)
            return

        try:
            rows, summary = self._facade.load_usage_stats(bank_id)
        except Exception as exc:
            self._usage_summary_lbl.setText(
                f"<b style='color:red;'>Lỗi tải dữ liệu:</b> {exc}"
            )
            self._usage_table.setRowCount(0)
            return

        total = summary.total_questions
        active_cnt = summary.active_questions
        total_uses = summary.total_uses
        total_correct = summary.total_correct
        type_str = (
            f"MC: {summary.type_breakdown.mc} &nbsp;"
            f"MA: {summary.type_breakdown.ma} &nbsp;"
            f"Blank: {summary.type_breakdown.blank} &nbsp;"
            f"SA: {summary.type_breakdown.sa}"
        )
        correct_pct = (
            f" ({100 * total_correct // total_uses}%)" if total_uses > 0 else ""
        )
        self._usage_summary_lbl.setText(
            f"<b>Tổng câu hỏi:</b> {total} "
            f"(Active: {active_cnt}, Inactive: {total - active_cnt})"
            f"&nbsp;&nbsp;|&nbsp;&nbsp;<b>Loại:</b> {type_str}"
            f"&nbsp;&nbsp;|&nbsp;&nbsp;<b>Lượt sử dụng:</b> {total_uses}"
            f"&nbsp;&nbsp;|&nbsp;&nbsp;<b>Trả lời đúng:</b> {total_correct}{correct_pct}"
        )

        _type_lbl = {"MC": "MC", "MA": "MA", "BLANK": "Blank", "SA": "SA"}
        self._usage_table.setUpdatesEnabled(False)
        try:
            self._usage_table.setRowCount(total)
            for r, row in enumerate(rows):
                def _ucell(text: str, center: bool = False) -> QTableWidgetItem:
                    item = QTableWidgetItem(text)
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    if center:
                        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    return item

                code_item = _ucell(row.question_code)
                code_item.setData(Qt.ItemDataRole.UserRole, row.question_id)
                # Tooltip shows content preview
                preview = row.content[:120]
                code_item.setToolTip(preview)
                self._usage_table.setItem(r, 0, code_item)
                self._usage_table.setItem(
                    r, 1,
                    _ucell(_type_lbl.get(row.question_type, row.question_type), center=True),
                )
                self._usage_table.setItem(
                    r, 2, _ucell(row.difficulty.capitalize(), center=True)
                )
                self._usage_table.setItem(
                    r, 3, _ucell(f"{row.point_value:.1f}", center=True)
                )
                self._usage_table.setItem(
                    r, 4, _ucell(str(row.used_count), center=True)
                )
                self._usage_table.setItem(
                    r, 5, _ucell(str(row.correct_count), center=True)
                )
                edit_item = _ucell("✎", center=True)
                edit_item.setToolTip("Sửa câu hỏi")
                edit_item.setForeground(Qt.GlobalColor.red)
                edit_item.setData(Qt.ItemDataRole.UserRole, row.question_id)
                edit_item.setData(Qt.ItemDataRole.UserRole + 1, bank_id)
                self._usage_table.setItem(r, 6, edit_item)
        finally:
            self._usage_table.setUpdatesEnabled(True)

    def _on_usage_cell_clicked(self, row: int, column: int) -> None:
        """Open editor when user clicks the action column in usage table."""
        if column != 6:
            return
        item = self._usage_table.item(row, column)
        if item is None:
            return
        question_id = item.data(Qt.ItemDataRole.UserRole)
        bank_id = item.data(Qt.ItemDataRole.UserRole + 1)
        if isinstance(question_id, int) and isinstance(bank_id, int):
            self._open_question_editor(bank_id, question_id)

    def _open_question_editor(self, bank_id: int, question_id: int) -> None:
        """Open QuestionEditorDialog for the given question then refresh."""
        from ui.dialogs.question_editor_dialog import QuestionEditorDialog

        try:
            q = self._facade.get_question_for_edit(question_id)
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi", f"Không thể tải câu hỏi:\n{exc}")
            return

        if q is None:
            QMessageBox.warning(self, "Không tìm thấy", "Câu hỏi không còn tồn tại.")
            return

        dlg = QuestionEditorDialog(bank_id, q, parent=self)
        if dlg.exec() == QuestionEditorDialog.DialogCode.Accepted:
            self._refresh_usage_now()


# ---------------------------------------------------------------------------
# Stat card widget
# ---------------------------------------------------------------------------

class _StatCard(QFrame):
    """A simple flat card showing a label and a large value."""

    def __init__(self, label: str, value: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("stat_card")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFixedHeight(90)
        self.setMinimumWidth(130)
        self.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed
        )
        vl = QVBoxLayout(self)
        vl.setContentsMargins(14, 10, 14, 10)
        vl.setSpacing(2)
        self._lbl = QLabel(label)
        self._lbl.setObjectName("stat_card_label")
        self._val = QLabel(value)
        self._val.setObjectName("stat_card_value")
        vl.addWidget(self._lbl)
        vl.addWidget(self._val)

    def set_value(self, value: str) -> None:
        self._val.setText(value)
