"""Reporting and usage sections for DashboardView."""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDateEdit,
    QDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)


class DashboardDetailMixin:
    def _build_reporting_section(self) -> QGroupBox:
        box = QGroupBox("Báo cáo sử dụng gần đây")
        box.setStyleSheet("QGroupBox { font-weight: bold; }")
        vl = QVBoxLayout(box)
        vl.setSpacing(8)

        row = QHBoxLayout()
        self._card_exam_mode = self._card_exam_mode if hasattr(self, "_card_exam_mode") else None
        self._card_exam_mode = self._card_exam_mode or self._make_card("Kiểm tra", "0")
        self._card_practice_mode = self._card_practice_mode or self._make_card("Luyện tập", "0")
        self._card_study_mode = self._card_study_mode or self._make_card("Ôn tập", "0")
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
        self._reporting_bank_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
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
            day_label = f"{start} -> {end}"
        else:
            day_label = f"{int(selected_days) if isinstance(selected_days, int) else 7} ngày"

        if window_summary is None:
            self._reporting_summary_lbl.setText(f"Chưa có dữ liệu hoàn tất trong cửa sổ {day_label.lower()}.")
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
            except (RuntimeError, ValueError, OSError):
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
        except (RuntimeError, ValueError, OSError):
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
        except (RuntimeError, ValueError, OSError) as exc:
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
        except (RuntimeError, ValueError, OSError) as exc:
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
        self._usage_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
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
        self._card_import_warnings = self._card_import_warnings or self._make_card("Cảnh báo nhập", "0")
        self._card_runtime_warnings = self._card_runtime_warnings or self._make_card("Cảnh báo runtime", "0")
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
        self._usage_bank_combo.blockSignals(True)
        prev = self._usage_bank_combo.currentData()
        self._usage_bank_combo.clear()
        self._usage_bank_combo.addItem("— Chọn ngân hàng —", userData=None)
        if items is None:
            try:
                items = self._facade.load_usage_banks()
            except (RuntimeError, ValueError, OSError):
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
        bank_id = self._usage_bank_combo.currentData()
        if bank_id is None:
            self._usage_summary_lbl.setText("Chọn ngân hàng để xem thống kê.")
            self._usage_detail_lbl.setText("Chưa có dữ liệu mức độ và CLO.")
            self._usage_table.setRowCount(0)
            return

        try:
            rows, summary = self._facade.load_usage_stats(bank_id)
        except (RuntimeError, ValueError, OSError) as exc:
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
            f"CRQ: {summary.type_breakdown.crq}"
        )
        correct_pct = f" ({100 * total_correct // total_uses}%)" if total_uses > 0 else ""
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
            clo_text = " &nbsp;&nbsp;|&nbsp;&nbsp; ".join(f"{code}: {count}" for code, count in clo_top)
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
                code_item.setToolTip(row.content[:120])
                self._usage_table.setItem(r, 0, code_item)
                self._usage_table.setItem(
                    r, 1,
                    _ucell(self._QUESTION_TYPE_LABELS.get(row.question_type, row.question_type), center=True),
                )
                self._usage_table.setItem(r, 2, _ucell(row.learning_outcome_code or "—", center=True))
                self._usage_table.setItem(r, 3, _ucell(self._display_level(row.difficulty), center=True))
                self._usage_table.setItem(r, 4, _ucell(f"{row.point_value:.1f}", center=True))
                self._usage_table.setItem(r, 5, _ucell(str(row.used_count), center=True))
                self._usage_table.setItem(r, 6, _ucell(str(row.correct_count), center=True))
                edit_item = _ucell("✎", center=True)
                edit_item.setToolTip("Sửa câu hỏi")
                edit_item.setForeground(Qt.GlobalColor.red)
                edit_item.setData(Qt.ItemDataRole.UserRole, row.question_id)
                edit_item.setData(Qt.ItemDataRole.UserRole + 1, bank_id)
                self._usage_table.setItem(r, 7, edit_item)
        finally:
            self._usage_table.setUpdatesEnabled(True)

    def _on_usage_cell_clicked(self, row: int, column: int) -> None:
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
        from ui.dialogs.problem_editor_dialog import ProblemEditorDialog
        from ui.dialogs.question_editor_dialog import QuestionEditorDialog

        try:
            q = self._facade.get_question_for_edit(question_id)
        except (RuntimeError, ValueError, OSError) as exc:
            QMessageBox.critical(self, "Lỗi", f"Không thể tải câu hỏi:\n{exc}")
            return

        if q is None:
            QMessageBox.warning(self, "Không tìm thấy", "Câu hỏi không còn tồn tại.")
            return

        dlg_class = ProblemEditorDialog if q.is_problem_question() else QuestionEditorDialog
        dlg = dlg_class(bank_id, q, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._refresh_usage_now()

    def _display_level(self, difficulty: str | None) -> str:
        raw = str(difficulty or "").strip()
        if not raw:
            return "—"
        mapping = {"easy": "Nhớ", "medium": "Hiểu", "hard": "Vận dụng"}
        return mapping.get(raw.lower(), raw)
