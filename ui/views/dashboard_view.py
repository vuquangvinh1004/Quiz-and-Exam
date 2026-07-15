"""Màn tổng quan: thống kê, báo cáo sử dụng và cảnh báo vận hành."""
from __future__ import annotations

import os

from PySide6.QtCore import QThread, QTimer
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

from ui.facades.dashboard_facade import DashboardFacade
from ui.views.dashboard_detail_mixin import DashboardDetailMixin
from ui.views.dashboard_shared import _DashboardOverviewWorker, _StatCard


class DashboardView(DashboardDetailMixin, QWidget):
    """Màn tổng quan với các thẻ thống kê."""

    _QUESTION_TYPE_LABELS = {
        "MC": "Trắc nghiệm 1 đáp án",
        "MA": "Trắc nghiệm nhiều đáp án",
        "TF": "Đúng/Sai",
        "BLANK": "Điền vào chỗ trống",
        "SA": "Trả lời ngắn",
        "ES": "Tự luận",
    }
    _DIFFICULTY_LABELS = ("Nhớ", "Hiểu", "Vận dụng", "Phân tích", "Đánh giá", "Sáng tạo")

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
        self._card_banks = None
        self._card_questions = None
        self._card_mc = None
        self._card_ma = None
        self._card_tf = None
        self._card_blank = None
        self._card_sa = None
        self._card_es = None
        self._card_attempts = None
        self._card_avg_score = None
        self._card_best_score = None
        self._card_exam_mode = None
        self._card_practice_mode = None
        self._card_study_mode = None
        self._card_import_warnings = None
        self._card_runtime_warnings = None
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

    def _make_card(self, label: str, value: str) -> _StatCard:
        return _StatCard(label, value)

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
        content = QWidget()
        scroll.setWidget(content)
        outer.addWidget(scroll, stretch=1)

        self._content_vl = QVBoxLayout(content)
        self._content_vl.setContentsMargins(16, 8, 16, 16)
        self._content_vl.setSpacing(20)

        row1 = QHBoxLayout()
        self._card_banks = self._make_card("🗂 Ngân hàng", "0")
        self._card_questions = self._make_card("📋 Câu hỏi", "0")
        row1.addWidget(self._card_banks)
        row1.addWidget(self._card_questions)
        row1.addStretch()
        self._content_vl.addLayout(row1)

        self._content_vl.addWidget(self._build_attempt_section())
        self._content_vl.addWidget(self._build_reporting_section())

        type_box = self._build_type_breakdown_box()
        self._content_vl.addWidget(type_box)

        banks_box = self._build_recent_banks_box()
        self._content_vl.addWidget(banks_box)

        self._content_vl.addWidget(self._build_usage_section())
        self._content_vl.addWidget(self._build_warning_section())
        self._content_vl.addStretch()

    def _build_type_breakdown_box(self):
        from PySide6.QtWidgets import QGridLayout, QGroupBox

        type_box = QGroupBox("Phân bố theo loại câu hỏi")
        type_box.setStyleSheet("QGroupBox { font-weight: bold; }")
        type_grid = QGridLayout(type_box)
        type_grid.setSpacing(12)
        self._card_mc = self._make_card("Trắc nghiệm 1 đáp án", "0")
        self._card_ma = self._make_card("Trắc nghiệm nhiều đáp án", "0")
        self._card_tf = self._make_card("Đúng/Sai", "0")
        self._card_blank = self._make_card("Điền vào chỗ trống", "0")
        self._card_sa = self._make_card("Trả lời ngắn", "0")
        self._card_es = self._make_card("Tự luận", "0")
        type_grid.addWidget(self._card_mc, 0, 0)
        type_grid.addWidget(self._card_ma, 0, 1)
        type_grid.addWidget(self._card_tf, 0, 2)
        type_grid.addWidget(self._card_blank, 1, 0)
        type_grid.addWidget(self._card_sa, 1, 1)
        type_grid.addWidget(self._card_es, 1, 2)
        return type_box

    def _build_recent_banks_box(self):
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QGroupBox, QVBoxLayout

        banks_box = QGroupBox("Ngân hàng gần đây")
        banks_box.setStyleSheet("QGroupBox { font-weight: bold; }")
        banks_vl = QVBoxLayout(banks_box)
        self._banks_label = QLabel("–")
        self._banks_label.setWordWrap(True)
        self._banks_label.setTextFormat(Qt.TextFormat.RichText)
        self._banks_label.setStyleSheet("padding: 4px; font-size: 14px;")
        banks_vl.addWidget(self._banks_label)
        return banks_box

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
            self._banks_label.setText(f"<table>{''.join(rows)}</table>")
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
            self._usage_summary_lbl.setText(f"<b style='color:red;'>Lỗi tải dữ liệu:</b> {error_message}")
            self._usage_table.setRowCount(0)
            self._load_usage_banks(items=[])
            self._warning_summary_lbl.setText(f"<b style='color:red;'>Lỗi cảnh báo vận hành:</b> {error_message}")
        else:
            self._load_usage_banks(items=usage_banks if isinstance(usage_banks, list) else None)
            self._load_reporting_banks(items=usage_banks if isinstance(usage_banks, list) else None)

    def _on_refresh_thread_finished(self) -> None:
        self._refresh_worker = None
        self._refresh_thread = None

    def refresh(self) -> None:
        self._refresh()

    def _build_attempt_section(self):
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QGroupBox, QHBoxLayout, QVBoxLayout

        box = QGroupBox("Hiệu suất làm bài")
        box.setStyleSheet("QGroupBox { font-weight: bold; }")
        vl = QVBoxLayout(box)
        vl.setSpacing(8)

        row = QHBoxLayout()
        self._card_attempts = self._make_card("Lượt làm bài", "0")
        self._card_avg_score = self._make_card("Điểm TB", "0%")
        self._card_best_score = self._make_card("Điểm cao nhất", "0%")
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
