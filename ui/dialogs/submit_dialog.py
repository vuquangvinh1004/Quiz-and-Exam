"""Dialog for choosing submission destination and executing submission.

Shown only in EXAM mode after the user clicks 'Nộp bài'.
Practice and Study modes use a separate result-summary dialog (no submission).

Submission modes (from SubmissionSettings.mode):
  "none"   – nothing configured; user can still choose ad-hoc options here.
  "email"  – send via configured SMTP.
  "folder" – save to configured folder.
  "both"   – email + folder.

The dialog allows overriding the recipient email and/or folder for a single
submission without changing the saved settings.
"""
from __future__ import annotations

import threading
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QThread, Signal, QObject
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.domain.services.submission_service import SubmissionService, SubmissionSettings
from core.utils.error_mapper import map_exception_to_user_message
from core.utils.exceptions import SubmissionError
from core.utils.logger import get_logger
from modules.grading.result_builder import AttemptResultData

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Worker thread for async submission
# ---------------------------------------------------------------------------

class _SubmissionWorker(QObject):
    """Performs submission in a background thread."""

    finished = Signal(dict)   # result dict from SubmissionService.submit()
    error = Signal(str)
    progress = Signal(str)    # human-readable stage description

    def __init__(
        self,
        service: SubmissionService,
        data: AttemptResultData,
        cfg: SubmissionSettings,
        recipient: Optional[str],
        folder_path: Optional[str],
        gsheets_url: Optional[str] = None,
        gsheets_credentials_path: Optional[str] = None,
    ) -> None:
        super().__init__()
        self._service = service
        self._data = data
        self._cfg = cfg
        self._recipient = recipient
        self._folder_path = folder_path
        self._gsheets_url = gsheets_url
        self._gsheets_credentials_path = gsheets_credentials_path

    def run(self) -> None:
        try:
            self.progress.emit("Đang gửi bài…")
            result = self._service.submit(
                self._data,
                self._cfg,
                recipient=self._recipient,
                folder_path=self._folder_path,
            )
            # Google Sheets submission (additional, independent channel)
            if self._gsheets_url and self._gsheets_credentials_path:
                self.progress.emit("Đang ghi Google Sheets…")
                from modules.google_sheets.submitter import GoogleSheetsSubmitter
                submitter = GoogleSheetsSubmitter()
                # Pre-build rows so they can be queued on failure
                rows = submitter._build_rows(self._data)  # noqa: SLF001
                try:
                    submitter.submit(
                        self._data,
                        self._gsheets_url,
                        self._gsheets_credentials_path,
                    )
                    result["gsheets_submitted"] = True
                except Exception as exc:
                    logger.error(f"Google Sheets submission failed: {exc}")
                    result["errors"].append(
                        "Lỗi Google Sheets: "
                        f"{map_exception_to_user_message(exc)}"
                    )
                    # Attach data needed for offline enqueue
                    result["gsheets_failed_data"] = {
                        "quiz_title": self._data.quiz_title,
                        "submitter_name": self._data.submitter_name,
                        "submitter_id": self._data.submitter_id,
                        "score": self._data.score,
                        "max_score": self._data.max_score,
                        "gsheets_url": self._gsheets_url,
                        "gsheets_credentials_path": self._gsheets_credentials_path,
                        "rows": rows,
                    }
            self.finished.emit(result)
        except SubmissionError as exc:
            logger.error(f"Submission worker domain error: {exc}")
            self.error.emit(map_exception_to_user_message(exc))
        except Exception as exc:
            logger.error(f"Submission worker error: {exc}")
            self.error.emit(map_exception_to_user_message(exc))


# ---------------------------------------------------------------------------
# Main dialog
# ---------------------------------------------------------------------------

