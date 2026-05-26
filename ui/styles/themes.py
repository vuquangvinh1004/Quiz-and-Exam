"""Light and dark theme stylesheets for the application."""
from __future__ import annotations

from ui.styles.design_tokens import get_theme_tokens

LIGHT_THEME_QSS = """
/* ── Global: force all widgets to light palette ─────────────────── */
QWidget {
    background-color: #f5f5f5;
    color: #212121;
    font-size: 14px;
}
QMainWindow {
    background-color: #f5f5f5;
}

/* ── Sidebar (keep dark) ─────────────────────────────────────────── */
QWidget#sidebar {
    background-color: #2c3e50;
    min-width: 180px;
    max-width: 180px;
}
QPushButton#nav_button {
    color: #ecf0f1;
    background-color: transparent;
    border: none;
    text-align: left;
    padding: 10px 16px;
    font-size: 14px;
}
QPushButton#nav_button:hover {
    background-color: #34495e;
}
QPushButton#nav_button:checked {
    background-color: #1abc9c;
    font-weight: bold;
    color: #ffffff;
}

/* ── Labels ─────────────────────────────────────────────────────── */
QLabel {
    background-color: transparent;
    color: #212121;
}

/* ── GroupBox ────────────────────────────────────────────────────── */
QGroupBox {
    background-color: #f5f5f5;
    color: #212121;
    border: 1px solid #d0d5dd;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 6px;
    font-weight: bold;
}
QGroupBox::title {
    color: #212121;
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    left: 10px;
}

/* ── Scroll areas ────────────────────────────────────────────────── */
QScrollArea {
    background-color: #f5f5f5;
    border: none;
}
QScrollArea > QWidget > QWidget {
    background-color: #f5f5f5;
}
QScrollBar:vertical, QScrollBar:horizontal {
    background-color: #e8e8e8;
    width: 10px;
    height: 10px;
}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background-color: #b0b0b0;
    border-radius: 5px;
    min-height: 20px;
    min-width: 20px;
}
QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {
    background-color: #888888;
}
QScrollBar::add-line, QScrollBar::sub-line {
    height: 0px;
    width: 0px;
}

/* ── List widget ─────────────────────────────────────────────────── */
QListWidget {
    background-color: #ffffff;
    color: #212121;
    border: 1px solid #d0d5dd;
    border-radius: 4px;
    outline: none;
}
QListWidget::item {
    color: #212121;
    padding: 6px 8px;
}
QListWidget::item:selected {
    background-color: #1abc9c;
    color: #ffffff;
}
QListWidget::item:hover:!selected {
    background-color: #e6f7f4;
}

/* ── Table widget ────────────────────────────────────────────────── */
QTableWidget {
    background-color: #ffffff;
    color: #212121;
    gridline-color: #e0e0e0;
    border: 1px solid #d0d5dd;
    border-radius: 4px;
    outline: none;
    alternate-background-color: #f8faff;
}
QTableWidget::item {
    color: #212121;
    padding: 4px 6px;
}
QTableWidget::item:selected {
    background-color: #1abc9c;
    color: #ffffff;
}
QHeaderView {
    background-color: #f0f0f0;
}
QHeaderView::section {
    background-color: #e8ecf0;
    color: #212121;
    border: none;
    border-right: 1px solid #d0d5dd;
    border-bottom: 1px solid #d0d5dd;
    padding: 5px 8px;
    font-weight: bold;
}
QHeaderView::section:last {
    border-right: none;
}

/* ── Tree widget ─────────────────────────────────────────────────── */
QTreeWidget {
    background-color: #ffffff;
    color: #212121;
    border: 1px solid #d0d5dd;
    outline: none;
}
QTreeWidget::item {
    color: #212121;
}
QTreeWidget::item:selected {
    background-color: #1abc9c;
    color: #ffffff;
}

/* ── Input fields ────────────────────────────────────────────────── */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #ffffff;
    color: #212121;
    border: 1px solid #b8bfc9;
    border-radius: 4px;
    padding: 4px 6px;
    selection-background-color: #1abc9c;
    selection-color: #ffffff;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border-color: #1abc9c;
}
QLineEdit:read-only {
    background-color: #f0f0f0;
    color: #666666;
}

/* ── ComboBox ────────────────────────────────────────────────────── */
QComboBox {
    background-color: #ffffff;
    color: #212121;
    border: 1px solid #b8bfc9;
    border-radius: 4px;
    padding: 4px 28px 4px 8px;
    min-height: 22px;
}
QComboBox:focus {
    border-color: #1abc9c;
}
QComboBox::drop-down {
    border: none;
    width: 22px;
}
QComboBox::down-arrow {
    width: 10px;
    height: 10px;
}
QComboBox QAbstractItemView {
    background-color: #ffffff;
    color: #212121;
    border: 1px solid #b8bfc9;
    selection-background-color: #1abc9c;
    selection-color: #ffffff;
    outline: none;
}

/* ── SpinBox ─────────────────────────────────────────────────────── */
QSpinBox, QDoubleSpinBox {
    background-color: #ffffff;
    color: #212121;
    border: 1px solid #b8bfc9;
    border-radius: 4px;
    padding: 4px 6px;
}
QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: #1abc9c;
}

/* ── CheckBox & RadioButton ──────────────────────────────────────── */
QCheckBox, QRadioButton {
    background-color: transparent;
    color: #212121;
    spacing: 6px;
}
QCheckBox::indicator, QRadioButton::indicator {
    width: 16px;
    height: 16px;
}

/* ── Standard buttons ────────────────────────────────────────────── */
QPushButton {
    background-color: #e8ecf0;
    color: #212121;
    border: 1px solid #c4cdd5;
    border-radius: 4px;
    padding: 5px 14px;
    min-height: 22px;
}
QPushButton:hover {
    background-color: #d8dfe8;
    border-color: #a8b5c0;
}
QPushButton:pressed {
    background-color: #c4cdd5;
}
QPushButton:disabled {
    background-color: #f0f0f0;
    color: #a0a0a0;
    border-color: #ddd;
}

/* ── Frame ───────────────────────────────────────────────────────── */
QFrame {
    background-color: transparent;
    color: #212121;
}
QFrame[frameShape="4"],
QFrame[frameShape="5"] {
    background-color: #d0d5dd;
    border: none;
    max-height: 1px;
    max-width: 1px;
}

/* ── Splitter ────────────────────────────────────────────────────── */
QSplitter::handle {
    background-color: #d0d5dd;
}
QSplitter::handle:horizontal {
    width: 2px;
}
QSplitter::handle:vertical {
    height: 2px;
}

/* ── Dialog ──────────────────────────────────────────────────────── */
QDialog {
    background-color: #f5f5f5;
    color: #212121;
}
/* ── Tab Widget ─────────────────────────────────────────────────── */
QTabWidget::pane {
    border: 1px solid #d0d5dd;
    background-color: #f5f5f5;
}
QTabWidget::tab-bar {
    alignment: left;
}
QTabBar::tab {
    background-color: #e0e4ea;
    color: #212121;
    border: 1px solid #c4cdd5;
    border-bottom: none;
    padding: 6px 16px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}
QTabBar::tab:selected {
    background-color: #f5f5f5;
    color: #212121;
    font-weight: bold;
    border-bottom: 2px solid #1abc9c;
}
QTabBar::tab:hover:!selected {
    background-color: #d0d5de;
}
/* ── Named labels ────────────────────────────────────────────────── */
QLabel#view_title {
    font-size: 20px;
    font-weight: bold;
    padding: 10px 16px 4px 16px;
}
QLabel#muted_label {
    color: #666666;
    font-size: 13px;
}

/* ── Stat card (Dashboard) ───────────────────────────────────────── */
QFrame#stat_card {
    background-color: #f0f4ff;
    border: 1px solid #c6d4f0;
    border-radius: 8px;
}
QLabel#stat_card_label {
    font-size: 13px;
    color: #555555;
    background-color: transparent;
}
QLabel#stat_card_value {
    font-size: 27px;
    font-weight: bold;
    color: #2468a8;
    background-color: transparent;
}

/* ── Status bar ──────────────────────────────────────────────────── */
QStatusBar {
    background-color: #e8ecf0;
    color: #444444;
    font-size: 13px;
    border-top: 1px solid #d0d5dd;
}

/* ── ToolTip ─────────────────────────────────────────────────────── */
QToolTip {
    background-color: #fffbe6;
    color: #212121;
    border: 1px solid #e8d44d;
    padding: 4px 6px;
    border-radius: 3px;
}
"""

