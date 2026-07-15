"""Quiz Desktop App – entry point.

Usage:
    python main.py

Responsibilities:
1. Ensure data directories exist.
2. Configure logging.
3. Initialize the database (run migrations).
4. Start the PySide6 application and show the main window.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from config.paths import APP_DIR, DB_PATH, LOGS_DIR, ensure_data_dirs
from config.settings import settings
from core.database.connection import create_db_engine, init_db
from core.database.schema_repair import repair_questions_type_constraint
from core.utils.exceptions import MigrationError
from core.utils.logger import configure_logging, get_logger

logger = get_logger(__name__)


def _run_startup_migrations() -> None:
    """Apply any pending Alembic migrations.

    Raises:
        MigrationError: If Alembic upgrade fails.
    """
    try:
        from alembic import command
        from alembic.config import Config

        alembic_cfg = Config(str(APP_DIR / "alembic.ini"))
        command.upgrade(alembic_cfg, "head")
    except Exception as exc:  # pragma: no cover
        raise MigrationError("Startup migration failed") from exc


def _can_fallback_to_init_db(db_path: Path = DB_PATH) -> bool:
    """Allow create_all fallback only when DB is truly fresh/missing."""
    if not db_path.exists():
        return True
    try:
        return db_path.stat().st_size == 0
    except OSError:
        return False


def _initialize_database() -> None:
    """Initialize DB with strict migration-first policy."""
    try:
        _run_startup_migrations()
    except MigrationError as exc:
        if _can_fallback_to_init_db():
            logger.warning(
                "Migration failed on fresh DB; falling back to init_db(create_all)."
            )
            engine = create_db_engine()
            init_db(engine)
            return
        logger.error(f"Migration failed on existing DB; startup aborted: {exc}")
        raise

    if repair_questions_type_constraint(DB_PATH):
        logger.warning("Repaired legacy questions schema to allow ES/TF question types.")


def main() -> int:
    """Application entry point."""
    # 1. Directories
    ensure_data_dirs()

    # 2. Logging
    configure_logging(log_dir=LOGS_DIR, level=settings.log_level)
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")

    # 3. Database – strict migration-first startup
    try:
        _initialize_database()
    except MigrationError as exc:
        logger.critical(f"Cannot start app due to migration error: {exc}")
        return 1

    # 4. Qt application
    app = QApplication(sys.argv)
    app.setApplicationName(settings.app_name)
    app.setApplicationVersion(settings.app_version)

    # Prevent multiple instances – if already running, the second launch exits.
    from PySide6.QtNetwork import QLocalServer, QLocalSocket
    _lock_name = f"QuizDesktopApp_{settings.app_name}"
    _sock = QLocalSocket()
    _sock.connectToServer(_lock_name)
    if _sock.waitForConnected(300):
        # Another instance is already running – just exit
        _sock.disconnectFromServer()
        logger.warning("Another instance is already running. Exiting.")
        return 0
    # Clean up any stale socket left by a previous crashed process
    QLocalServer.removeServer(_lock_name)
    _lock_server = QLocalServer()
    _lock_server.listen(_lock_name)

    # Set application icon (used in taskbar, title bar, Alt+Tab switcher)
    # Prefer .ico (user-replaceable); fall back to .png
    _icon_path = APP_DIR / "assets" / "icons" / "app_icon.ico"
    if not _icon_path.exists():
        _icon_path = APP_DIR / "assets" / "icons" / "app_icon.png"
    if _icon_path.exists():
        app.setWindowIcon(QIcon(str(_icon_path)))
    else:
        logger.warning(f"App icon not found: {_icon_path}")

    # Windows: set explicit App User Model ID so the taskbar shows the app icon
    # instead of the generic Python interpreter icon
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                f"QuizApp.{settings.app_name}.{settings.app_version}"
            )
        except Exception:  # pragma: no cover
            pass  # Non-critical – silently skip on unsupported environments

    from ui.main_window import MainWindow

    window = MainWindow()
    window.show()
    # Bring window to front regardless of what else is open
    window.raise_()
    window.activateWindow()
    window.setWindowState(
        window.windowState() & ~Qt.WindowState.WindowMinimized
        | Qt.WindowState.WindowActive
    )

    logger.info("Main window shown – entering event loop.")
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
