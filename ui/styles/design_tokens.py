"""Design token maps for Quiz Desktop App themes.

These tokens mirror DESIGN.md semantic roles and provide a single source
for runtime style values used by themes.py.
"""
from __future__ import annotations

LIGHT_TOKENS: dict[str, str] = {
    "color-primary": "#1abc9c",
    "color-on-primary": "#ffffff",
    "color-bg-app": "#f5f5f5",
    "color-text-main": "#212121",
    "color-text-muted": "#666666",
    "color-border": "#d0d5dd",
    "color-surface": "#ffffff",
    "color-nav-bg": "#2c3e50",
    "color-nav-hover": "#34495e",
    "color-nav-text": "#ecf0f1",
    "color-tab-selected-border": "#1abc9c",
}

DARK_TOKENS: dict[str, str] = {
    "color-primary": "#0e639c",
    "color-on-primary": "#ffffff",
    "color-bg-app": "#1e1e1e",
    "color-text-main": "#d4d4d4",
    "color-text-muted": "#aaaaaa",
    "color-border": "#3e3e42",
    "color-surface": "#252526",
    "color-nav-bg": "#252526",
    "color-nav-hover": "#2d2d30",
    "color-nav-text": "#d4d4d4",
    "color-tab-selected-border": "#1abc9c",
}


def get_theme_tokens(theme: str) -> dict[str, str]:
    """Return semantic tokens for a given theme name."""
    if theme == "dark":
        return DARK_TOKENS
    return LIGHT_TOKENS
