"""Database connection management.

Provides a single application-level engine instance.
Use ``get_engine()`` for a fresh engine (tests) or the module singleton.
"""
from __future__ import annotations

from pathlib import Path

from sqlalchemy import Engine, create_engine

from config.paths import DB_PATH, ensure_data_dirs
from core.database.models import Base


def create_db_engine(db_path: Path | None = None) -> Engine:
    """Create and return a SQLAlchemy Engine.

    Args:
        db_path: Override the default DB_PATH (useful in tests).
    """
    ensure_data_dirs()
    path = db_path or DB_PATH
    url = f"sqlite:///{path.as_posix()}"
    return create_engine(
        url,
        connect_args={"check_same_thread": False},
        echo=False,
    )


def init_db(engine: Engine) -> None:
    """Create all tables from the ORM metadata if they do not exist.

    This is a convenience for first-run initialization.
    Full schema migrations must use Alembic.
    """
    Base.metadata.create_all(engine)
