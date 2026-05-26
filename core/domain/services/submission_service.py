"""Submission service: email and local-folder delivery of exam results.

Settings are persisted in the app_settings table using well-known keys.
SMTP credentials are stored locally in SQLite — acceptable for a local-first
desktop app with no network transport of the DB file itself.

Business rules (ARCHITECTURE §7.2 / §5.6):
- Only EXAM mode triggers real submission (folder or email).
- PRACTICE / STUDY modes show a summary dialog, not a submission.
- This service only handles EXAM submission; caller must enforce mode check.
"""
from __future__ import annotations

import email.mime.application
import email.mime.multipart
import email.mime.text
import smtplib
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from core.database.models import AppSetting
from core.utils.exceptions import SubmissionConfigError, SubmissionDeliveryError
from core.utils.logger import get_logger
from modules.grading.result_builder import AttemptResultData, ExamResultExporter

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Well-known setting keys
# ---------------------------------------------------------------------------
_KEY_MODE = "submission.mode"           # "none" | "email" | "folder" | "both"
_KEY_DEFAULT_EMAIL = "submission.default_email"
_KEY_SMTP_SERVER = "submission.smtp_server"
_KEY_SMTP_PORT = "submission.smtp_port"
_KEY_SMTP_USER = "submission.smtp_user"
_KEY_SMTP_PASSWORD = "submission.smtp_password"
_KEY_SMTP_SENDER = "submission.smtp_sender"
_KEY_SUBMIT_FOLDER = "submission.submit_folder"
_KEY_SMTP_USE_TLS = "submission.smtp_use_tls"   # "true" | "false"
_KEY_GSHEETS_CREDENTIALS = "submission.gsheets_credentials_path"
_KEY_GSHEETS_DEFAULT_URL = "submission.gsheets_default_url"

ALL_KEYS = [
    _KEY_MODE, _KEY_DEFAULT_EMAIL, _KEY_SMTP_SERVER, _KEY_SMTP_PORT,
    _KEY_SMTP_USER, _KEY_SMTP_PASSWORD, _KEY_SMTP_SENDER, _KEY_SUBMIT_FOLDER,
    _KEY_SMTP_USE_TLS, _KEY_GSHEETS_CREDENTIALS, _KEY_GSHEETS_DEFAULT_URL,
]


# ---------------------------------------------------------------------------
# Settings dataclass
# ---------------------------------------------------------------------------

