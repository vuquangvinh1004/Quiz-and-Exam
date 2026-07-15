"""Picker dialog for reusable problem rubric templates."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from core.domain.services.question_service_types import ProblemRubricTemplateSummary
from core.utils.latex_rendering import render_inline_latex_html
from ui.facades.question_bank_facade import QuestionBankFacade


class ProblemTemplatePickerDialog(QDialog):
    """Bank-specific rubric template picker with preview and management actions."""

    def __init__(
        self,
        templates: list[ProblemRubricTemplateSummary],
        parent: QWidget | None = None,
        *,
        facade: QuestionBankFacade | None = None,
        bank_id: int | None = None,
    ) -> None:
        super().__init__(parent)
        self._templates = templates
        self._facade = facade
        self._bank_id = bank_id
        self._selected_template_id: int | None = None
        self.setWindowTitle("Dùng MẪU")
        self.setMinimumSize(620, 460)
        self._build_ui()
        self._populate()

    @property
    def selected_template_id(self) -> int | None:
        return self._selected_template_id

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(10)

        self._list = QListWidget()
        self._list.itemSelectionChanged.connect(self._update_preview)
        self._list.itemDoubleClicked.connect(lambda *_: self.accept())
        root.addWidget(self._list, stretch=1)

        self._preview = QTextBrowser()
        self._preview.setOpenExternalLinks(False)
        self._preview.setHtml("<div style='color:#777;'>Chọn một mẫu để xem chi tiết.</div>")
        self._preview.setMinimumHeight(150)
        self._preview.setStyleSheet(
            "QTextBrowser { color: #555; background: #fafafa; border: 1px solid #ddd; }"
            "QTextBrowser .math { font-weight: 600; }"
        )
        root.addWidget(self._preview)

        manage_row = QHBoxLayout()
        self._rename_btn = QPushButton("Đổi tên")
        self._rename_btn.clicked.connect(self._rename_current_template)
        self._delete_btn = QPushButton("Xóa")
        self._delete_btn.clicked.connect(self._delete_current_template)
        manage_row.addWidget(self._rename_btn)
        manage_row.addWidget(self._delete_btn)
        manage_row.addStretch()
        root.addLayout(manage_row)

        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.button(QDialogButtonBox.StandardButton.Ok).setText("Dùng")
        btn_box.button(QDialogButtonBox.StandardButton.Cancel).setText("Hủy")
        btn_box.accepted.connect(self._on_accept)
        btn_box.rejected.connect(self.reject)
        root.addWidget(btn_box)

        self._sync_manage_buttons()

    def _populate(self) -> None:
        self._list.clear()
        for template in self._templates:
            label = self._template_label(template)
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, template.template_id)
            item.setToolTip(label)
            self._list.addItem(item)
        if self._list.count() > 0:
            self._list.setCurrentRow(0)
        self._sync_manage_buttons()

    def _sync_manage_buttons(self) -> None:
        enabled = self._current_template() is not None and self._facade is not None and self._bank_id is not None
        self._rename_btn.setEnabled(enabled)
        self._delete_btn.setEnabled(enabled)

    def _current_template(self) -> ProblemRubricTemplateSummary | None:
        item = self._list.currentItem()
        if item is None:
            return None
        template_id = item.data(Qt.ItemDataRole.UserRole)
        return next((t for t in self._templates if t.template_id == template_id), None)

    def _template_label(self, template: ProblemRubricTemplateSummary) -> str:
        return f"{template.name}  |  {template.row_count} hàng  |  {template.total_score:g} điểm"

    def _format_preview(self, template: ProblemRubricTemplateSummary) -> str:
        lines = [
            "<div style='font-family: Segoe UI, sans-serif; font-size: 11.5pt; color: #1f2937;'>",
            "<div style='font-weight:700; margin-bottom:6px;'>Xem trước mẫu rubric</div>",
            f"<div style='margin-bottom:4px;'><b>Tên mẫu:</b> {render_inline_latex_html(template.name)}</div>",
            f"<div style='margin-bottom:4px;'><b>Số hàng:</b> {template.row_count}</div>",
            f"<div style='margin-bottom:8px;'><b>Tổng điểm:</b> {template.total_score:g}</div>",
            "<div style='font-weight:700; margin-bottom:4px;'>Chi tiết:</div>",
        ]
        if self._facade is None:
            lines.append("<div style='color:#777;font-style:italic;'>(Không có dữ liệu chi tiết)</div>")
            lines.append("</div>")
            return "\n".join(lines)
        data = self._facade.get_problem_template(template.template_id)
        if data is None:
            lines.append("<div style='color:#777;font-style:italic;'>(Mẫu đã không còn tồn tại)</div>")
            lines.append("</div>")
            return "\n".join(lines)
        if not data.rows:
            lines.append("<div style='color:#777;font-style:italic;'>(Không có hàng nào)</div>")
            lines.append("</div>")
            return "\n".join(lines)
        lines.append("<table style='width:100%; border-collapse:collapse;'>")
        lines.append(
            "<tr><th style='border:1px solid #ddd; padding:6px; background:#eef3f9;'>#</th>"
            "<th style='border:1px solid #ddd; padding:6px; background:#eef3f9;'>Mã</th>"
            "<th style='border:1px solid #ddd; padding:6px; background:#eef3f9;'>Nội dung</th>"
            "<th style='border:1px solid #ddd; padding:6px; background:#eef3f9;'>Điểm</th></tr>"
        )
        for idx, row in enumerate(data.rows, start=1):
            if isinstance(row, dict):
                marker = str(row.get("marker", "") or "").strip()
                content = str(row.get("content", "") or "").strip()
                raw_score = row.get("score", None)
            else:
                marker = str(getattr(row, "marker", "") or "").strip()
                content = str(getattr(row, "content", "") or "").strip()
                raw_score = getattr(row, "score", None)
            marker = marker or "-"
            content = content or "(trống)"
            score = f"{float(raw_score or 0.0):g}"
            lines.append(
                "<tr>"
                f"<td style='border:1px solid #ddd; padding:6px; text-align:center;'>{idx}</td>"
                f"<td style='border:1px solid #ddd; padding:6px; text-align:center;'>{render_inline_latex_html(marker)}</td>"
                f"<td style='border:1px solid #ddd; padding:6px;'>{render_inline_latex_html(content)}</td>"
                f"<td style='border:1px solid #ddd; padding:6px; text-align:center; color:#c0392b; font-weight:700;'>{score}</td>"
                "</tr>"
            )
        lines.append("</table></div>")
        return "\n".join(lines)

    def _update_preview(self) -> None:
        template = self._current_template()
        if template is None:
            self._preview.setHtml("<div style='color:#777;'>Chọn một mẫu để xem chi tiết.</div>")
            self._sync_manage_buttons()
            return
        self._preview.setHtml(self._format_preview(template))
        self._sync_manage_buttons()

    def _rename_current_template(self) -> None:
        template = self._current_template()
        if template is None or self._facade is None:
            return
        new_name, accepted = QInputDialog.getText(
            self,
            "Đổi tên MẪU",
            "Tên mẫu mới:",
            text=template.name,
        )
        if not accepted:
            return
        try:
            renamed = self._facade.rename_problem_template(template.template_id, new_name)
        except ValueError as exc:
            QMessageBox.warning(self, "Lỗi đổi tên", str(exc))
            return
        except (RuntimeError, OSError) as exc:
            QMessageBox.critical(self, "Lỗi đổi tên", f"Không thể đổi tên mẫu:\n{exc}")
            return

        for idx, row in enumerate(self._templates):
            if row.template_id == template.template_id:
                self._templates[idx] = renamed
                break
        self._populate()
        self._select_template(renamed.template_id)

    def _delete_current_template(self) -> None:
        template = self._current_template()
        if template is None or self._facade is None:
            return
        answer = QMessageBox.question(
            self,
            "Xóa MẪU",
            f"Xóa mẫu '{template.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self._facade.delete_problem_template(template.template_id)
        except ValueError as exc:
            QMessageBox.warning(self, "Lỗi xóa mẫu", str(exc))
            return
        except (RuntimeError, OSError) as exc:
            QMessageBox.critical(self, "Lỗi xóa mẫu", f"Không thể xóa mẫu:\n{exc}")
            return

        self._templates = [row for row in self._templates if row.template_id != template.template_id]
        self._populate()

    def _select_template(self, template_id: int) -> None:
        for idx in range(self._list.count()):
            item = self._list.item(idx)
            if item is not None and item.data(Qt.ItemDataRole.UserRole) == template_id:
                self._list.setCurrentRow(idx)
                return

    def _on_accept(self) -> None:
        item = self._list.currentItem()
        if item is None:
            return
        self._selected_template_id = item.data(Qt.ItemDataRole.UserRole)
        self.accept()


__all__ = ["ProblemTemplatePickerDialog"]
