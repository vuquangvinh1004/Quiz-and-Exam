"""Helpers for rendering BLANK placeholders in user-facing text."""
from __future__ import annotations

import re

from core.utils.constants import LEGACY_BLANK_PLACEHOLDER

_BLANK_PLACEHOLDER_RE = re.compile(r"\[\[blank\]\]", re.IGNORECASE)


def render_blank_placeholders(text: str, blank_line: str = LEGACY_BLANK_PLACEHOLDER) -> str:
    """Render canonical BLANK placeholders as visible underline spans.

    The app stores and validates the canonical ``[[blank]]`` marker, but
    user-facing previews should show a blank line instead. Legacy underline
    placeholders are left intact and also treated as the same visible form.
    """
    if not text:
        return ""
    rendered = _BLANK_PLACEHOLDER_RE.sub(blank_line, text)
    return rendered
