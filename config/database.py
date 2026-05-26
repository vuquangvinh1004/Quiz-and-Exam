"""Database engine and session factory configuration."""
from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config.paths import DB_PATH, ensure_data_dirs


def _build_database_url(db_path: Path) -> str:
    return f"sqlite:///{db_path.as_posix()}"


def get_engine(db_path: Path | None = None):
    """Return a SQLAlchemy engine for the given path (default: DB_PATH)."""
    ensure_data_dirs()
    path = db_path or DB_PATH
    url = _build_database_url(path)
    return create_engine(
        url,
        connect_args={"check_same_thread": False},
        echo=False,
    )


def get_session_factory(db_path: Path | None = None):
    """Return a sessionmaker bound to the configured engine."""
    engine = get_engine(db_path)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)
