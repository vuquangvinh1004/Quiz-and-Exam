"""Unit tests for ResultHistoryView filter logic.

Tests the pure Python portion of _apply_filter() in isolation:
- No DB involved; _attempts is set directly as list[dict]
- Verifies search, mode, status, and combination filters
- Verifies _clear_filter() resets all inputs
- Verifies count label text (shown/total)

Requires: pytest-qt (offscreen via QT_QPA_PLATFORM=offscreen)
"""
from __future__ import annotations

import os

import pytest
from PySide6.QtWidgets import QApplication

from ui.views.result_history_view import ResultHistoryView

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


# ---------------------------------------------------------------------------
# App fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def view(qapp):
    v = ResultHistoryView()
    return v


# ---------------------------------------------------------------------------
# Sample data factory
# ---------------------------------------------------------------------------

def _sample_attempts():
    """Return 6 dict rows that exercise search / mode / status combinations."""
    from datetime import UTC, datetime

    now = datetime(2024, 6, 1, 10, 0, tzinfo=UTC)
    return [
        {"id": 1, "quiz_title": "Toán học", "mode": "EXAM", "status": "SUBMITTED",
         "score": 8.0, "max_score": 10.0, "score_pct": 80.0, "started_at": now},
        {"id": 2, "quiz_title": "Vật lý", "mode": "PRACTICE", "status": "TIME_UP",
         "score": 5.0, "max_score": 10.0, "score_pct": 50.0, "started_at": now},
        {"id": 3, "quiz_title": "Hóa học", "mode": "STUDY", "status": "COMPLETED",
         "score": 9.0, "max_score": 10.0, "score_pct": 90.0, "started_at": now},
        {"id": 4, "quiz_title": "Toán nâng cao", "mode": "EXAM", "status": "TIME_UP",
         "score": 3.0, "max_score": 10.0, "score_pct": 30.0, "started_at": now},
        {"id": 5, "quiz_title": "Vật lý nâng cao", "mode": "PRACTICE", "status": "SUBMITTED",
         "score": 7.0, "max_score": 10.0, "score_pct": 70.0, "started_at": now},
        {"id": 6, "quiz_title": "Sinh học", "mode": "STUDY", "status": "COMPLETED",
         "score": 6.0, "max_score": 10.0, "score_pct": 60.0, "started_at": now},
    ]


# ---------------------------------------------------------------------------
# Tests – no filter (show all)
# ---------------------------------------------------------------------------

class TestNoFilter:

    def test_all_shown_when_no_filter(self, view):
        view._attempts = _sample_attempts()
        view._apply_filter()
        assert view._table.rowCount() == 6

    def test_count_label_total_when_all_shown(self, view):
        view._attempts = _sample_attempts()
        view._apply_filter()
        assert "Tổng: 6" in view._lbl_count.text()


# ---------------------------------------------------------------------------
# Tests – search filter
# ---------------------------------------------------------------------------

class TestSearchFilter:

    def test_search_filters_by_title(self, view):
        view._attempts = _sample_attempts()
        view._search_edit.setText("toán")
        # _apply_filter() is called via signal; or call directly
        view._apply_filter()
        # "Toán học" + "Toán nâng cao" → 2
        assert view._table.rowCount() == 2

    def test_search_case_insensitive(self, view):
        view._attempts = _sample_attempts()
        view._search_edit.setText("TOÁN")
        view._apply_filter()
        assert view._table.rowCount() == 2

    def test_search_no_match_returns_empty(self, view):
        view._attempts = _sample_attempts()
        view._search_edit.setText("XYZ không tồn tại")
        view._apply_filter()
        assert view._table.rowCount() == 0

    def test_count_label_shows_filtered(self, view):
        view._attempts = _sample_attempts()
        view._search_edit.setText("vật lý")
        view._apply_filter()
        assert "Hiển thị 2/6" in view._lbl_count.text()


# ---------------------------------------------------------------------------
# Tests – mode filter
# ---------------------------------------------------------------------------

