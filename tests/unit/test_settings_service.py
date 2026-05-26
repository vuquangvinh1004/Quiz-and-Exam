"""Unit tests for core/domain/services/settings_service.py (Phase 6).

Tests:
  - get: returns default when missing, returns stored value
  - set: creates new row, updates existing row
  - get_theme: default 'light', reads from DB
  - set_theme: saves valid themes, rejects unknown themes
"""
from __future__ import annotations

import pytest

from core.database.models import AppSetting
from core.domain.services.settings_service import SettingsService


class TestGet:

    def test_returns_default_when_key_not_found(self, db_session):
        result = SettingsService.get(db_session, "nonexistent_key", "fallback")
        assert result == "fallback"

    def test_returns_none_default_by_default(self, db_session):
        result = SettingsService.get(db_session, "nonexistent_key")
        assert result is None

    def test_returns_stored_value(self, db_session):
        db_session.add(AppSetting(setting_key="my_key", setting_value="my_value"))
        db_session.flush()
        assert SettingsService.get(db_session, "my_key") == "my_value"

    def test_does_not_affect_other_keys(self, db_session):
        db_session.add(AppSetting(setting_key="a", setting_value="1"))
        db_session.flush()
        assert SettingsService.get(db_session, "b") is None


class TestSet:

    def test_creates_new_row(self, db_session):
        SettingsService.set(db_session, "fresh_key", "fresh_value")
        row = db_session.query(AppSetting).filter_by(setting_key="fresh_key").first()
        assert row is not None
        assert row.setting_value == "fresh_value"

    def test_updates_existing_row(self, db_session):
        db_session.add(AppSetting(setting_key="existing", setting_value="old"))
        db_session.flush()
        SettingsService.set(db_session, "existing", "new")
        row = db_session.query(AppSetting).filter_by(setting_key="existing").first()
        assert row.setting_value == "new"

    def test_does_not_create_duplicate_rows(self, db_session):
        SettingsService.set(db_session, "dup_key", "v1")
        SettingsService.set(db_session, "dup_key", "v2")
        count = db_session.query(AppSetting).filter_by(setting_key="dup_key").count()
        assert count == 1
        assert SettingsService.get(db_session, "dup_key") == "v2"


class TestGetTheme:

    def test_default_theme_is_light(self, db_session):
        assert SettingsService.get_theme(db_session) == "light"

    def test_returns_stored_theme(self, db_session):
        db_session.add(AppSetting(setting_key="app_theme", setting_value="dark"))
        db_session.flush()
        assert SettingsService.get_theme(db_session) == "dark"


class TestSetTheme:

    def test_stores_light_theme(self, db_session):
        SettingsService.set_theme(db_session, "light")
        assert SettingsService.get_theme(db_session) == "light"

    def test_stores_dark_theme(self, db_session):
        SettingsService.set_theme(db_session, "dark")
        assert SettingsService.get_theme(db_session) == "dark"

    def test_updates_existing_theme(self, db_session):
        SettingsService.set_theme(db_session, "light")
        SettingsService.set_theme(db_session, "dark")
        assert SettingsService.get_theme(db_session) == "dark"

    def test_rejects_unknown_theme(self, db_session):
        with pytest.raises(ValueError, match="Unknown theme"):
            SettingsService.set_theme(db_session, "blue")

    def test_rejects_empty_string(self, db_session):
        with pytest.raises(ValueError):
            SettingsService.set_theme(db_session, "")
