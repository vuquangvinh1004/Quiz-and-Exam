"""Unit tests for core/utils/logger.py (Phase 7 coverage).

Covers:
  - configure_logging: creates log directory, sets up sinks, idempotent
  - get_logger: returns a bound logger that accepts log calls
"""
from __future__ import annotations

from pathlib import Path

import pytest

# Reset module-level flag before each test so configure_logging is callable
import importlib
import core.utils.logger as logger_module


@pytest.fixture(autouse=True)
def reset_logger_state():
    """Reset _configured flag so each test starts fresh."""
    logger_module._configured = False
    yield
    logger_module._configured = False


class TestConfigureLogging:

    def test_creates_log_dir(self, tmp_path):
        log_dir = tmp_path / "sublogs"
        assert not log_dir.exists()
        logger_module.configure_logging(log_dir=log_dir)
        assert log_dir.exists()

    def test_sets_configured_flag(self, tmp_path):
        log_dir = tmp_path / "logs"
        assert logger_module._configured is False
        logger_module.configure_logging(log_dir=log_dir)
        assert logger_module._configured is True

    def test_idempotent_second_call_skipped(self, tmp_path):
        log_dir = tmp_path / "logs"
        logger_module.configure_logging(log_dir=log_dir)
        # Second call must not raise and must keep flag True
        logger_module.configure_logging(log_dir=log_dir)
        assert logger_module._configured is True

    def test_accepts_debug_level(self, tmp_path):
        log_dir = tmp_path / "debug_logs"
        logger_module.configure_logging(log_dir=log_dir, level="DEBUG")
        assert logger_module._configured is True

    def test_accepts_warning_level(self, tmp_path):
        log_dir = tmp_path / "warn_logs"
        logger_module.configure_logging(log_dir=log_dir, level="WARNING")
        assert logger_module._configured is True

    def test_existing_dir_does_not_raise(self, tmp_path):
        log_dir = tmp_path / "existing"
        log_dir.mkdir()
        logger_module.configure_logging(log_dir=log_dir)
        assert logger_module._configured is True


class TestGetLogger:

    def test_returns_logger_object(self, tmp_path):
        logger = logger_module.get_logger("test_module")
        assert logger is not None

    def test_logger_supports_info(self, tmp_path):
        log_dir = tmp_path / "logs"
        logger_module.configure_logging(log_dir=log_dir)
        logger = logger_module.get_logger("test_module")
        # Should not raise
        logger.info("test info message")

    def test_logger_supports_warning(self, tmp_path):
        log_dir = tmp_path / "logs"
        logger_module.configure_logging(log_dir=log_dir)
        logger = logger_module.get_logger("test_module")
        logger.warning("test warning")

    def test_logger_supports_error(self, tmp_path):
        log_dir = tmp_path / "logs"
        logger_module.configure_logging(log_dir=log_dir)
        logger = logger_module.get_logger("test_module")
        logger.error("test error")

    def test_different_names_return_same_type(self):
        l1 = logger_module.get_logger("mod.a")
        l2 = logger_module.get_logger("mod.b")
        assert type(l1) is type(l2)
