"""Dialog for configuring submission settings (SMTP, default email, folder).

Accessible from SettingsView and also from within SubmitDialog via a link.
Persists settings to the app_settings table via SubmissionService.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.utils.error_mapper import map_exception_to_user_message
from core.domain.services.submission_service import SubmissionSettings
from core.utils.logger import get_logger
from ui.facades.submission_settings_facade import SubmissionSettingsFacade
from ui.styles import apply_checkbox_style

logger = get_logger(__name__)


class SubmissionSettingsDialog(QDialog):
    """Configure how and where quiz results are submitted after an EXAM."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._facade = SubmissionSettingsFacade()
        self.setWindowTitle("Cài đặt Nộp bài")
        self.setMinimumWidth(680)
        self.setModal(True)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint
        )
        self._cfg = self._load_settings()
        self._build_ui()
        self._populate_fields()

    # ------------------------------------------------------------------
    # Settings persistence
    # ------------------------------------------------------------------

    def _load_settings(self) -> SubmissionSettings:
        try:
            return self._facade.load_settings()
        except Exception as exc:
            logger.warning(f"Could not load submission settings: {exc}")
            return SubmissionSettings()

    def _save_settings(self, cfg: SubmissionSettings) -> None:
        self._facade.save_settings(cfg)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        tabs = QTabWidget()
        tabs.addTab(self._build_mode_tab(), "Phương thức nộp")
        tabs.addTab(self._build_email_tab(), "Cài đặt Email")
        tabs.addTab(self._build_folder_tab(), "Cài đặt Thư mục")
        tabs.addTab(self._build_gsheets_tab(), "Google Sheets")
        layout.addWidget(tabs)

        # Status label
        self._status_label = QLabel("")
        self._status_label.hide()
        layout.addWidget(self._status_label)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Lưu cài đặt")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Hủy")
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _build_mode_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(8)

        layout.addWidget(QLabel(
            "Chọn phương thức nộp bài mặc định sau khi hoàn thành bài kiểm tra:"
        ))

        self._mode_none = QRadioButton("Không nộp bài (chỉ hiển thị kết quả)")
        self._mode_email = QRadioButton("Nộp qua Email")
        self._mode_folder = QRadioButton("Lưu vào Thư mục trên máy tính")
        self._mode_both = QRadioButton("Cả Email và Thư mục")

        for btn in (self._mode_none, self._mode_email, self._mode_folder, self._mode_both):
            layout.addWidget(btn)

        note = QLabel(
            '<i style="color: #666;">Lưu ý: Cài đặt này chỉ áp dụng cho chế độ '
            "<b>Kiểm tra</b>. Luyện tập và Học tập chỉ hiển thị kết quả tổng hợp.</i>"
        )
        note.setTextFormat(Qt.TextFormat.RichText)
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch()
        return widget

    def _build_email_tab(self) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._default_email_edit = QLineEdit()
        self._default_email_edit.setPlaceholderText("giaovien@example.com")
        form.addRow("Email người nhận mặc định:", self._default_email_edit)

        form.addRow(QLabel(""))  # spacer

        form.addRow(QLabel("<b>Cấu hình SMTP:</b>"))

        self._smtp_server_edit = QLineEdit()
        self._smtp_server_edit.setPlaceholderText("smtp.gmail.com")
        form.addRow("SMTP Server:", self._smtp_server_edit)

        self._smtp_port_spin = QSpinBox()
        self._smtp_port_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self._smtp_port_spin.setRange(1, 65535)
        self._smtp_port_spin.setValue(587)
        form.addRow("SMTP Port:", self._smtp_port_spin)

        self._smtp_tls_check = QCheckBox("Dùng STARTTLS (khuyến nghị)")
        apply_checkbox_style(self._smtp_tls_check)
        form.addRow("", self._smtp_tls_check)

        self._smtp_user_edit = QLineEdit()
        self._smtp_user_edit.setPlaceholderText("your.account@gmail.com")
        form.addRow("Tên đăng nhập:", self._smtp_user_edit)

        self._smtp_password_edit = QLineEdit()
        self._smtp_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._smtp_password_edit.setPlaceholderText("App password / Mật khẩu SMTP")
        form.addRow("Mật khẩu:", self._smtp_password_edit)

        self._smtp_sender_edit = QLineEdit()
        self._smtp_sender_edit.setPlaceholderText("Tên hiển thị <address@domain.com>")
        form.addRow("Địa chỉ gửi:", self._smtp_sender_edit)

        hint = QLabel(
            '<span style="color: #888; font-size: 12px;">'
            "Gmail: Bật xác thực 2 bước, dùng App Password thay mật khẩu thông thường."
            "</span>"
        )
        hint.setWordWrap(True)
        form.addRow("", hint)

        # Test button
        test_row = QHBoxLayout()
        self._test_btn = QPushButton("Kiểm tra kết nối SMTP")
        self._test_btn.clicked.connect(self._test_smtp)
        self._test_result = QLabel("")
        test_row.addWidget(self._test_btn)
        test_row.addWidget(self._test_result, stretch=1)
        form.addRow("", test_row)

        return widget

    def _build_folder_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        row = QHBoxLayout()
        self._folder_edit = QLineEdit()
        self._folder_edit.setPlaceholderText("Chọn thư mục mặc định để lưu kết quả...")
        self._folder_edit.setReadOnly(True)
        row.addWidget(self._folder_edit, stretch=1)

        browse_btn = QPushButton("Chọn thư mục...")
        browse_btn.setMinimumWidth(132)
        browse_btn.clicked.connect(self._browse_folder)
        row.addWidget(browse_btn)
        layout.addLayout(row)

        note = QLabel(
            "File Excel kết quả sẽ được đặt tên tự động theo định dạng:<br>"
            "<code>KetQua_HoTen_BaiKiemTra_YYYYMMDD_HHMMSS.xlsx</code>"
        )
        note.setTextFormat(Qt.TextFormat.RichText)
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch()
        return widget

    def _build_gsheets_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)

        # Instructions
        info = QLabel(
            "<b>Cách thiết lập Google Sheets:</b><br>"
            "1. Tạo Service Account trên <a href='https://console.cloud.google.com'>Google Cloud Console</a>.<br>"
            "2. Tải file JSON key của Service Account về máy.<br>"
            "3. Tạo Google Sheet, chia sẻ (Share) với email của Service Account (quyền <b>Editor</b>).<br>"
            "4. Có thể điền URL Sheet mặc định để học sinh không cần nhập lại.<br><br>"
            "<i>Học sinh sẽ nhập URL lúc nộp bài nếu không có mặc định.</i>"
        )
        info.setTextFormat(Qt.TextFormat.RichText)
        info.setWordWrap(True)
        info.setOpenExternalLinks(True)
        layout.addWidget(info)

        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # Credentials path
        cred_row = QHBoxLayout()
        self._gsheets_cred_edit = QLineEdit()
        self._gsheets_cred_edit.setPlaceholderText("Đường dẫn đến file credentials.json ...")
        self._gsheets_cred_edit.setReadOnly(True)
        cred_row.addWidget(self._gsheets_cred_edit, stretch=1)
        browse_cred_btn = QPushButton("Chọn file...")
        browse_cred_btn.setMinimumWidth(112)
        browse_cred_btn.clicked.connect(self._browse_credentials)
        cred_row.addWidget(browse_cred_btn)
        form.addRow("File credentials.json:", cred_row)

        # Default sheet URL
        self._gsheets_url_edit = QLineEdit()
        self._gsheets_url_edit.setPlaceholderText(
            "https://docs.google.com/spreadsheets/d/... (tuỳ chọn)"
        )
        form.addRow("URL Sheet mặc định:", self._gsheets_url_edit)

        layout.addLayout(form)
        layout.addStretch()
        return widget

    # ------------------------------------------------------------------
    # Populate from loaded settings
    # ------------------------------------------------------------------

    def _populate_fields(self) -> None:
        cfg = self._cfg
        mode_map = {
            "none": self._mode_none,
            "email": self._mode_email,
            "folder": self._mode_folder,
            "both": self._mode_both,
        }
        mode_map.get(cfg.mode, self._mode_none).setChecked(True)

        self._default_email_edit.setText(cfg.default_email)
        self._smtp_server_edit.setText(cfg.smtp_server)
        self._smtp_port_spin.setValue(cfg.smtp_port)
        self._smtp_tls_check.setChecked(cfg.smtp_use_tls)
        self._smtp_user_edit.setText(cfg.smtp_user)
        self._smtp_password_edit.setText(cfg.smtp_password)
        self._smtp_sender_edit.setText(cfg.smtp_sender)
        self._folder_edit.setText(cfg.submit_folder)
        self._gsheets_cred_edit.setText(cfg.gsheets_credentials_path)
        self._gsheets_url_edit.setText(cfg.gsheets_default_url)

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

    def _browse_credentials(self) -> None:
        current_dir = str(Path(self._gsheets_cred_edit.text()).parent) if self._gsheets_cred_edit.text() else str(Path.home())
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Chọn file credentials.json",
            current_dir,
            "JSON files (*.json)",
        )
        if path:
            self._gsheets_cred_edit.setText(path)

    def _test_smtp(self) -> None:
        """Quick smoke-test: connect to SMTP server and check login."""
        server = self._smtp_server_edit.text().strip()
        port = self._smtp_port_spin.value()
        user = self._smtp_user_edit.text().strip()
        password = self._smtp_password_edit.text()
        use_tls = self._smtp_tls_check.isChecked()

        if not server:
            self._test_result.setText(
                '<span style="color: #c0392b;">Chưa nhập SMTP server.</span>'
            )
            self._test_result.setTextFormat(Qt.TextFormat.RichText)
            return

        try:
            self._facade.test_smtp_connection(
                server=server,
                port=port,
                user=user,
                password=password,
                use_tls=use_tls,
            )
            self._test_result.setText(
                '<span style="color: #27ae60;">✓ Kết nối thành công!</span>'
            )
        except Exception as exc:
            self._test_result.setText(
                f'<span style="color: #c0392b;">✗ {map_exception_to_user_message(exc)}</span>'
            )
        self._test_result.setTextFormat(Qt.TextFormat.RichText)

    def _on_save(self) -> None:
        if self._mode_email.isChecked():
            mode = "email"
        elif self._mode_folder.isChecked():
            mode = "folder"
        elif self._mode_both.isChecked():
            mode = "both"
        else:
            mode = "none"

        cfg = SubmissionSettings(
            mode=mode,
            default_email=self._default_email_edit.text().strip(),
            smtp_server=self._smtp_server_edit.text().strip(),
            smtp_port=self._smtp_port_spin.value(),
            smtp_use_tls=self._smtp_tls_check.isChecked(),
            smtp_user=self._smtp_user_edit.text().strip(),
            smtp_password=self._smtp_password_edit.text(),
            smtp_sender=self._smtp_sender_edit.text().strip(),
            submit_folder=self._folder_edit.text().strip(),
            gsheets_credentials_path=self._gsheets_cred_edit.text().strip(),
            gsheets_default_url=self._gsheets_url_edit.text().strip(),
        )
        try:
            self._save_settings(cfg)
            self._cfg = cfg
            logger.info("Submission settings saved.")
            self.accept()
        except Exception as exc:
            logger.error(f"Failed to save submission settings: {exc}")
            self._status_label.setText(
                "<span style=\"color: #c0392b;\">"
                f"Lỗi lưu cài đặt: {map_exception_to_user_message(exc)}"
                "</span>"
            )
            self._status_label.setTextFormat(Qt.TextFormat.RichText)
            self._status_label.show()