@dataclass
class SubmissionSettings:
    """Holds all configurable parameters for the submission feature."""

    mode: str = "none"          # "none" | "email" | "folder" | "both"
    default_email: str = ""     # default recipient
    smtp_server: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_sender: str = ""       # display sender address
    submit_folder: str = ""
    smtp_use_tls: bool = True
    gsheets_credentials_path: str = ""   # path to Service Account JSON key
    gsheets_default_url: str = ""        # default Sheet URL (teacher pre-fills)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class SubmissionService:
    """Handles persistence of settings and execution of submission actions."""

    def __init__(self) -> None:
        self._exporter = ExamResultExporter()

    # ------------------------------------------------------------------
    # Settings persistence
    # ------------------------------------------------------------------

    def load_settings(self, session: Session) -> SubmissionSettings:
        """Load submission settings from app_settings table."""
        rows = (
            session.query(AppSetting)
            .filter(AppSetting.setting_key.in_(ALL_KEYS))
            .all()
        )
        kv = {r.setting_key: (r.setting_value or "") for r in rows}
        return SubmissionSettings(
            mode=kv.get(_KEY_MODE, "none"),
            default_email=kv.get(_KEY_DEFAULT_EMAIL, ""),
            smtp_server=kv.get(_KEY_SMTP_SERVER, ""),
            smtp_port=int(kv.get(_KEY_SMTP_PORT, "587") or "587"),
            smtp_user=kv.get(_KEY_SMTP_USER, ""),
            smtp_password=kv.get(_KEY_SMTP_PASSWORD, ""),
            smtp_sender=kv.get(_KEY_SMTP_SENDER, ""),
            submit_folder=kv.get(_KEY_SUBMIT_FOLDER, ""),
            smtp_use_tls=kv.get(_KEY_SMTP_USE_TLS, "true").lower() != "false",
            gsheets_credentials_path=kv.get(_KEY_GSHEETS_CREDENTIALS, ""),
            gsheets_default_url=kv.get(_KEY_GSHEETS_DEFAULT_URL, ""),
        )

    def save_settings(self, session: Session, cfg: SubmissionSettings) -> None:
        """Upsert submission settings into app_settings table."""
        pairs: list[tuple[str, str]] = [
            (_KEY_MODE, cfg.mode),
            (_KEY_DEFAULT_EMAIL, cfg.default_email),
            (_KEY_SMTP_SERVER, cfg.smtp_server),
            (_KEY_SMTP_PORT, str(cfg.smtp_port)),
            (_KEY_SMTP_USER, cfg.smtp_user),
            (_KEY_SMTP_PASSWORD, cfg.smtp_password),
            (_KEY_SMTP_SENDER, cfg.smtp_sender),
            (_KEY_SUBMIT_FOLDER, cfg.submit_folder),
            (_KEY_SMTP_USE_TLS, "true" if cfg.smtp_use_tls else "false"),
            (_KEY_GSHEETS_CREDENTIALS, cfg.gsheets_credentials_path),
            (_KEY_GSHEETS_DEFAULT_URL, cfg.gsheets_default_url),
        ]
        existing = {
            r.setting_key: r
            for r in session.query(AppSetting)
            .filter(AppSetting.setting_key.in_([p[0] for p in pairs]))
            .all()
        }
        for key, value in pairs:
            if key in existing:
                existing[key].setting_value = value
            else:
                session.add(AppSetting(setting_key=key, setting_value=value))

    # ------------------------------------------------------------------
    # Filename helper
    # ------------------------------------------------------------------

    @staticmethod
    def build_filename(data: AttemptResultData) -> str:
        """Build a safe filename from submitter and quiz information."""

        def _safe(text: str) -> str:
            return "".join(c if c.isalnum() or c in " _-" else "_" for c in text).strip()

        ts = data.submitted_at.strftime("%Y%m%d_%H%M%S")
        return f"KetQua_{_safe(data.submitter_name)}_{_safe(data.quiz_title)}_{ts}.xlsx"

    # ------------------------------------------------------------------
    # Folder delivery
    # ------------------------------------------------------------------

    def submit_to_folder(
        self,
        data: AttemptResultData,
        folder_path: str,
    ) -> Path:
        """Save an Excel result file to *folder_path*. Returns the saved path."""
        if not folder_path:
            raise SubmissionConfigError("Chưa chọn thư mục để lưu file kết quả.")
        folder = Path(folder_path)
        try:
            folder.mkdir(parents=True, exist_ok=True)
            filename = self.build_filename(data)
            dest = folder / filename
            excel_bytes = self._exporter.build_excel(data)
            dest.write_bytes(excel_bytes)
        except OSError as exc:
            raise SubmissionDeliveryError(
                f"Không thể ghi file kết quả vào thư mục: {folder_path}"
            ) from exc
        logger.info(f"Submission saved to folder: {dest}")
        return dest

    # ------------------------------------------------------------------
    # Email delivery
    # ------------------------------------------------------------------

    def submit_via_email(
        self,
        data: AttemptResultData,
        cfg: SubmissionSettings,
        recipient: str,
    ) -> None:
        """Send Excel result as an email attachment to *recipient*.

        Raises:
            SubmissionConfigError: if required configuration is missing.
            SubmissionDeliveryError: on mail server and delivery errors.
        """
        if not cfg.smtp_server:
            raise SubmissionConfigError(
                "Chưa cấu hình SMTP server.\n"
                "Vào Cài đặt → Nộp bài để thiết lập."
            )
        recipient = recipient.strip()
        if not recipient:
            raise SubmissionConfigError("Địa chỉ email người nhận không được trống.")

        excel_bytes = self._exporter.build_excel(data)
        filename = self.build_filename(data)

        msg = email.mime.multipart.MIMEMultipart()
        sender = (cfg.smtp_sender.strip() or cfg.smtp_user.strip()) or "noreply@quizapp"
        msg["From"] = sender
        msg["To"] = recipient
        msg["Subject"] = (
            f"[Kết quả kiểm tra] {data.quiz_title} – {data.submitter_name}"
        )

        body = (
            f"Xin chào,\n\n"
            f"Đây là kết quả làm bài kiểm tra:\n"
            f"  Họ và tên  : {data.submitter_name}\n"
            f"  ID / Mã số : {data.submitter_id}\n"
            f"  Bài kiểm tra: {data.quiz_title}\n"
            f"  Điểm số    : {data.score:.2f} / {data.max_score:.2f}\n"
            f"  Số câu đúng: {data.correct_count}\n"
            f"  Số câu sai : {data.incorrect_count}\n"
            f"  Số bỏ qua  : {data.skipped_count}\n\n"
            f"Kết quả chi tiết đính kèm trong file Excel.\n\n"
            f"Trân trọng,\nQuiz Desktop App"
        )
        msg.attach(email.mime.text.MIMEText(body, "plain", "utf-8"))

        attachment = email.mime.application.MIMEApplication(
            excel_bytes, Name=filename
        )
        attachment["Content-Disposition"] = f'attachment; filename="{filename}"'
        msg.attach(attachment)

        try:
            with smtplib.SMTP(cfg.smtp_server, cfg.smtp_port, timeout=30) as smtp:
                smtp.ehlo()
                if cfg.smtp_use_tls:
                    smtp.starttls()
                    smtp.ehlo()
                if cfg.smtp_user:
                    smtp.login(cfg.smtp_user, cfg.smtp_password)
                smtp.sendmail(sender, [recipient], msg.as_bytes())
        except (smtplib.SMTPException, OSError) as exc:
            raise SubmissionDeliveryError(
                "Không thể gửi email kết quả qua SMTP."
            ) from exc

        logger.info(f"Submission emailed to: {recipient}")

    # ------------------------------------------------------------------
    # Combined submission (mode="both")
    # ------------------------------------------------------------------

    def submit(
        self,
        data: AttemptResultData,
        cfg: SubmissionSettings,
        *,
        recipient: Optional[str] = None,
        folder_path: Optional[str] = None,
    ) -> dict[str, object]:
        """Execute submission according to *cfg.mode*.

        Returns a result dict with keys 'folder_path', 'email_sent', 'errors'.
        """
        result: dict[str, object] = {
            "folder_path": None,
            "email_sent": False,
            "errors": [],
        }
        effective_mode = cfg.mode
        send_email = effective_mode in ("email", "both")
        save_folder = effective_mode in ("folder", "both")

        if save_folder:
            target_folder = folder_path or cfg.submit_folder
            try:
                saved = self.submit_to_folder(data, target_folder)
                result["folder_path"] = saved
            except (SubmissionConfigError, SubmissionDeliveryError) as exc:
                logger.error(f"Folder submission failed: {exc}")
                result["errors"].append(f"Lỗi lưu thư mục: {exc}")

        if send_email:
            target_email = (recipient or cfg.default_email).strip()
            try:
                self.submit_via_email(data, cfg, target_email)
                result["email_sent"] = True
            except (SubmissionConfigError, SubmissionDeliveryError) as exc:
                logger.error(f"Email submission failed: {exc}")
                result["errors"].append(f"Lỗi gửi email: {exc}")

        return result