class SubmitDialog(QDialog):
    """Dialog to choose submission destination and execute EXAM submission."""

    def __init__(
        self,
        data: AttemptResultData,
        cfg: SubmissionSettings,
        service: SubmissionService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._data = data
        self._cfg = cfg
        self._service = service
        self._worker_thread: Optional[QThread] = None

        self.setWindowTitle("Nộp bài")
        self.setMinimumWidth(460)
        self.setModal(True)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint
        )
        self._build_ui()
        self._pre_fill_from_settings()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # -- Summary header --
        summary = QLabel(
            f"<b>Thông tin bài nộp</b><br>"
            f"Họ và tên : <b>{self._data.submitter_name}</b><br>"
            f"ID / Mã số: <b>{self._data.submitter_id}</b><br>"
            f"Bài kiểm tra: {self._data.quiz_title}<br>"
            f"Điểm số: <b>{self._data.score:.2f} / {self._data.max_score:.2f}</b>"
        )
        summary.setTextFormat(Qt.TextFormat.RichText)
        summary.setWordWrap(True)
        layout.addWidget(summary)

        # -- Email group --
        self._email_group = QGroupBox("Nộp bài qua Email")
        self._email_group.setCheckable(True)
        self._email_group.setChecked(False)
        email_layout = QFormLayout(self._email_group)
        email_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self._email_edit = QLineEdit()
        self._email_edit.setPlaceholderText("example@domain.com")
        email_layout.addRow("Địa chỉ người nhận:", self._email_edit)

        smtp_note = QLabel(
            '<span style="color: #888; font-size: 12px;">'
            "Cấu hình SMTP trong Cài đặt → Nộp bài."
            "</span>"
        )
        email_layout.addRow("", smtp_note)
        layout.addWidget(self._email_group)

        # -- Folder group --
        self._folder_group = QGroupBox("Lưu vào thư mục")
        self._folder_group.setCheckable(True)
        self._folder_group.setChecked(False)
        folder_layout = QHBoxLayout(self._folder_group)

        self._folder_edit = QLineEdit()
        self._folder_edit.setPlaceholderText("Chọn thư mục...")
        self._folder_edit.setReadOnly(True)
        folder_layout.addWidget(self._folder_edit, stretch=1)

        browse_btn = QPushButton("Chọn...")
        browse_btn.setFixedWidth(72)
        browse_btn.clicked.connect(self._browse_folder)
        folder_layout.addWidget(browse_btn)
        layout.addWidget(self._folder_group)

        # -- Google Sheets group --
        self._gsheets_group = QGroupBox("Nộp vào Google Sheets")
        self._gsheets_group.setCheckable(True)
        self._gsheets_group.setChecked(False)
        gsheets_layout = QFormLayout(self._gsheets_group)
        gsheets_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self._gsheets_url_edit = QLineEdit()
        self._gsheets_url_edit.setPlaceholderText(
            "https://docs.google.com/spreadsheets/d/..."
        )
        gsheets_layout.addRow("URL Google Sheet:", self._gsheets_url_edit)

        gsheets_note = QLabel(
            '<span style="color: #888; font-size: 12px;">'
            "nhập URL Google Sheet mà giáo viên đã gửi, Sheet phải được chia sẻ với tài khoản Service Account."
            "</span>"
        )
        gsheets_note.setWordWrap(True)
        gsheets_layout.addRow("", gsheets_note)
        layout.addWidget(self._gsheets_group)

        # -- Progress / status --
        self._progress = QProgressBar()
        self._progress.setRange(0, 0)   # indeterminate
        self._progress.hide()
        layout.addWidget(self._progress)

        self._status_label = QLabel("")
        self._status_label.setWordWrap(True)
        self._status_label.hide()
        layout.addWidget(self._status_label)

        # -- Buttons --
        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._submit_btn = self._buttons.button(QDialogButtonBox.StandardButton.Ok)
        self._submit_btn.setText("Nộp bài")
        self._buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Hủy")
        self._submit_btn.clicked.connect(self._on_submit)
        self._buttons.rejected.connect(self.reject)
        layout.addWidget(self._buttons)

    def _pre_fill_from_settings(self) -> None:
        """Pre-fill fields based on saved SubmissionSettings."""
        mode = self._cfg.mode
        if mode in ("email", "both"):
            self._email_group.setChecked(True)
            self._email_edit.setText(self._cfg.default_email)
        if mode in ("folder", "both"):
            self._folder_group.setChecked(True)
            self._folder_edit.setText(self._cfg.submit_folder)
        # Pre-fill Sheet URL from default; disable group if credentials not configured
        if self._cfg.gsheets_credentials_path:
            self._gsheets_url_edit.setText(self._cfg.gsheets_default_url)
        else:
            self._gsheets_group.setEnabled(False)
            self._gsheets_group.setToolTip(
                "Chưa cấu hình file credentials.json.\n"
                "Vào Cài đặt → Nộp bài → Google Sheets để thiết lập."
            )

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _browse_folder(self) -> None:
        current = self._folder_edit.text() or str(Path.home())
        folder = QFileDialog.getExistingDirectory(
            self, "Chọn thư mục lưu kết quả", current
        )
        if folder:
            self._folder_edit.setText(folder)

    def _on_submit(self) -> None:
        use_email = self._email_group.isChecked()
        use_folder = self._folder_group.isChecked()
        use_gsheets = self._gsheets_group.isChecked() and self._gsheets_group.isEnabled()

        if not use_email and not use_folder and not use_gsheets:
            self._show_status(
                "⚠ Vui lòng chọn ít nhất một phương thức nộp bài.",
                error=True,
            )
            return

        if use_email and not self._email_edit.text().strip():
            self._show_status("⚠ Vui lòng nhập địa chỉ email người nhận.", error=True)
            return

        if use_folder and not self._folder_edit.text().strip():
            self._show_status("⚠ Vui lòng chọn thư mục lưu file.", error=True)
            return

        if use_gsheets and not self._gsheets_url_edit.text().strip():
            self._show_status("⚠ Vui lòng nhập URL Google Sheet.", error=True)
            return

        # Build effective settings for email/folder (unchanged logic)
        effective_cfg = SubmissionSettings(
            mode=(
                "both"   if (use_email and use_folder)
                else "email"  if use_email
                else "folder" if use_folder
                else "none"
            ),
            default_email=self._cfg.default_email,
            smtp_server=self._cfg.smtp_server,
            smtp_port=self._cfg.smtp_port,
            smtp_user=self._cfg.smtp_user,
            smtp_password=self._cfg.smtp_password,
            smtp_sender=self._cfg.smtp_sender,
            smtp_use_tls=self._cfg.smtp_use_tls,
            submit_folder=self._folder_edit.text().strip(),
        )
        recipient = self._email_edit.text().strip() if use_email else None
        folder_path = self._folder_edit.text().strip() if use_folder else None
        gsheets_url = self._gsheets_url_edit.text().strip() if use_gsheets else None
        gsheets_creds = self._cfg.gsheets_credentials_path if use_gsheets else None

        self._start_submission(effective_cfg, recipient, folder_path, gsheets_url, gsheets_creds)

    def _start_submission(
        self,
        cfg: SubmissionSettings,
        recipient: Optional[str],
        folder_path: Optional[str],
        gsheets_url: Optional[str] = None,
        gsheets_credentials_path: Optional[str] = None,
    ) -> None:
        """Start background submission thread."""
        self._submit_btn.setEnabled(False)
        self._progress.show()
        self._show_status("Đang xử lý...", error=False)

        self._worker_thread = QThread(self)
        worker = _SubmissionWorker(
            self._service, self._data, cfg, recipient, folder_path,
            gsheets_url=gsheets_url,
            gsheets_credentials_path=gsheets_credentials_path,
        )
        worker.moveToThread(self._worker_thread)
        self._worker_thread.started.connect(worker.run)
        worker.progress.connect(self._on_progress)
        worker.finished.connect(self._on_submission_done)
        worker.error.connect(self._on_submission_error)
        worker.finished.connect(self._worker_thread.quit)
        worker.error.connect(self._worker_thread.quit)
        self._worker_thread.start()

    def _on_progress(self, msg: str) -> None:
        """Update the status label with the current submission stage."""
        self._show_status(msg, error=False)

    def _on_submission_done(self, result: dict) -> None:
        self._progress.hide()
        errors: list[str] = result.get("errors", [])  # type: ignore[assignment]
        folder_path: Optional[Path] = result.get("folder_path")  # type: ignore[assignment]
        email_sent: bool = result.get("email_sent", False)  # type: ignore[assignment]
        gsheets_submitted: bool = result.get("gsheets_submitted", False)  # type: ignore[assignment]
        gsheets_failed_data: Optional[dict] = result.get("gsheets_failed_data")  # type: ignore[assignment]

        # Separate GSheets errors from blocking errors so email/folder success
        # is still reported and the user is offered enqueue for GSheets.
        gsheets_errors = [e for e in errors if "Google Sheets" in e]
        other_errors = [e for e in errors if "Google Sheets" not in e]

        if other_errors:
            msg = "Có lỗi xảy ra:\n" + "\n".join(other_errors)
            self._show_status(f"⚠ {msg}", error=True)
            self._submit_btn.setEnabled(True)
            return

        lines = ["✓ Nộp bài thành công!"]
        if folder_path:
            lines.append(f"Đã lưu: {folder_path}")
        if email_sent:
            lines.append("Đã gửi email.")
        if gsheets_submitted:
            lines.append("Đã ghi vào Google Sheets.")

        if gsheets_errors:
            lines.append("⚠ Lỗi Google Sheets — chưa ghi được vào Sheet.")

        self._show_status("\n".join(lines), error=bool(gsheets_errors))

        self._submit_btn.setEnabled(False)
        close_btn = self._buttons.button(QDialogButtonBox.StandardButton.Cancel)
        close_btn.setText("Đóng")

        # Offer to save failed GSheets submission to offline queue
        if gsheets_failed_data:
            self._offer_gsheets_enqueue(gsheets_failed_data)

    def _on_submission_error(self, error_msg: str) -> None:
        self._progress.hide()
        self._show_status(f"⚠ Lỗi: {error_msg}", error=True)
        self._submit_btn.setEnabled(True)

    def _offer_gsheets_enqueue(self, failed_data: dict) -> None:
        """Ask the user whether to save the failed GSheets rows to the retry queue."""
        from PySide6.QtWidgets import QMessageBox

        reply = QMessageBox.question(
            self,
            "Lưu vào hàng chờ",
            "Không thể ghi vào Google Sheets lúc này.\n\n"
            "Bạn có muốn lưu bài nộp vào hàng chờ để nộp lại sau không?\n"
            "(Xem lại trong Lịch sử → Nộp lại GSheets)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                from modules.google_sheets.pending_queue import PendingGSheetsQueue
                PendingGSheetsQueue().push(
                    quiz_title=failed_data["quiz_title"],
                    submitter_name=failed_data["submitter_name"],
                    submitter_id=failed_data["submitter_id"],
                    score=failed_data["score"],
                    max_score=failed_data["max_score"],
                    gsheets_url=failed_data["gsheets_url"],
                    gsheets_credentials_path=failed_data["gsheets_credentials_path"],
                    rows=failed_data["rows"],
                )
                self._show_status(
                    "\n".join([
                        self._status_label.text()
                        .replace("<br>", "\n").replace(
                            '<span style="color: #c0392b;">', ""
                        ).replace('<span style="color: #27ae60;">', "").replace(
                            "</span>", ""
                        ),
                        "✓ Đã lưu vào hàng chờ.",
                    ]),
                    error=False,
                )
            except Exception as exc:
                logger.error(f"Failed to enqueue pending GSheets item: {exc}")
                self._show_status(
                    "⚠ Không thể lưu vào hàng chờ: "
                    f"{map_exception_to_user_message(exc)}",
                    error=True,
                )

    def _show_status(self, msg: str, *, error: bool) -> None:
        colour = "#c0392b" if error else "#27ae60"
        self._status_label.setText(
            f'<span style="color: {colour};">{msg.replace(chr(10), "<br>")}</span>'
        )
        self._status_label.setTextFormat(Qt.TextFormat.RichText)
        self._status_label.show()
