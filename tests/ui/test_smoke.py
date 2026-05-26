"""UI smoke tests for main views (Phase 7).

Verifies that each view can be instantiated and displayed without crash.
These tests run headlessly via the QT_QPA_PLATFORM=offscreen environment variable.

Requires: pytest-qt (pytestqt)
"""
from __future__ import annotations

import os
import pytest

# Force offscreen rendering so tests can run in CI / headless environments
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from ui.views.dashboard_view import DashboardView
from ui.views.import_view import ImportView
from ui.views.question_bank_view import QuestionBankView
from ui.views.quiz_builder_view import QuizBuilderView
from ui.views.quiz_runner_view import QuizRunnerView
from ui.views.result_history_view import ResultHistoryView
from ui.views.settings_view import SettingsView


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def qapp_instance():
    """Module-scoped QApplication for all smoke tests."""
    app = QApplication.instance() or QApplication([])
    yield app


# ---------------------------------------------------------------------------
# Dashboard smoke test
# ---------------------------------------------------------------------------

class TestDashboardSmoke:

    def test_instantiates_without_crash(self, qapp_instance):
        view = DashboardView()
        assert view is not None

    def test_has_widget_structure(self, qapp_instance):
        view = DashboardView()
        # Must be a QWidget subclass
        from PySide6.QtWidgets import QWidget
        assert isinstance(view, QWidget)

    def test_shows_without_crash(self, qapp_instance):
        view = DashboardView()
        view.show()
        view.hide()


# ---------------------------------------------------------------------------
# ImportView smoke test
# ---------------------------------------------------------------------------

class TestImportViewSmoke:

    def test_instantiates(self, qapp_instance):
        view = ImportView()
        assert view is not None

    def test_shows_without_crash(self, qapp_instance):
        view = ImportView()
        view.show()
        view.hide()


# ---------------------------------------------------------------------------
# QuestionBankView smoke test
# ---------------------------------------------------------------------------

class TestQuestionBankViewSmoke:

    def test_instantiates(self, qapp_instance):
        view = QuestionBankView()
        assert view is not None

    def test_shows_without_crash(self, qapp_instance):
        view = QuestionBankView()
        view.show()
        view.hide()


# ---------------------------------------------------------------------------
# QuizBuilderView smoke test
# ---------------------------------------------------------------------------

class TestQuizBuilderViewSmoke:

    def test_instantiates(self, qapp_instance):
        view = QuizBuilderView()
        assert view is not None

    def test_has_quiz_started_signal(self, qapp_instance):
        from PySide6.QtCore import Signal
        view = QuizBuilderView()
        assert hasattr(view, "quiz_started")

    def test_shows_without_crash(self, qapp_instance):
        view = QuizBuilderView()
        view.show()
        view.hide()


# ---------------------------------------------------------------------------
# QuizRunnerView smoke test
# ---------------------------------------------------------------------------

class TestQuizRunnerViewSmoke:

    def test_instantiates(self, qapp_instance):
        view = QuizRunnerView()
        assert view is not None

    def test_shows_without_crash(self, qapp_instance):
        view = QuizRunnerView()
        view.show()
        view.hide()


# ---------------------------------------------------------------------------
# ResultHistoryView smoke test
# ---------------------------------------------------------------------------

class TestResultHistoryViewSmoke:

    def test_instantiates(self, qapp_instance):
        view = ResultHistoryView()
        assert view is not None

    def test_shows_without_crash(self, qapp_instance):
        view = ResultHistoryView()
        view.show()
        view.hide()


# ---------------------------------------------------------------------------
# SettingsView smoke test
# ---------------------------------------------------------------------------

class TestSettingsViewSmoke:

    def test_instantiates(self, qapp_instance):
        view = SettingsView()
        assert view is not None

    def test_has_theme_changed_signal(self, qapp_instance):
        view = SettingsView()
        assert hasattr(view, "theme_changed")

    def test_shows_without_crash(self, qapp_instance):
        view = SettingsView()
        view.show()
        view.hide()


# ---------------------------------------------------------------------------
# MainWindow smoke test
# ---------------------------------------------------------------------------

class TestMainWindowSmoke:

    def test_instantiates(self, qapp_instance):
        from ui.main_window import MainWindow
        win = MainWindow()
        assert win is not None

    def test_has_minimum_size(self, qapp_instance):
        from ui.main_window import MainWindow
        win = MainWindow()
        # Architecture requires minimum 960x640
        assert win.minimumWidth() >= 960
        assert win.minimumHeight() >= 640

    def test_shows_without_crash(self, qapp_instance):
        from ui.main_window import MainWindow
        win = MainWindow()
        win.show()
        win.hide()
