"""Unit tests for blank placeholder rendering helpers."""
from __future__ import annotations

from core.utils.blank_rendering import render_blank_placeholders


def test_render_blank_placeholders_converts_canonical_marker():
    assert render_blank_placeholders("Thang đo [[blank]]") == "Thang đo ________"


def test_render_blank_placeholders_keeps_existing_underscores():
    assert render_blank_placeholders("Thang đo ________") == "Thang đo ________"


def test_render_blank_placeholders_handles_mixed_case_marker():
    assert render_blank_placeholders("Thang đo [[BLANK]]") == "Thang đo ________"