class TestModeFilter:

    def test_mode_exam_filter(self, view):
        view._attempts = _sample_attempts()
        idx = view._mode_filter.findData("EXAM")
        view._mode_filter.setCurrentIndex(idx)
        view._apply_filter()
        # rows 1, 4 are EXAM → 2
        assert view._table.rowCount() == 2

    def test_mode_practice_filter(self, view):
        view._attempts = _sample_attempts()
        idx = view._mode_filter.findData("PRACTICE")
        view._mode_filter.setCurrentIndex(idx)
        view._apply_filter()
        assert view._table.rowCount() == 2

    def test_mode_study_filter(self, view):
        view._attempts = _sample_attempts()
        idx = view._mode_filter.findData("STUDY")
        view._mode_filter.setCurrentIndex(idx)
        view._apply_filter()
        assert view._table.rowCount() == 2


# ---------------------------------------------------------------------------
# Tests – status filter
# ---------------------------------------------------------------------------

class TestStatusFilter:

    def test_status_submitted_filter(self, view):
        view._attempts = _sample_attempts()
        idx = view._status_filter.findData("SUBMITTED")
        view._status_filter.setCurrentIndex(idx)
        view._apply_filter()
        assert view._table.rowCount() == 2

    def test_status_completed_filter(self, view):
        view._attempts = _sample_attempts()
        idx = view._status_filter.findData("COMPLETED")
        view._status_filter.setCurrentIndex(idx)
        view._apply_filter()
        assert view._table.rowCount() == 2

    def test_status_time_up_filter(self, view):
        view._attempts = _sample_attempts()
        idx = view._status_filter.findData("TIME_UP")
        view._status_filter.setCurrentIndex(idx)
        view._apply_filter()
        assert view._table.rowCount() == 2


# ---------------------------------------------------------------------------
# Tests – combined filters
# ---------------------------------------------------------------------------

class TestCombinedFilters:

    def test_mode_and_status_combined(self, view):
        view._attempts = _sample_attempts()
        idx_mode = view._mode_filter.findData("EXAM")
        view._mode_filter.setCurrentIndex(idx_mode)
        idx_status = view._status_filter.findData("SUBMITTED")
        view._status_filter.setCurrentIndex(idx_status)
        view._apply_filter()
        # Only row 1: EXAM + SUBMITTED
        assert view._table.rowCount() == 1

    def test_search_and_mode_combined(self, view):
        view._attempts = _sample_attempts()
        view._search_edit.setText("nâng cao")
        idx_mode = view._mode_filter.findData("EXAM")
        view._mode_filter.setCurrentIndex(idx_mode)
        view._apply_filter()
        # Only row 4: "Toán nâng cao" + EXAM
        assert view._table.rowCount() == 1

    def test_all_filters_no_match(self, view):
        view._attempts = _sample_attempts()
        view._search_edit.setText("toán")
        idx_mode = view._mode_filter.findData("STUDY")
        view._mode_filter.setCurrentIndex(idx_mode)
        view._apply_filter()
        assert view._table.rowCount() == 0


# ---------------------------------------------------------------------------
# Tests – clear filter
# ---------------------------------------------------------------------------

class TestClearFilter:

    def test_clear_filter_shows_all_rows(self, view):
        view._attempts = _sample_attempts()
        # Apply a restrictive filter first
        view._search_edit.setText("toán")
        view._apply_filter()
        assert view._table.rowCount() == 2

        # Clear
        view._clear_filter()
        assert view._table.rowCount() == 6

    def test_clear_filter_resets_widgets(self, view):
        view._attempts = _sample_attempts()
        view._search_edit.setText("test")
        idx = view._mode_filter.findData("EXAM")
        view._mode_filter.setCurrentIndex(idx)
        idx2 = view._status_filter.findData("SUBMITTED")
        view._status_filter.setCurrentIndex(idx2)

        view._clear_filter()

        assert view._search_edit.text() == ""
        assert view._mode_filter.currentData() is None
        assert view._status_filter.currentData() is None
