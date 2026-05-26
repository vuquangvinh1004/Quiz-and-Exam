"""General utility helpers used across the application."""
from __future__ import annotations

import re
from typing import Any


def normalize_whitespace(text: str) -> str:
    """Strip leading/trailing whitespace and collapse inner runs to one space."""
    return re.sub(r"\s+", " ", text.strip())


def normalize_line_breaks(text: str) -> str:
    """Normalize all line-break variants to ``\\n``."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def parse_bool(value: Any, default: bool = False) -> bool:
    """Convert common truthy/falsy strings and numbers to a Python bool.

    Accepted truthy:  ``true``, ``TRUE``, ``1``, ``yes``, ``y``
    Accepted falsy:   ``false``, ``FALSE``, ``0``, ``no``, ``n``
    Empty string or None returns *default*.

    Raises:
        ValueError: If the value is a non-empty string that is not recognised.
    """
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized == "":
        return default
    if normalized in ("true", "1", "yes", "y"):
        return True
    if normalized in ("false", "0", "no", "n"):
        return False
    raise ValueError(f"Cannot convert {value!r} to bool")


def split_multi_value(raw: str, delimiter: str = "||") -> list[str]:
    """Split a delimited string, stripping each token, dropping empties.

    Args:
        raw:       The raw field value (e.g. ``"A||C||D"``).
        delimiter: Token separator; defaults to the official ``||``.

    Returns:
        List of non-empty strings.
    """
    if not raw:
        return []
    return [token.strip() for token in raw.split(delimiter) if token.strip()]


def parse_tags(raw: str) -> list[str]:
    """Parse a comma-separated tags string into a cleaned list."""
    if not raw:
        return []
    return [t.strip() for t in raw.split(",") if t.strip()]
