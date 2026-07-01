"""Màn tổng quan: thống kê, báo cáo sử dụng và cảnh báo vận hành.

Hiển thị: tổng quan ngân hàng/câu hỏi, phân tích lượt làm,
breakdown sử dụng và cảnh báo gần đây. Dữ liệu được lấy qua facade/service.
"""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from PySide6.QtCore import QDate, QObject, Qt, QThread, QTimer, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDateEdit,
    QFrame,
    QFileDialog,
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

    finished = Signal(object, object, object, object)

    def __init__(self, facade: DashboardFacade) -> None:
        super().__init__()
        self._facade = facade

    def run(self) -> None:
        try:
            overview = self._facade.load_overview()
            usage_banks = self._facade.load_usage_banks()
            warning_summary = self._facade.load_warning_summary()
            self.finished.emit(overview, usage_banks, warning_summary, None)
        except (RuntimeError, ValueError, OSError) as exc:  # pragma: no cover
            self.finished.emit(None, [], None, str(exc))


class DashboardView(QWidget):
    """Màn tổng quan với các thẻ thống kê."""

    _QUESTION_TYPE_LABELS = {
        "MC": "Trắc nghiệm 1 đáp án",
        "MA": "Trắc nghiệm nhiều đáp án",
        "TF": "Đúng/Sai",
        "BLANK": "Điền vào chỗ trống",
        "SA": "Trả lời ngắn",
        "ES": "Tự luận",
    }
    _DIFFICULTY_LABELS = (
        "Nhớ",
        "Hiểu",
        "Vận dụng",
        "Phân tích",
        "Đánh giá",
        "Sáng tạo",
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._facade = DashboardFacade()
        self._refresh_thread: QThread | None = None
        self._refresh_worker: _DashboardOverviewWorker | None = None
        self._usage_refresh_timer = QTimer(self)
        self._usage_refresh_timer.setSingleShot(True)
        self._usage_refresh_timer.setInterval(220)
        self._usage_refresh_timer.timeout.connect(self._refresh_usage_now)
        self._reporting_refresh_timer = QTimer(self)
        self._reporting_refresh_timer.setSingleShot(True)
        self._reporting_refresh_timer.setInterval(220)
        self._reporting_refresh_timer.timeout.connect(self._refresh_reporting_now)
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
        title = QLabel("Tổng quan")
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

        # Row 2: attempt analytics
        self._content_vl.addWidget(self._build_attempt_section())

        # Row 2b: deeper reporting
        self._content_vl.addWidget(self._build_reporting_section())

        # Row 3: type breakdown cards (6 cards)
        type_box = QGroupBox("Phân bố theo loại câu hỏi")
        type_box.setStyleSheet("QGroupBox { font-weight: bold; }")
        type_grid = QGridLayout(type_box)
        type_grid.setSpacing(12)
        self._card_mc = _StatCard("Trắc nghiệm 1 đáp án", "0")
        self._card_ma = _StatCard("Trắc nghiệm nhiều đáp án", "0")
        self._card_tf = _StatCard("Đúng/Sai", "0")
        self._card_blank = _StatCard("Điền vào chỗ trống", "0")
        self._card_sa = _StatCard("Trả lời ngắn", "0")
        self._card_es = _StatCard("Tự luận", "0")
        type_grid.addWidget(self._card_mc, 0, 0)
        type_grid.addWidget(self._card_ma, 0, 1)
        type_grid.addWidget(self._card_tf, 0, 2)
        type_grid.addWidget(self._card_blank, 1, 0)
        type_grid.addWidget(self._card_sa, 1, 1)
        type_grid.addWidget(self._card_es, 1, 2)
        self._content_vl.addWidget(type_box)

        # Row 4: bank stats table
        banks_box = QGroupBox("Ngân hàng gần đây")
        banks_box.setStyleSheet("QGroupBox { font-weight: bold; }")
        banks_vl = QVBoxLayout(banks_box)
        self._banks_label = QLabel("–")
        self._banks_label.setWordWrap(True)
        self._banks_label.setTextFormat(Qt.TextFormat.RichText)
        self._banks_label.setStyleSheet("padding: 4px; font-size: 14px;")
        banks_vl.addWidget(self._banks_label)
        self._content_vl.addWidget(banks_box)

        # Row 5: usage stats
        self._content_vl.addWidget(self._build_usage_section())

        # Row 6: telemetry warning summary
        self._content_vl.addWidget(self._build_warning_section())

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
            self._card_tf.set_value("0")
            self._card_blank.set_value("0")
            self._card_sa.set_value("0")
            self._card_es.set_value("0")
            self._apply_attempt_stats(None)
            self._apply_reporting(None, None, None, None)
            self._usage_summary_lbl.setText("Chọn ngân hàng để xem thống kê.")
            self._usage_detail_lbl.setText("Chưa có dữ liệu mức độ và CLO.")
            self._usage_table.setRowCount(0)
            self._banks_label.setText("Chưa có ngân hàng nào.")
            return

        self._card_banks.set_value(str(overview.total_banks))
        self._card_questions.set_value(str(overview.total_questions))
        self._card_mc.set_value(str(overview.type_breakdown.mc))
        self._card_ma.set_value(str(overview.type_breakdown.ma))
        self._card_tf.set_value(str(overview.type_breakdown.tf))
        self._card_blank.set_value(str(overview.type_breakdown.blank))
        self._card_sa.set_value(str(overview.type_breakdown.sa))
        self._card_es.set_value(str(overview.type_breakdown.es))
        self._apply_attempt_stats(getattr(overview, "attempt_stats", None))
        self._apply_reporting(
            getattr(overview, "mode_breakdown", None),
            getattr(overview, "recent_activity", None),
            getattr(overview, "reporting_window_summary", None),
            getattr(overview, "reporting_bank_breakdown", None),
        )

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
                self._load_reporting_banks(items=self._facade.load_reporting_banks())
                self._apply_warning_summary(self._facade.load_warning_summary())
            except (RuntimeError, ValueError, OSError):
                self._apply_overview(None)
                self._load_usage_banks(items=[])
                self._load_reporting_banks(items=[])
                self._apply_warning_summary(None)
            return

        if self._refresh_thread is not None and self._refresh_thread.isRunning():
            return

        self._refresh_btn.setEnabled(False)
        self._banks_label.setText("Đang tải tổng quan...")
        self._attempt_summary_lbl.setText("Đang tải thống kê bài làm...")
        self._reporting_summary_lbl.setText("Đang tải breakdown và xu hướng...")
        self._reporting_bank_table.setRowCount(0)
        self._usage_summary_lbl.setText("Đang tải dữ liệu sử dụng câu hỏi...")
        self._warning_summary_lbl.setText("Đang tải cảnh báo vận hành...")

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
        warning_summary: object | None,
        error_message: object | None,
    ) -> None:
        self._refresh_btn.setEnabled(True)
        self._apply_overview(overview)
        self._apply_warning_summary(warning_summary)

        if error_message:
            self._usage_summary_lbl.setText(
                f"<b style='color:red;'>Lỗi tải dữ liệu:</b> {error_message}"
            )
            self._usage_table.setRowCount(0)
            self._load_usage_banks(items=[])
            self._warning_summary_lbl.setText(
                f"<b style='color:red;'>Lỗi cảnh báo vận hành:</b> {error_message}"
            )
        else:
            self._load_usage_banks(items=usage_banks if isinstance(usage_banks, list) else None)
            self._load_reporting_banks(items=usage_banks if isinstance(usage_banks, list) else None)

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

    def _build_attempt_section(self) -> QGroupBox:
        box = QGroupBox("Hiệu suất làm bài")
        box.setStyleSheet("QGroupBox { font-weight: bold; }")
        vl = QVBoxLayout(box)
        vl.setSpacing(8)

        row = QHBoxLayout()
        self._card_attempts = _StatCard("Lượt làm bài", "0")
        self._card_avg_score = _StatCard("Điểm TB", "0%")
        self._card_best_score = _StatCard("Điểm cao nhất", "0%")
        row.addWidget(self._card_attempts)
        row.addWidget(self._card_avg_score)
        row.addWidget(self._card_best_score)
        row.addStretch()
        vl.addLayout(row)

        self._attempt_summary_lbl = QLabel("Chưa có dữ liệu bài làm đã hoàn tất.")
        self._attempt_summary_lbl.setTextFormat(Qt.TextFormat.RichText)
        self._attempt_summary_lbl.setWordWrap(True)
        self._attempt_summary_lbl.setStyleSheet("color: #444; padding: 4px 0;")
        vl.addWidget(self._attempt_summary_lbl)
        return box

    def _apply_attempt_stats(self, stats: object | None) -> None:
        if stats is None:
            self._card_attempts.set_value("0")
            self._card_avg_score.set_value("0%")
            self._card_best_score.set_value("0%")
            self._attempt_summary_lbl.setText("Chưa có dữ liệu bài làm đã hoàn tất.")
            return

        self._card_attempts.set_value(str(stats.total_attempts))
        self._card_avg_score.set_value(f"{stats.avg_score_pct:.1f}%")
        self._card_best_score.set_value(f"{stats.best_score_pct:.1f}%")
        self._attempt_summary_lbl.setText(
            f"<b>Tổng đúng:</b> {stats.total_correct}"
            f"&nbsp;&nbsp;|&nbsp;&nbsp;<b>Tổng sai:</b> {stats.total_incorrect}"
            f"&nbsp;&nbsp;|&nbsp;&nbsp;<b>Tổng bỏ qua:</b> {stats.total_skipped}"
        )

    def _build_reporting_section(self) -> QGroupBox:
        box = QGroupBox("Báo cáo sử dụng gần đây")
        box.setStyleSheet("QGroupBox { font-weight: bold; }")
        vl = QVBoxLayout(box)
        vl.setSpacing(8)

        row = QHBoxLayout()
        self._card_exam_mode = _StatCard("Kiểm tra", "0")
        self._card_practice_mode = _StatCard("Luyện tập", "0")
        self._card_study_mode = _StatCard("Ôn tập", "0")
        row.addWidget(self._card_exam_mode)
        row.addWidget(self._card_practice_mode)
        row.addWidget(self._card_study_mode)
        row.addStretch()
        vl.addLayout(row)

        filters = QHBoxLayout()
        filters.addWidget(QLabel("Ngân hàng:"))
        self._report_bank_combo = QComboBox()
        self._report_bank_combo.setMinimumWidth(180)
        self._report_bank_combo.currentIndexChanged.connect(self._on_report_bank_changed)
        filters.addWidget(self._report_bank_combo)
        filters.addWidget(QLabel("Bài kiểm tra:"))
        self._report_quiz_combo = QComboBox()
        self._report_quiz_combo.setMinimumWidth(220)
        self._report_quiz_combo.currentIndexChanged.connect(self._schedule_reporting_refresh)
        filters.addWidget(self._report_quiz_combo)
        filters.addWidget(QLabel("Khoảng thời gian:"))
        self._report_days_combo = QComboBox()
        self._report_days_combo.addItem("7 ngày", 7)
        self._report_days_combo.addItem("14 ngày", 14)
        self._report_days_combo.addItem("30 ngày", 30)
        self._report_days_combo.addItem("Tùy chỉnh", "custom")
        self._report_days_combo.currentIndexChanged.connect(self._sync_reporting_range_controls)
        self._report_days_combo.currentIndexChanged.connect(self._schedule_reporting_refresh)
        filters.addWidget(self._report_days_combo)
        filters.addWidget(QLabel("Từ ngày:"))
        self._report_start_date = QDateEdit()
        self._report_start_date.setCalendarPopup(True)
        self._report_start_date.setDisplayFormat("dd/MM/yyyy")
        self._report_start_date.setDate(QDate.currentDate().addDays(-6))
        self._report_start_date.dateChanged.connect(self._schedule_reporting_refresh)
        filters.addWidget(self._report_start_date)
        filters.addWidget(QLabel("Đến ngày:"))
        self._report_end_date = QDateEdit()
        self._report_end_date.setCalendarPopup(True)
        self._report_end_date.setDisplayFormat("dd/MM/yyyy")
        self._report_end_date.setDate(QDate.currentDate())
        self._report_end_date.dateChanged.connect(self._schedule_reporting_refresh)
        filters.addWidget(self._report_end_date)
        self._report_export_btn = QPushButton("Xuất CSV")
        self._report_export_btn.clicked.connect(self._export_reporting_csv)
        filters.addWidget(self._report_export_btn)
        filters.addStretch()
        vl.addLayout(filters)
        self._sync_reporting_range_controls()

        self._reporting_summary_lbl = QLabel("Chưa có dữ liệu breakdown và xu hướng gần đây.")
        self._reporting_summary_lbl.setTextFormat(Qt.TextFormat.RichText)
        self._reporting_summary_lbl.setWordWrap(True)
        self._reporting_summary_lbl.setStyleSheet("color: #444; padding: 4px 0;")
        vl.addWidget(self._reporting_summary_lbl)

        self._reporting_bank_table = QTableWidget(0, 6)
        self._reporting_bank_table.setHorizontalHeaderLabels(
            ["Ngân hàng", "Lượt làm", "Bài kiểm tra", "Điểm TB", "Điểm cao nhất", "Lần cuối"]
        )
        report_hdr = self._reporting_bank_table.horizontalHeader()
        report_hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col in range(1, 6):
            report_hdr.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        self._reporting_bank_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._reporting_bank_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._reporting_bank_table.verticalHeader().setVisible(False)
        self._reporting_bank_table.setAlternatingRowColors(True)
        self._reporting_bank_table.setMinimumHeight(180)
        vl.addWidget(self._reporting_bank_table)
        return box

    def _apply_reporting(
        self,
        mode_breakdown: object | None,
        recent_activity: object | None,
        window_summary: object | None,
        bank_breakdown: object | None,
    ) -> None:
        if mode_breakdown is None:
            self._card_exam_mode.set_value("0")
            self._card_practice_mode.set_value("0")
            self._card_study_mode.set_value("0")
            self._reporting_summary_lbl.setText("Chưa có dữ liệu breakdown và xu hướng gần đây.")
            self._reporting_bank_table.setRowCount(0)
            return

        self._card_exam_mode.set_value(str(mode_breakdown.exam_count))
        self._card_practice_mode.set_value(str(mode_breakdown.practice_count))
        self._card_study_mode.set_value(str(mode_breakdown.study_count))

        points = recent_activity if isinstance(recent_activity, list) else []
        active_points = [p for p in points if getattr(p, "attempts", 0) > 0]
        selected_days = self._report_days_combo.currentData()
        if selected_days == "custom":
            start = self._report_start_date.date().toString("dd/MM/yyyy")
            end = self._report_end_date.date().toString("dd/MM/yyyy")
            day_label = f"{start} - {end}"
        else:
            day_label = f"{selected_days} ngày" if isinstance(selected_days, int) else "7 ngày"
        if window_summary is None or getattr(window_summary, "total_attempts", 0) <= 0:
            self._reporting_summary_lbl.setText(
                f"Chưa ghi nhận lượt làm bài hoàn tất trong cửa sổ {day_label.lower()}."
            )
        else:
            trend_text = "Không có ngày nào phát sinh attempt."
            if active_points:
                trend_text = " &nbsp;&nbsp;|&nbsp;&nbsp; ".join(
                    f"{p.date_label}: {p.attempts} lượt, TB {p.avg_score_pct:.1f}%"
                    for p in active_points[-5:]
                )
            self._reporting_summary_lbl.setText(
                f"<b>{day_label}:</b> {window_summary.total_attempts} lượt làm"
                f" &nbsp;&nbsp;|&nbsp;&nbsp; <b>Ngân hàng hoạt động:</b> {window_summary.active_banks}"
                f" &nbsp;&nbsp;|&nbsp;&nbsp; <b>Bài kiểm tra hoạt động:</b> {window_summary.active_quizzes}"
                f" &nbsp;&nbsp;|&nbsp;&nbsp; <b>TB:</b> {window_summary.avg_score_pct:.1f}%"
                f" &nbsp;&nbsp;|&nbsp;&nbsp; <b>Cao nhất:</b> {window_summary.best_score_pct:.1f}%"
                f"<br><b>Xu hướng gần nhất:</b> {trend_text}"
            )

        rows = bank_breakdown if isinstance(bank_breakdown, list) else []
        self._reporting_bank_table.setRowCount(len(rows))
        for row_idx, row in enumerate(rows):
            items = [
                QTableWidgetItem(str(getattr(row, "bank_name", ""))),
                QTableWidgetItem(str(getattr(row, "attempt_count", 0))),
                QTableWidgetItem(str(getattr(row, "quiz_count", 0))),
                QTableWidgetItem(f"{getattr(row, 'avg_score_pct', 0.0):.1f}%"),
                QTableWidgetItem(f"{getattr(row, 'best_score_pct', 0.0):.1f}%"),
                QTableWidgetItem(str(getattr(row, "last_activity_at", ""))),
            ]
            for col_idx, item in enumerate(items):
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if col_idx > 0:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self._reporting_bank_table.setItem(row_idx, col_idx, item)

    def _load_reporting_banks(self, items: list[tuple[int, str]] | None = None) -> None:
        self._report_bank_combo.blockSignals(True)
        prev = self._report_bank_combo.currentData()
        self._report_bank_combo.clear()
        self._report_bank_combo.addItem("— Tất cả ngân hàng —", userData=None)
        if items is None:
            try:
                items = self._facade.load_reporting_banks()
            except Exception:
                items = []
        for bid, bname in items:
            self._report_bank_combo.addItem(bname, userData=bid)
        for i in range(self._report_bank_combo.count()):
            if self._report_bank_combo.itemData(i) == prev:
                self._report_bank_combo.setCurrentIndex(i)
                break
        self._report_bank_combo.blockSignals(False)
        self._on_report_bank_changed()

    def _load_reporting_quizzes(self, bank_id: int | None) -> None:
        self._report_quiz_combo.blockSignals(True)
        prev = self._report_quiz_combo.currentData()
        self._report_quiz_combo.clear()
        self._report_quiz_combo.addItem("— Tất cả bài kiểm tra —", userData=None)
        try:
            items = self._facade.load_reporting_quizzes(bank_id)
        except Exception:
            items = []
        for quiz_id, title in items:
            self._report_quiz_combo.addItem(title, userData=quiz_id)
        for i in range(self._report_quiz_combo.count()):
            if self._report_quiz_combo.itemData(i) == prev:
                self._report_quiz_combo.setCurrentIndex(i)
                break
        self._report_quiz_combo.blockSignals(False)

    def _on_report_bank_changed(self) -> None:
        bank_id = self._report_bank_combo.currentData()
        self._load_reporting_quizzes(bank_id if isinstance(bank_id, int) else None)
        self._schedule_reporting_refresh()

    def _schedule_reporting_refresh(self) -> None:
        self._reporting_refresh_timer.start()

    def _sync_reporting_range_controls(self) -> None:
        is_custom = self._report_days_combo.currentData() == "custom"
        self._report_start_date.setEnabled(is_custom)
        self._report_end_date.setEnabled(is_custom)

    def _selected_reporting_range(self) -> tuple[int, date | None, date | None]:
        current_data = self._report_days_combo.currentData()
        if current_data == "custom":
            start = self._report_start_date.date().toPython()
            end = self._report_end_date.date().toPython()
            return 0, start, end
        return int(current_data) if isinstance(current_data, int) else 7, None, None

    def _refresh_reporting_now(self) -> None:
        bank_id = self._report_bank_combo.currentData()
        quiz_id = self._report_quiz_combo.currentData()
        self._sync_reporting_range_controls()
        days, start_date, end_date = self._selected_reporting_range()
        try:
            snapshot = self._facade.load_filtered_reporting(
                bank_id=bank_id if isinstance(bank_id, int) else None,
                quiz_id=quiz_id if isinstance(quiz_id, int) else None,
                days=days,
                start_date=start_date,
                end_date=end_date,
            )
        except Exception as exc:
            self._apply_reporting(None, None, None, None)
            self._reporting_summary_lbl.setText(
                f"<b style='color:red;'>Lỗi tải reporting:</b> {exc}"
            )
            return
        self._apply_reporting(
            snapshot.mode_breakdown,
            snapshot.recent_activity,
            snapshot.window_summary,
            snapshot.bank_breakdown,
        )

    def _export_reporting_csv(self) -> None:
        bank_id = self._report_bank_combo.currentData()
        quiz_id = self._report_quiz_combo.currentData()
        days, start_date, end_date = self._selected_reporting_range()
        default_name = "analytics_reporting.csv"
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Xuất báo cáo analytics",
            default_name,
            "CSV (*.csv)",
        )
        if not save_path:
            return
        try:
            path = self._facade.export_reporting_csv(
                output_path=Path(os.path.abspath(save_path)),
                bank_id=bank_id if isinstance(bank_id, int) else None,
                quiz_id=quiz_id if isinstance(quiz_id, int) else None,
                days=days,
                start_date=start_date,
                end_date=end_date,
            )
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi", f"Không thể xuất CSV analytics:\n{exc}")
            return
        QMessageBox.information(self, "Xuất thành công", f"Đã xuất báo cáo CSV tại:\n{path}")

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

        self._usage_detail_lbl = QLabel("Chưa có dữ liệu mức độ và CLO.")
        self._usage_detail_lbl.setTextFormat(Qt.TextFormat.RichText)
        self._usage_detail_lbl.setWordWrap(True)
        self._usage_detail_lbl.setStyleSheet("color: #444; padding: 4px 0;")
        vl.addWidget(self._usage_detail_lbl)

        self._usage_table = QTableWidget(0, 8)
        self._usage_table.setHorizontalHeaderLabels(
            ["Mã", "Loại", "CLO", "Mức độ", "Điểm", "Số lần được dùng", "Số lần trả lời đúng", "Sửa câu hỏi"]
        )
        _hdr = self._usage_table.horizontalHeader()
        for _col in range(8):
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

    def _build_warning_section(self) -> QGroupBox:
        box = QGroupBox("Cảnh báo vận hành gần đây")
        box.setStyleSheet("QGroupBox { font-weight: bold; }")
        vl = QVBoxLayout(box)
        row = QHBoxLayout()
        self._card_import_warnings = _StatCard("Cảnh báo nhập", "0")
        self._card_runtime_warnings = _StatCard("Cảnh báo runtime", "0")
        row.addWidget(self._card_import_warnings)
        row.addWidget(self._card_runtime_warnings)
        row.addStretch()
        vl.addLayout(row)

        self._warning_summary_lbl = QLabel("Chưa có cảnh báo vận hành gần đây.")
        self._warning_summary_lbl.setTextFormat(Qt.TextFormat.RichText)
        self._warning_summary_lbl.setWordWrap(True)
        self._warning_summary_lbl.setStyleSheet("color: #444; padding: 4px 0;")
        vl.addWidget(self._warning_summary_lbl)
        return box

    def _apply_warning_summary(self, summary: object | None) -> None:
        if summary is None:
            self._card_import_warnings.set_value("0")
            self._card_runtime_warnings.set_value("0")
            self._warning_summary_lbl.setText("Chưa có cảnh báo vận hành gần đây.")
            return

        self._card_import_warnings.set_value(str(summary.import_warning_count))
        self._card_runtime_warnings.set_value(str(summary.runtime_warning_count))

        if not summary.recent_items:
            self._warning_summary_lbl.setText(
                "Không ghi nhận cảnh báo nhập/runtime đáng chú ý trong các log gần đây."
            )
            return

        rows: list[str] = []
        for item in summary.recent_items:
            rows.append(
                f"<tr><td style='padding:4px 8px 4px 4px;'><b>{item.timestamp}</b></td>"
                f"<td style='padding:4px 8px;color:#8e44ad;'>{item.category}</td>"
                f"<td style='padding:4px 8px;color:#c0392b;'>{item.event}</td>"
                f"<td style='padding:4px 4px 4px 8px;'>{item.message}</td></tr>"
            )
        self._warning_summary_lbl.setText(f"<table>{''.join(rows)}</table>")

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
            self._usage_detail_lbl.setText("Chưa có dữ liệu mức độ và CLO.")
            self._usage_table.setRowCount(0)
            return

        try:
            rows, summary = self._facade.load_usage_stats(bank_id)
        except Exception as exc:
            self._usage_summary_lbl.setText(
                f"<b style='color:red;'>Lỗi tải dữ liệu:</b> {exc}"
            )
            self._usage_detail_lbl.setText("")
            self._usage_table.setRowCount(0)
            return

        total = summary.total_questions
        active_cnt = summary.active_questions
        total_uses = summary.total_uses
        total_correct = summary.total_correct
        type_str = (
            f"Trắc nghiệm 1 đáp án: {summary.type_breakdown.mc} &nbsp;"
            f"Trắc nghiệm nhiều đáp án: {summary.type_breakdown.ma} &nbsp;"
            f"Đúng/Sai: {summary.type_breakdown.tf} &nbsp;"
            f"Điền vào chỗ trống: {summary.type_breakdown.blank} &nbsp;"
            f"Trả lời ngắn: {summary.type_breakdown.sa} &nbsp;"
            f"Tự luận: {summary.type_breakdown.es}"
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

        difficulty_breakdown = getattr(summary, "difficulty_breakdown", {})
        clo_count = int(getattr(summary, "learning_outcome_count", 0) or 0)
        clo_top = getattr(summary, "learning_outcome_top", [])
        difficulty_text = " &nbsp;&nbsp;|&nbsp;&nbsp; ".join(
            f"{label}: {int(difficulty_breakdown.get(label, 0) or 0)}"
            for label in self._DIFFICULTY_LABELS
        )
        clo_text = "Không có CLO nào được gắn."
        if clo_top:
            clo_text = " &nbsp;&nbsp;|&nbsp;&nbsp; ".join(
                f"{code}: {count}" for code, count in clo_top
            )
        self._usage_detail_lbl.setText(
            f"<b>Mức độ:</b> {difficulty_text}"
            f"&nbsp;&nbsp;|&nbsp;&nbsp;<b>CLO gắn:</b> {clo_count}/{total}"
            f"<br><b>CLO nổi bật:</b> {clo_text}"
        )

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
                    _ucell(self._QUESTION_TYPE_LABELS.get(row.question_type, row.question_type), center=True),
                )
                self._usage_table.setItem(
                    r, 2, _ucell(row.learning_outcome_code or "—", center=True)
                )
                self._usage_table.setItem(
                    r, 3, _ucell(self._display_level(row.difficulty), center=True)
                )
                self._usage_table.setItem(
                    r, 4, _ucell(f"{row.point_value:.1f}", center=True)
                )
                self._usage_table.setItem(
                    r, 5, _ucell(str(row.used_count), center=True)
                )
                self._usage_table.setItem(
                    r, 6, _ucell(str(row.correct_count), center=True)
                )
                edit_item = _ucell("✎", center=True)
                edit_item.setToolTip("Sửa câu hỏi")
                edit_item.setForeground(Qt.GlobalColor.red)
                edit_item.setData(Qt.ItemDataRole.UserRole, row.question_id)
                edit_item.setData(Qt.ItemDataRole.UserRole + 1, bank_id)
                self._usage_table.setItem(r, 7, edit_item)
        finally:
            self._usage_table.setUpdatesEnabled(True)

    def _on_usage_cell_clicked(self, row: int, column: int) -> None:
        """Open editor when user clicks the action column in usage table."""
        if column != 7:
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

    def _display_level(self, difficulty: str | None) -> str:
        raw = str(difficulty or "").strip()
        if not raw:
            return "—"
        mapping = {
            "easy": "Nhớ",
            "medium": "Hiểu",
            "hard": "Vận dụng",
        }
        return mapping.get(raw.lower(), raw)


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
