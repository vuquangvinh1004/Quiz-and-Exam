"""Centralized mapping from internal exceptions to user-facing messages."""
from __future__ import annotations

from core.utils.exceptions import (
    DatabaseError,
    ImportFileError,
    ImportValidationError,
    MigrationError,
    QuizAppError,
    SettingsError,
    SubmissionConfigError,
    SubmissionDeliveryError,
    SubmissionError,
    ValidationError,
)


def map_exception_to_user_message(exc: Exception) -> str:
    """Map known exception types to concise user-facing Vietnamese text."""
    if isinstance(exc, ImportValidationError):
        return "Dữ liệu import không hợp lệ. Vui lòng kiểm tra các dòng bị báo lỗi."
    if isinstance(exc, ImportFileError):
        return "Không thể đọc file import. Hãy kiểm tra định dạng và quyền truy cập file."
    if isinstance(exc, ValidationError):
        return "Dữ liệu không hợp lệ. Vui lòng kiểm tra lại thông tin đã nhập."
    if isinstance(exc, SettingsError):
        return "Không thể tải hoặc lưu cài đặt. Vui lòng thử lại."
    if isinstance(exc, SubmissionConfigError):
        return "Thiếu hoặc sai cấu hình nộp bài. Vui lòng kiểm tra lại cài đặt."
    if isinstance(exc, SubmissionDeliveryError):
        return "Không thể gửi/lưu bài nộp. Vui lòng thử lại sau."
    if isinstance(exc, SubmissionError):
        return str(exc) or "Nộp bài thất bại do lỗi nghiệp vụ."
    if isinstance(exc, MigrationError):
        return "Không thể nâng cấp dữ liệu ứng dụng. Vui lòng kiểm tra log và liên hệ hỗ trợ."
    if isinstance(exc, DatabaseError):
        return "Có lỗi truy cập cơ sở dữ liệu. Vui lòng thử lại sau."
    if isinstance(exc, QuizAppError):
        return str(exc) or "Đã xảy ra lỗi nghiệp vụ trong ứng dụng."
    return str(exc) or "Đã xảy ra lỗi không xác định."
