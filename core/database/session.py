"""Session factory and context-manager helper.

Usage:
    from core.database.session import get_session

    with get_session() as session:
        bank = QuestionBank(name="My Bank")
        session.add(bank)
        # auto-committed on exit, rolled back on exception
"""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

from sqlalchemy.orm import Session, sessionmaker

from core.database.connection import create_db_engine

_SessionFactory: Optional[sessionmaker] = None


def _get_factory(db_path: Optional[Path] = None) -> sessionmaker:
    """Return or build the shared session factory."""
    global _SessionFactory
    if _SessionFactory is None or db_path is not None:
        engine = create_db_engine(db_path)
        _SessionFactory = sessionmaker(
            bind=engine, autoflush=False, autocommit=False,
            expire_on_commit=False,
        )
    return _SessionFactory


def reset_session_factory(db_path: Optional[Path] = None) -> None:
    """Force recreation of the session factory (used in tests)."""
    global _SessionFactory
    engine = create_db_engine(db_path)
    _SessionFactory = sessionmaker(
        bind=engine, autoflush=False, autocommit=False,
        expire_on_commit=False,
    )


@contextmanager
def get_session(db_path: Optional[Path] = None) -> Generator[Session, None, None]:
    """Context manager that yields a transactional session.

    Commits on clean exit, rolls back on any exception, always closes.
    """
    factory = _get_factory(db_path)
    session: Session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
