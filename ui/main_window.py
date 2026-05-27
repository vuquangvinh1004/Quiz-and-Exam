"""Main application window.

Layout (ARCHITECTURE §9.1):
┌────────────────────────────────────────────────────────────────┐
│ Quiz Desktop App                            [ _ ][ □ ][ X ]   │
├──────────────┬─────────────────────────────────────────────────┤
│  sidebar     │  Content area (stacked widget)                  │
│  (nav btns)  │                                                 │
├──────────────┴─────────────────────────────────────────────────┤
│  Status: Ready | DB: OK | Autosave: ON | Theme: Light          │
└────────────────────────────────────────────────────────────────┘

Business rules:
- No business logic here; view switches only.
- All view-specific logic lives in the respective view module.
"""
from __future__ import annotations

import importlib

from PySide6.QtGui import QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from config.paths import APP_DIR
from config.settings import settings
from ui.styles.themes import get_stylesheet

# Nav item definitions: (label, module_path, class_name)
# Views are loaded lazily on first navigation to reduce startup time.
_NAV_ITEMS: list[tuple[str, str, str]] = [
    ("🏠  Dashboard",        "ui.views.dashboard_view",      "DashboardView"),
    ("📚  Ngân hàng",        "ui.views.question_bank_view",  "QuestionBankView"),
    ("📥  Import",           "ui.views.import_view",         "ImportView"),
    ("✏️  Tạo bài kiểm tra", "ui.views.quiz_builder_view",   "QuizBuilderView"),
    ("▶️  Làm bài",          "ui.views.quiz_runner_view",    "QuizRunnerView"),
    ("📋  Lịch sử",          "ui.views.result_history_view", "ResultHistoryView"),
    ("⚙️  Cài đặt",          "ui.views.settings_view",       "SettingsView"),
]


class MainWindow(QMainWindow):
    """Top-level application window."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(settings.app_name)
        self.setMinimumSize(960, 640)
        _icon_path = APP_DIR / "assets" / "icons" / "app_icon.ico"
        if not _icon_path.exists():
            _icon_path = APP_DIR / "assets" / "icons" / "app_icon.png"
        if _icon_path.exists():
            self.setWindowIcon(QIcon(str(_icon_path)))
        self._build_ui()
        self._init_theme_from_db()   # override .env default with DB-persisted value
        self._apply_theme()
        self._setup_shortcuts()
        self._navigate(0)  # show Dashboard by default

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Sidebar
        self._sidebar = self._build_sidebar()
        root_layout.addWidget(self._sidebar)

        # Content stacked widget – views are created lazily on first navigation
        self._stack = QStackedWidget()
        self._views: list[QWidget | None] = [None] * len(_NAV_ITEMS)
        for _ in _NAV_ITEMS:
            self._stack.addWidget(QWidget())  # placeholder until real view is loaded
        root_layout.addWidget(self._stack, stretch=1)

        # Status bar
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._update_status_bar()

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(0)

        self._nav_buttons: list[QPushButton] = []
        for idx, (label, *_) in enumerate(_NAV_ITEMS):
            btn = QPushButton(label)
            btn.setObjectName("nav_button")
            btn.setCheckable(True)
            btn.setFlat(True)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.setFixedHeight(44)
            btn.clicked.connect(lambda checked, i=idx: self._navigate(i))
            layout.addWidget(btn)
            self._nav_buttons.append(btn)

        layout.addStretch()
        return sidebar

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _load_view(self, index: int) -> QWidget:
        """Return the view at *index*, importing and creating it on first access."""
        if self._views[index] is not None:
            return self._views[index]  # type: ignore[return-value]

        _label, module_path, class_name = _NAV_ITEMS[index]
        mod = importlib.import_module(module_path)
        cls = getattr(mod, class_name)
        view: QWidget = cls(parent=self)

        # Swap placeholder → real view at the same stack index
        placeholder = self._stack.widget(index)
        self._stack.removeWidget(placeholder)
        self._stack.insertWidget(index, view)
        self._views[index] = view

        self._wire_view(index)
        return view

    def _wire_view(self, index: int) -> None:
        """Connect cross-view signals after a view is first created."""
        view = self._views[index]
        if index == 3:  # QuizBuilderView
            view.quiz_started.connect(self._launch_quiz)  # type: ignore[union-attr]
            if self._views[1] is not None:  # QuestionBankView already loaded
                self._views[1].refresh_requested.connect(view.refresh)  # type: ignore[union-attr]
        elif index == 1:  # QuestionBankView
            if self._views[3] is not None:  # QuizBuilderView already loaded
                view.refresh_requested.connect(self._views[3].refresh)  # type: ignore[union-attr]
        elif index == 6:  # SettingsView
            view.theme_changed.connect(self._on_theme_changed)  # type: ignore[union-attr]

    def _launch_quiz(self, quiz_id: int) -> None:
        """Called when QuizBuilderView emits quiz_started(quiz_id)."""
        runner = self._load_view(4)
        runner.load_quiz(quiz_id)  # type: ignore[union-attr]
        self._navigate(4)

    def _navigate(self, index: int) -> None:
        """Switch to view at *index*, loading it lazily if not yet created."""
        self._load_view(index)
        for i, btn in enumerate(self._nav_buttons):
            btn.setChecked(i == index)
        self._stack.setCurrentIndex(index)

    # ------------------------------------------------------------------
    # Keyboard shortcuts
    # ------------------------------------------------------------------

    def _setup_shortcuts(self) -> None:
        """Register global keyboard shortcuts.

        Ctrl+1 … Ctrl+7  — navigate to nav item 0-6
        F5                — refresh the currently visible view
        """
        for idx in range(len(_NAV_ITEMS)):
            sc = QShortcut(QKeySequence(f"Ctrl+{idx + 1}"), self)
            sc.activated.connect(lambda _checked=False, n=idx: self._navigate(n))

        refresh_sc = QShortcut(QKeySequence("F5"), self)
        refresh_sc.activated.connect(self._refresh_current_view)

    def _refresh_current_view(self) -> None:
        """Call refresh() on the active view if it implements Refreshable."""
        index = self._stack.currentIndex()
        view = self._views[index]
        if view is not None and hasattr(view, "refresh"):
            view.refresh()  # type: ignore[union-attr]

    # ------------------------------------------------------------------
    # Theme
    # ------------------------------------------------------------------

    def _init_theme_from_db(self) -> None:
        """Read the persisted theme from the DB and update the in-memory setting."""
        try:
            from core.database.session import get_session
            from core.domain.services.settings_service import SettingsService
            with get_session() as session:
                theme = SettingsService.get_theme(session)
            settings.app_theme = theme  # type: ignore[assignment]
        except Exception:
            pass  # keep the .env / default value on failure

    def _on_theme_changed(self, theme: str) -> None:
        """Called when SettingsView emits theme_changed."""
        settings.app_theme = theme  # type: ignore[assignment]
        self._apply_theme()
        self._update_status_bar()

    def _apply_theme(self) -> None:
        qss = get_stylesheet(settings.app_theme)
        self.setStyleSheet(qss)

    # ------------------------------------------------------------------
    # Status bar
    # ------------------------------------------------------------------

    def _update_status_bar(self, db_ok: bool = True) -> None:
        db_status = "DB: OK" if db_ok else "DB: ERROR"
        theme_label = f"Theme: {settings.app_theme.capitalize()}"
        self._status_bar.showMessage(
            f"Ready  |  {db_status}  |  Autosave: ON  |  {theme_label}"
        )
