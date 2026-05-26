"""Structural protocols for UI view contracts.

Using ``typing.Protocol`` allows views to satisfy the interface implicitly
(structural sub-typing) without inheriting from a common base class.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class Refreshable(Protocol):
    """Views that support a data refresh triggered by the F5 shortcut."""

    def refresh(self) -> None:
        """Reload/redisplay data from the current source."""
        ...