DARK_THEME_QSS = """
/* ── Global: force all widgets to dark palette ──────────────────── */
QWidget {
    background-color: #1e1e1e;
    color: #d4d4d4;    font-size: 14px;}
QMainWindow {
    background-color: #1e1e1e;
}

/* ── Sidebar ─────────────────────────────────────────────────────── */
QWidget#sidebar {
    background-color: #252526;
    min-width: 180px;
    max-width: 180px;
}
QPushButton#nav_button {
    color: #d4d4d4;
    background-color: transparent;
    border: none;
    text-align: left;
    padding: 10px 16px;
    font-size: 14px;
}
QPushButton#nav_button:hover {
    background-color: #2d2d30;
}
QPushButton#nav_button:checked {
    background-color: #0e639c;
    font-weight: bold;
    color: #ffffff;
}

/* ── Labels ─────────────────────────────────────────────────────── */
QLabel {
    background-color: transparent;
    color: #d4d4d4;
}

/* ── GroupBox ────────────────────────────────────────────────────── */
QGroupBox {
    background-color: #252526;
    color: #d4d4d4;
    border: 1px solid #3e3e42;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 6px;
    font-weight: bold;
}
QGroupBox::title {
    color: #d4d4d4;
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    left: 10px;
}

/* ── Scroll areas ────────────────────────────────────────────────── */
QScrollArea {
    background-color: #1e1e1e;
    border: none;
}
QScrollArea > QWidget > QWidget {
    background-color: #1e1e1e;
}
QScrollBar:vertical, QScrollBar:horizontal {
    background-color: #2d2d30;
    width: 10px;
    height: 10px;
}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background-color: #555558;
    border-radius: 5px;
    min-height: 20px;
    min-width: 20px;
}
QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {
    background-color: #7a7a7f;
}
QScrollBar::add-line, QScrollBar::sub-line {
    height: 0px;
    width: 0px;
}

/* ── List widget ─────────────────────────────────────────────────── */
QListWidget {
    background-color: #252526;
    color: #d4d4d4;
    border: 1px solid #3e3e42;
    border-radius: 4px;
    outline: none;
}
QListWidget::item {
    color: #d4d4d4;
    padding: 6px 8px;
}
QListWidget::item:selected {
    background-color: #0e639c;
    color: #ffffff;
}
QListWidget::item:hover:!selected {
    background-color: #2d2d30;
}

/* ── Table widget ────────────────────────────────────────────────── */
QTableWidget {
    background-color: #252526;
    color: #d4d4d4;
    gridline-color: #3e3e42;
    border: 1px solid #3e3e42;
    border-radius: 4px;
    outline: none;
    alternate-background-color: #2a2a2d;
}
QTableWidget::item {
    color: #d4d4d4;
    padding: 4px 6px;
}
QTableWidget::item:selected {
    background-color: #0e639c;
    color: #ffffff;
}
QHeaderView {
    background-color: #2d2d30;
}
QHeaderView::section {
    background-color: #2d2d30;
    color: #d4d4d4;
    border: none;
    border-right: 1px solid #3e3e42;
    border-bottom: 1px solid #3e3e42;
    padding: 5px 8px;
    font-weight: bold;
}
QHeaderView::section:last {
    border-right: none;
}

/* ── Tree widget ─────────────────────────────────────────────────── */
QTreeWidget {
    background-color: #252526;
    color: #d4d4d4;
    border: 1px solid #3e3e42;
    outline: none;
}
QTreeWidget::item {
    color: #d4d4d4;
}
QTreeWidget::item:selected {
    background-color: #0e639c;
    color: #ffffff;
}

/* ── Input fields ────────────────────────────────────────────────── */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #3c3c3c;
    color: #d4d4d4;
    border: 1px solid #555558;
    border-radius: 4px;
    padding: 4px 6px;
    selection-background-color: #0e639c;
    selection-color: #ffffff;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border-color: #0e639c;
}
QLineEdit:read-only {
    background-color: #2d2d30;
    color: #888888;
}

/* ── ComboBox ────────────────────────────────────────────────────── */
QComboBox {
    background-color: #3c3c3c;
    color: #d4d4d4;
    border: 1px solid #555558;
    border-radius: 4px;
    padding: 4px 28px 4px 8px;
    min-height: 22px;
}
QComboBox:focus {
    border-color: #0e639c;
}
QComboBox::drop-down {
    border: none;
    width: 22px;
}
QComboBox QAbstractItemView {
    background-color: #3c3c3c;
    color: #d4d4d4;
    border: 1px solid #555558;
    selection-background-color: #0e639c;
    selection-color: #ffffff;
    outline: none;
}

/* ── SpinBox ─────────────────────────────────────────────────────── */
QSpinBox, QDoubleSpinBox {
    background-color: #3c3c3c;
    color: #d4d4d4;
    border: 1px solid #555558;
    border-radius: 4px;
    padding: 4px 6px;
}
QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: #0e639c;
}

/* ── CheckBox & RadioButton ──────────────────────────────────────── */
QCheckBox, QRadioButton {
    background-color: transparent;
    color: #d4d4d4;
    spacing: 6px;
}
QCheckBox::indicator, QRadioButton::indicator {
    width: 16px;
    height: 16px;
}

/* ── Buttons ─────────────────────────────────────────────────────── */
QPushButton {
    background-color: #3c3c3c;
    color: #d4d4d4;
    border: 1px solid #555558;
    border-radius: 4px;
    padding: 5px 14px;
    min-height: 22px;
}
QPushButton:hover {
    background-color: #454545;
    border-color: #6a6a6a;
}
QPushButton:pressed {
    background-color: #555558;
}
QPushButton:disabled {
    background-color: #2d2d30;
    color: #666666;
    border-color: #3e3e42;
}

/* ── Frame ─────────────────────────────────────────────────────────*/
QFrame {
    background-color: transparent;
    color: #d4d4d4;
}

/* ── Splitter ────────────────────────────────────────────────────── */
QSplitter::handle {
    background-color: #3e3e42;
}
QSplitter::handle:horizontal {
    width: 2px;
}
QSplitter::handle:vertical {
    height: 2px;
}

/* ── Dialog ──────────────────────────────────────────────────────── */
QDialog {
    background-color: #1e1e1e;
    color: #d4d4d4;
}

/* ── Tab Widget ──────────────────────────────────────────────────── */
QTabWidget::pane {
    border: 1px solid #3c3c3c;
    background-color: #1e1e1e;
}
QTabWidget::tab-bar {
    alignment: left;
}
QTabBar::tab {
    background-color: #2d2d2d;
    color: #d4d4d4;
    border: 1px solid #3c3c3c;
    border-bottom: none;
    padding: 6px 16px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}
QTabBar::tab:selected {
    background-color: #1e1e1e;
    color: #ffffff;
    font-weight: bold;
    border-bottom: 2px solid #1abc9c;
}
QTabBar::tab:hover:!selected {
    background-color: #3a3a3a;
}

/* ── Named labels ────────────────────────────────────────────────── */
QLabel#view_title {
    font-size: 20px;
    font-weight: bold;
    padding: 10px 16px 4px 16px;
}
QLabel#muted_label {
    color: #aaaaaa;
    font-size: 13px;
}

/* ── Stat card (Dashboard) ───────────────────────────────────────── */
QFrame#stat_card {
    background-color: #2a3040;
    border: 1px solid #3a4860;
    border-radius: 8px;
}
QLabel#stat_card_label {
    font-size: 13px;
    color: #9090a0;
    background-color: transparent;
}
QLabel#stat_card_value {
    font-size: 27px;
    font-weight: bold;
    color: #4da8f0;
    background-color: transparent;
}

/* ── Status bar ──────────────────────────────────────────────────── */
QStatusBar {
    background-color: #007acc;
    color: #ffffff;
    font-size: 13px;
}

/* ── ToolTip ─────────────────────────────────────────────────────── */
QToolTip {
    background-color: #252526;
    color: #d4d4d4;
    border: 1px solid #555558;
    padding: 4px 6px;
    border-radius: 3px;
}
"""


