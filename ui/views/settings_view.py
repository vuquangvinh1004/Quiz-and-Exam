"""Màn cài đặt.

Provides application settings management:
  - Cài đặt chung: đổi giao diện lưu vào app_settings.
  - Nộp bài: gửi email hoặc lưu thư mục cho kết quả bài kiểm tra.
  - Sao lưu & Phục hồi: quản lý sao lưu SQLite cục bộ.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui.dialogs.submission_settings_dialog import SubmissionSettingsDialog
from ui.facades.settings_facade import SettingsFacade


class SettingsView(QWidget):
    """Cài đặt ứng dụng: giao diện, nộp bài, sao lưu/phục hồi."""

    # Emitted after the user applies a new theme so MainWindow can
    # update the QSS and status bar immediately.
    theme_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._facade = SettingsFacade()
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)

        title = QLabel("Cài đặt")
        title.setObjectName("view_title")
        layout.addWidget(title)

        layout.addWidget(self._build_general_group())
        layout.addWidget(self._build_submission_group())
        layout.addWidget(self._build_backup_group())
        layout.addStretch()

    def _build_general_group(self) -> QGroupBox:
        group = QGroupBox("Cài đặt chung")
        inner = QVBoxLayout(group)
        inner.setSpacing(10)

        # Theme row
        theme_row = QHBoxLayout()
        theme_row.addWidget(QLabel("Giao diện:"))
        self._theme_combo = QComboBox()
        self._theme_combo.addItem("Sáng", "light")
        self._theme_combo.addItem("Tối", "dark")
        self._theme_combo.setFixedWidth(160)
        theme_row.addWidget(self._theme_combo)
        theme_row.addStretch()
        inner.addLayout(theme_row)

        btn_apply = QPushButton("Áp dụng")
        btn_apply.setFixedHeight(34)
        btn_apply.setFixedWidth(120)
        btn_apply.clicked.connect(self._apply_general_settings)
        inner.addWidget(btn_apply)

        self._lbl_theme_status = QLabel("")
        self._lbl_theme_status.setObjectName("muted_label")
        inner.addWidget(self._lbl_theme_status)

        return group

    def _build_submission_group(self) -> QGroupBox:
        group = QGroupBox("Nộp bài")
        inner = QVBoxLayout(group)
        inner.setSpacing(10)

        desc = QLabel(
            "Cấu hình phương thức nộp bài sau khi hoàn thành bài ở <b>chế độ Kiểm tra</b>.<br>"
            "Hỗ trợ gửi qua Email và/hoặc lưu vào thư mục trên máy tính."
        )
        desc.setWordWrap(True)
        desc.setTextFormat(Qt.TextFormat.RichText)
        inner.addWidget(desc)

        row = QHBoxLayout()
        btn = QPushButton("Cấu hình nộp bài...")
        btn.setFixedHeight(36)
        btn.setFixedWidth(180)
        btn.clicked.connect(self._open_submission_settings)
        row.addWidget(btn)
        row.addStretch()
        inner.addLayout(row)

        self._sub_status = QLabel("")
        self._sub_status.setObjectName("muted_label")
        inner.addWidget(self._sub_status)
        self._refresh_submission_status()

        return group

    def _build_backup_group(self) -> QGroupBox:
        group = QGroupBox("Sao lưu & Phục hồi")
        inner = QVBoxLayout(group)
        inner.setSpacing(10)

        desc = QLabel(
            "Tạo bản sao lưu cơ sở dữ liệu vào thư mục <code>data/backups/</code>.<br>"
            "Sau khi phục hồi, cần khởi động lại ứng dụng để áp dụng thay đổi."
        )
        desc.setWordWrap(True)
        desc.setTextFormat(Qt.TextFormat.RichText)
        inner.addWidget(desc)

        btn_row = QHBoxLayout()

        btn_backup = QPushButton("Tạo sao lưu ngay")
        btn_backup.setFixedHeight(34)
        btn_backup.setFixedWidth(160)
        btn_backup.clicked.connect(self._on_create_backup)
        btn_row.addWidget(btn_backup)

        btn_restore = QPushButton("Phục hồi từ bản sao lưu...")
        btn_restore.setFixedHeight(34)
        btn_restore.setFixedWidth(180)
        btn_restore.clicked.connect(self._on_restore_backup)
        btn_row.addWidget(btn_restore)
        btn_row.addStretch()
        inner.addLayout(btn_row)

        self._lbl_backup_status = QLabel("")
        self._lbl_backup_status.setObjectName("muted_label")
        inner.addWidget(self._lbl_backup_status)

        return group

    # ------------------------------------------------------------------
    # Khi màn hình được hiển thị, làm mới giá trị từ DB
    # ------------------------------------------------------------------

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self.refresh()

    def refresh(self) -> None:
        """Điểm làm mới công khai cho contract F5 của MainWindow."""
        self._load_theme_from_db()
        self._refresh_submission_status()

    def _load_theme_from_db(self) -> None:
        try:
            theme = self._facade.get_theme()
            idx = self._theme_combo.findData(theme)
            if idx >= 0:
                self._theme_combo.setCurrentIndex(idx)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Xử lý cài đặt chung
    # ------------------------------------------------------------------

    def _apply_general_settings(self) -> None:
        theme = self._theme_combo.currentData()
        try:
            self._facade.set_theme(theme)
            label = self._theme_combo.currentText()
            self._lbl_theme_status.setText(f"Đã lưu: {label}")
            self.theme_changed.emit(theme)
        except Exception as exc:
            QMessageBox.warning(self, "Lỗi", f"Không thể lưu cài đặt:\n{exc}")

    # ------------------------------------------------------------------
    # Cài đặt nộp bài
    # ------------------------------------------------------------------

    def _open_submission_settings(self) -> None:
        dlg = SubmissionSettingsDialog(parent=self)
        if dlg.exec():
            self._refresh_submission_status()

    def _refresh_submission_status(self) -> None:
        try:
            cfg = self._facade.get_submission_status()
            mode_labels = {
                "none": "Không nộp bài",
                "email": f"Gửi Email → {cfg.default_email or '(chưa đặt)'}",
                "folder": f"Lưu thư mục → {cfg.submit_folder or '(chưa đặt)'}",
                "both": (
                    f"Email ({cfg.default_email or '—'}) + "
                    f"Thư mục ({cfg.submit_folder or '—'})"
                ),
            }
            label = mode_labels.get(cfg.mode, cfg.mode)
            self._sub_status.setText(f"Trạng thái hiện tại: {label}")
        except Exception:
            self._sub_status.setText("")

    # ------------------------------------------------------------------
    # Sao lưu / phục hồi
    # ------------------------------------------------------------------

    def _on_create_backup(self) -> None:
        from config.paths import BACKUPS_DIR, DB_PATH
        try:
            dest = self._facade.create_backup(DB_PATH, BACKUPS_DIR)
            self._lbl_backup_status.setText(f"Bản sao lưu đã lưu: {dest.name}")
            QMessageBox.information(
                self, "Sao lưu thành công", f"Đã tạo bản sao lưu:\n{dest}"
            )
        except Exception as exc:
            QMessageBox.warning(self, "Lỗi", f"Không thể tạo bản sao lưu:\n{exc}")

    def _on_restore_backup(self) -> None:
        from config.paths import BACKUPS_DIR, DB_PATH

        backup_file_str, _ = QFileDialog.getOpenFileName(
            self,
            "Chọn file sao lưu",
            str(BACKUPS_DIR),
            "SQLite Database (*.db)",
        )
        if not backup_file_str:
            return

        from pathlib import Path
        backup_file = Path(backup_file_str)

        confirm = QMessageBox.warning(
            self,
            "Xác nhận phục hồi",
            f"⚠️  Thao tác này sẽ GHI ĐÈ toàn bộ dữ liệu hiện tại\nbằng file sao lưu:\n\n{backup_file.name}\n\n"
            "Dữ liệu hiện tại sẽ bị MẤT nếu chưa có bản sao lưu.\n\n"
            "Bạn có chắc chắn muốn phục hồi không?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            self._facade.restore_backup(DB_PATH, backup_file)
            self._lbl_backup_status.setText(f"Đã phục hồi từ: {backup_file.name}")
            QMessageBox.information(
                self,
                "Phục hồi thành công",
                "Đã phục hồi dữ liệu thành công.\n\n"
                "Vui lòng khởi động lại ứng dụng để áp dụng thay đổi.",
            )
        except Exception as exc:
            QMessageBox.warning(self, "Lỗi", f"Không thể phục hồi:\n{exc}")

