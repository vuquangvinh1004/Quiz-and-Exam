from __future__ import annotations

from core.utils.error_mapper import map_exception_to_user_message
from core.utils.exceptions import (
    DatabaseError,
    ImportFileError,
    ImportValidationError,
    MigrationError,
    SettingsError,
    SubmissionConfigError,
    SubmissionDeliveryError,
    ValidationError,
)


def test_map_import_validation_error() -> None:
    exc = ImportValidationError(errors=[{"row": 1, "severity": "error", "message": "x"}])
    msg = map_exception_to_user_message(exc)
    assert "import" in msg.lower()


def test_map_migration_error() -> None:
    msg = map_exception_to_user_message(MigrationError("boom"))
    assert "nâng cấp" in msg.lower()


def test_map_settings_error() -> None:
    msg = map_exception_to_user_message(SettingsError("fail"))
    assert "cài đặt" in msg.lower()


def test_map_database_error() -> None:
    msg = map_exception_to_user_message(DatabaseError("db"))
    assert "cơ sở dữ liệu" in msg.lower()


def test_map_unknown_error_falls_back_to_str() -> None:
    msg = map_exception_to_user_message(RuntimeError("raw error"))
    assert msg == "raw error"


def test_map_import_file_error() -> None:
    msg = map_exception_to_user_message(ImportFileError("file"))
    assert "file" in msg.lower()


def test_map_validation_error() -> None:
    msg = map_exception_to_user_message(ValidationError("invalid"))
    assert "không hợp lệ" in msg.lower()


def test_map_submission_config_error() -> None:
    msg = map_exception_to_user_message(SubmissionConfigError("cfg"))
    assert "cấu hình" in msg.lower()


def test_map_submission_delivery_error() -> None:
    msg = map_exception_to_user_message(SubmissionDeliveryError("delivery"))
    assert "gửi/lưu" in msg.lower()
