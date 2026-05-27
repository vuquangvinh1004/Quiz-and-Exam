"""Session factory and context-manager helper.

Usage:
    from core.database.session import get_session

    with get_session() as session:
        bank = QuestionBank(name="My Bank")
        session.add(bank)
        # auto-committed on exit, rolled back on exception
"""
from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from core.database.connection import create_db_engine

_SessionFactory: sessionmaker | None = None
_SessionFactoryEngine: Engine | None = None


def _build_factory(engine: Engine) -> sessionmaker:
    return sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )


def _set_shared_factory(engine: Engine) -> None:
    global _SessionFactory, _SessionFactoryEngine
    old_engine = _SessionFactoryEngine
    _SessionFactory = _build_factory(engine)
    _SessionFactoryEngine = engine
    if old_engine is not None and old_engine is not engine:
        old_engine.dispose()


def _get_factory(db_path: Path | None = None) -> sessionmaker:
    """Return or build the shared session factory."""
    global _SessionFactory
    if _SessionFactory is None or db_path is not None:
        _set_shared_factory(create_db_engine(db_path))
    return _SessionFactory


def reset_session_factory(db_path: Path | None = None) -> None:
    """Force recreation of the session factory (used in tests)."""
    engine = create_db_engine(db_path)
    _set_shared_factory(engine)


@contextmanager
def get_session(db_path: Path | None = None) -> Generator[Session, None, None]:
    """Context manager that yields a transactional session.

    Commits on clean exit, rolls back on any exception, always closes.
    """
    factory = _get_factory(db_path)
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
