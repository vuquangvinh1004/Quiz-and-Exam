"""Settings service: persistent app settings via app_settings table.

Uses the ``app_settings`` key-value table (ARCHITECTURE §8.2) to store
and retrieve application preferences.

Known setting keys:
  ``app_theme``   – ``"light"`` or ``"dark"``  (default ``"light"``)
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from core.database.models import AppSetting

_KNOWN_THEMES: frozenset[str] = frozenset({"light", "dark"})


class SettingsService:
    """Stateless service for reading/writing app_settings rows."""

    # ------------------------------------------------------------------
    # Generic get / set
    # ------------------------------------------------------------------

    @staticmethod
    def get(session: Session, key: str, default: Optional[str] = None) -> Optional[str]:
        """Return the stored value for *key*, or *default* if not found."""
        row = session.query(AppSetting).filter_by(setting_key=key).first()
        return row.setting_value if row is not None else default

    @staticmethod
    def set(session: Session, key: str, value: str) -> None:
        """Create or update a setting row.

        Flushes to the session but does not commit; callers should use
        ``get_session()`` which auto-commits on clean exit.
        """
        row = session.query(AppSetting).filter_by(setting_key=key).first()
        if row is None:
            row = AppSetting(setting_key=key, setting_value=value)
            session.add(row)
        else:
            row.setting_value = value
        session.flush()

    # ------------------------------------------------------------------
    # Theme helpers
    # ------------------------------------------------------------------

    @staticmethod
    def get_theme(session: Session) -> str:
        """Return the stored theme name; falls back to ``'light'``."""
        return SettingsService.get(session, "app_theme", "light") or "light"

    @staticmethod
    def set_theme(session: Session, theme: str) -> None:
        """Persist the app theme.

        Raises
        ------
        ValueError
            If *theme* is not one of the known theme names.
        """
        if theme not in _KNOWN_THEMES:
            raise ValueError(
                f"Unknown theme: {theme!r}.  Must be one of {sorted(_KNOWN_THEMES)}."
            )
        SettingsService.set(session, "app_theme", theme)
