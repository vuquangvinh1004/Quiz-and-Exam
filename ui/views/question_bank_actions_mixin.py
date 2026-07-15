"""CRUD and helper actions for QuestionBankView."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QDialog, QListWidgetItem, QMessageBox

from core.database.models import Question
from core.utils.latex_rendering import render_inline_latex_text
from core.utils.logger import get_logger
from ui.dialogs.bank_meta_dialog import BankMetaDialog
from ui.dialogs.problem_editor_dialog import ProblemEditorDialog
from ui.dialogs.question_editor_dialog import QuestionEditorDialog
from ui.facades.question_bank_facade import BankMetaData
from ui.utils.error_handler import show_critical_error
from ui.views.question_bank_shared import _LEGACY_DIFFICULTY_TO_LEVEL, _TYPE_TABLE_LABEL, cell

_logger = get_logger(__name__)


class QuestionBankActionsMixin:
    def _load_banks(self) -> None:
        prev_bank_id = self._current_bank_id
        self._bank_list.blockSignals(True)
        self._bank_list.clear()
        try:
            bank_data = self._facade.list_bank_overview_items()
        except Exception:
            bank_data = []
        for row in bank_data:
            item = QListWidgetItem(f"{row['name']}\n{self._format_bank_context(row)}")
            item.setData(Qt.ItemDataRole.UserRole, row["id"])
            item.setData(Qt.ItemDataRole.UserRole + 1, row["name"])
            item.setData(Qt.ItemDataRole.UserRole + 2, self._format_bank_context(row))
            item.setToolTip(self._format_bank_tooltip(row))
            self._bank_list.addItem(item)
        self._bank_list.blockSignals(False)

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
        self._q_table.setSortingEnabled(False)
        self._q_table.setRowCount(len(questions))
        for r, q in enumerate(questions):
            self._q_table.setItem(r, 0, cell(str(r + 1), center=True))
            self._q_table.setItem(r, 1, cell(q.question_code or ""))
            preview = render_inline_latex_text((q.content or ""))[:180]
            content_item = cell(preview)
            content_item.setToolTip(render_inline_latex_text(q.content or ""))
            self._q_table.setItem(r, 2, content_item)
            self._q_table.setItem(r, 3, cell(q.category or "", center=True))
            self._q_table.setItem(r, 4, cell(q.learning_outcome_code or "", center=True))
            self._q_table.setItem(r, 5, cell(self._display_level(q.difficulty), center=True))
            type_label = _TYPE_TABLE_LABEL.get(q.question_type, q.question_type)
            self._q_table.setItem(r, 6, cell(type_label, center=True))
            self._q_table.setItem(r, 7, cell(str(q.point_value or 1.0), center=True))
            if q.is_active:
                status_item = cell("✓ Đang dùng", center=True)
                status_item.setForeground(QColor("#27ae60"))
            else:
                status_item = cell("✗ Không dùng", center=True)
                status_item.setForeground(QColor("#c0392b"))
            status_item.setToolTip(status_item.text())
            self._q_table.setItem(r, 8, status_item)
            self._q_table.item(r, 0).setData(Qt.ItemDataRole.UserRole, q.id)
        bank_label = ""
        if self._current_bank_id:
            item = self._bank_list.currentItem()
            if item:
                bank_label = f"「{item.data(Qt.ItemDataRole.UserRole + 1) or item.text()}」 – "
        self._status_lbl.setText(
            f"{bank_label}{len(questions)} câu hỏi"
            + (" (đang lọc)" if self._search_edit.text() or self._type_filter.currentData() or self._diff_filter.currentData() else "")
        )
        self._q_table.setSortingEnabled(True)

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
            for i in range(self._bank_list.count()):
                if self._bank_list.item(i).data(Qt.ItemDataRole.UserRole) == new_id:
                    self._bank_list.setCurrentRow(i)
                    break
        except ValueError as exc:
            QMessageBox.warning(self, "Lỗi", str(exc))
        except Exception as exc:
            show_critical_error(self, "Lỗi", "Không thể tạo ngân hàng.", exc=exc)

    def _rename_bank(self) -> None:
        item = self._bank_list.currentItem()
        if item is None:
            QMessageBox.information(self, "Thông báo", "Chưa chọn ngân hàng.")
            return
        bid = item.data(Qt.ItemDataRole.UserRole)
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

    def _add_question(self) -> None:
        if self._current_bank_id is None:
            QMessageBox.information(self, "Thông báo", "Vui lòng chọn ngân hàng trước.")
            return
        dlg = QuestionEditorDialog(self._current_bank_id, parent=self)
        if dlg.exec() == QuestionEditorDialog.DialogCode.Accepted:
            self._refresh_questions()

    def _add_crq(self) -> None:
        if self._current_bank_id is None:
            QMessageBox.information(self, "Thông báo", "Vui lòng chọn ngân hàng trước.")
            return
        try:
            dlg = ProblemEditorDialog(self._current_bank_id, parent=self)
            if dlg.exec() == ProblemEditorDialog.DialogCode.Accepted:
                self._refresh_questions()
        except (ValueError, RuntimeError, OSError, TypeError, AttributeError) as exc:
            show_critical_error(
                self,
                "Lỗi",
                "Không thể mở cửa sổ thêm CRQ.",
                exc=exc,
            )

    def _add_problem(self) -> None:
        self._add_crq()

    def _edit_question(self) -> None:
        q = self._selected_question()
        if q is None:
            return
        dlg_class = ProblemEditorDialog if q.is_crq_question() else QuestionEditorDialog
        try:
            dlg = dlg_class(self._current_bank_id or q.bank_id, q, parent=self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                self._refresh_questions()
        except (ValueError, RuntimeError, OSError, TypeError, AttributeError) as exc:
            show_critical_error(
                self,
                "Lỗi",
                "Không thể mở cửa sổ sửa CRQ.",
                exc=exc,
            )

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

    def _selected_question(self) -> Question | None:
        row = self._q_table.currentRow()
        if row < 0 or row >= len(self._questions):
            QMessageBox.information(self, "Thông báo", "Chưa chọn câu hỏi.")
            return None
        qid = self._q_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        try:
            return self._facade.get_question_for_edit(qid)
        except (RuntimeError, OSError, ValueError) as exc:
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

    def _on_refresh_clicked(self) -> None:
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