_LIGHT_LITERAL_TOKEN_MAP: tuple[tuple[str, str], ...] = (
    ("#1abc9c", "color-primary"),
    ("#ffffff", "color-on-primary"),
    ("#f5f5f5", "color-bg-app"),
    ("#212121", "color-text-main"),
    ("#666666", "color-text-muted"),
    ("#d0d5dd", "color-border"),
    ("#2c3e50", "color-nav-bg"),
    ("#34495e", "color-nav-hover"),
    ("#ecf0f1", "color-nav-text"),
)

_DARK_LITERAL_TOKEN_MAP: tuple[tuple[str, str], ...] = (
    ("#0e639c", "color-primary"),
    ("#ffffff", "color-on-primary"),
    ("#1e1e1e", "color-bg-app"),
    ("#d4d4d4", "color-text-main"),
    ("#aaaaaa", "color-text-muted"),
    ("#3e3e42", "color-border"),
    ("#252526", "color-nav-bg"),
    ("#2d2d30", "color-nav-hover"),
)


def _apply_semantic_tokens(
    qss: str,
    theme: str,
    literal_token_map: tuple[tuple[str, str], ...],
) -> str:
    """Resolve key literal color roles from semantic theme tokens.

    This supports incremental migration from hardcoded QSS to token-driven
    styling without changing widget selectors and layout rules.
    """
    tokens = get_theme_tokens(theme)
    resolved = qss
    for literal_color, token_key in literal_token_map:
        token_color = tokens.get(token_key)
        if token_color:
            resolved = resolved.replace(literal_color, token_color)
    return resolved


def get_stylesheet(theme: str) -> str:
    """Return the QSS stylesheet string for the given theme name."""
    if theme == "dark":
        return _apply_semantic_tokens(
            DARK_THEME_QSS,
            "dark",
            _DARK_LITERAL_TOKEN_MAP,
        )
    return _apply_semantic_tokens(
        LIGHT_THEME_QSS,
        "light",
        _LIGHT_LITERAL_TOKEN_MAP,
    )
