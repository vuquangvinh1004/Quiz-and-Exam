"""Unit tests for core/utils/helpers.py"""
from __future__ import annotations

import pytest

from core.utils.helpers import (
    normalize_line_breaks,
    normalize_whitespace,
    parse_bool,
    parse_tags,
    split_multi_value,
)


class TestNormalizeWhitespace:
    def test_strip_leading_trailing(self):
        assert normalize_whitespace("  hello  ") == "hello"

    def test_collapse_inner(self):
        assert normalize_whitespace("hello   world") == "hello world"

    def test_mixed(self):
        assert normalize_whitespace("  a  b   c  ") == "a b c"


class TestNormalizeLineBreaks:
    def test_crlf(self):
        assert normalize_line_breaks("a\r\nb") == "a\nb"

    def test_cr(self):
        assert normalize_line_breaks("a\rb") == "a\nb"

    def test_no_change_needed(self):
        assert normalize_line_breaks("a\nb") == "a\nb"


class TestParseBool:
    @pytest.mark.parametrize("val", ["true", "TRUE", "1", "yes", "y"])
    def test_truthy(self, val):
        assert parse_bool(val) is True

    @pytest.mark.parametrize("val", ["false", "FALSE", "0", "no", "n"])
    def test_falsy(self, val):
        assert parse_bool(val) is False

    def test_none_returns_default_false(self):
        assert parse_bool(None, default=False) is False

    def test_none_returns_default_true(self):
        assert parse_bool(None, default=True) is True

    def test_empty_string_returns_default(self):
        assert parse_bool("", default=True) is True

    def test_bool_input_passthrough(self):
        assert parse_bool(True) is True
        assert parse_bool(False) is False

    def test_invalid_string_raises(self):
        with pytest.raises(ValueError):
            parse_bool("maybe")


class TestSplitMultiValue:
    def test_basic(self):
        assert split_multi_value("A||C||D") == ["A", "C", "D"]

    def test_single(self):
        assert split_multi_value("A") == ["A"]

    def test_empty_string(self):
        assert split_multi_value("") == []

    def test_strips_whitespace(self):
        assert split_multi_value(" A || B ") == ["A", "B"]

    def test_drops_empty_tokens(self):
        assert split_multi_value("A||||B") == ["A", "B"]


class TestParseTags:
    def test_basic(self):
        assert parse_tags("python,sql,alembic") == ["python", "sql", "alembic"]

    def test_strips_whitespace(self):
        assert parse_tags(" a , b , c ") == ["a", "b", "c"]

    def test_empty_drops(self):
        assert parse_tags("a,,b") == ["a", "b"]

    def test_empty_string(self):
        assert parse_tags("") == []
