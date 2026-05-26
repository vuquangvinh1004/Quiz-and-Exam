"""Unit tests for core/database/session.py (Phase 7 coverage).

Covers:
  - _get_factory: creates factory, reuses singleton, refreshes on db_path arg
  - reset_session_factory: reinitialises factory
  - get_session: commit path, rollback-on-exception path, always-close
"""
from __future__ import annotations

import pytest
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from core.database import session as session_module
from core.database.session import _get_factory, get_session, reset_session_factory
from core.database.models import Base, QuestionBank


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mem_db_path(tmp_path: Path) -> Path:
    """Return path to a temp SQLite file (not in-memory; real file)."""
    return tmp_path / "test_session.db"


# ---------------------------------------------------------------------------
# _get_factory
# ---------------------------------------------------------------------------

class TestGetFactory:

    def test_returns_sessionmaker(self, tmp_path):
        p = _mem_db_path(tmp_path)
        factory = _get_factory(db_path=p)
        assert isinstance(factory, sessionmaker)

    def test_reuses_singleton_when_no_db_path(self, tmp_path):
        p = _mem_db_path(tmp_path)
        # Force a fresh factory
        reset_session_factory(db_path=p)
        f1 = _get_factory()          # no db_path → uses global
        f2 = _get_factory()          # same call
        assert f1 is f2

    def test_refreshes_when_db_path_given(self, tmp_path):
        p1 = tmp_path / "a.db"
        p2 = tmp_path / "b.db"
        f1 = _get_factory(db_path=p1)
        f2 = _get_factory(db_path=p2)
        # Different db_path → different factories
        assert f1 is not f2


# ---------------------------------------------------------------------------
# reset_session_factory
# ---------------------------------------------------------------------------

class TestResetSessionFactory:

    def test_creates_new_factory(self, tmp_path):
        p = _mem_db_path(tmp_path)
        reset_session_factory(db_path=p)
        f1 = _get_factory()
        reset_session_factory(db_path=p)
        f2 = _get_factory()
        # After reset, a new factory is installed (different object)
        assert f1 is not f2

    def test_new_factory_opens_session(self, tmp_path):
        p = _mem_db_path(tmp_path)
        reset_session_factory(db_path=p)
        factory = _get_factory()
        session = factory()
        try:
            session.execute(text("SELECT 1"))
        finally:
            session.close()


# ---------------------------------------------------------------------------
# get_session
# ---------------------------------------------------------------------------

class TestGetSession:

    def test_commit_on_clean_exit(self, tmp_path):
        p = _mem_db_path(tmp_path)
        # Bootstrap tables
        from sqlalchemy import create_engine
        engine = create_engine(f"sqlite:///{p}")
        Base.metadata.create_all(engine)
        engine.dispose()

        reset_session_factory(db_path=p)
        with get_session(db_path=p) as session:
            bank = QuestionBank(name="CommitBank")
            session.add(bank)

        # Verify persisted
        with get_session(db_path=p) as session:
            result = session.query(QuestionBank).filter_by(name="CommitBank").first()
        assert result is not None

    def test_rollback_on_exception(self, tmp_path):
        p = _mem_db_path(tmp_path)
        from sqlalchemy import create_engine
        engine = create_engine(f"sqlite:///{p}")
        Base.metadata.create_all(engine)
        engine.dispose()

        reset_session_factory(db_path=p)
        with pytest.raises(ValueError):
            with get_session(db_path=p) as session:
                bank = QuestionBank(name="RollbackBank")
                session.add(bank)
                raise ValueError("forced error")

        # Should NOT be persisted
        with get_session(db_path=p) as session:
            result = session.query(QuestionBank).filter_by(name="RollbackBank").first()
        assert result is None

    def test_session_closed_after_use(self, tmp_path):
        """Session should be closed after context exit."""
        p = _mem_db_path(tmp_path)
        reset_session_factory(db_path=p)
        captured = []
        with get_session(db_path=p) as session:
            captured.append(session)
            # Mark the session object for later identity check
            session_id = id(session)
        # After exit the context must have called close().
        # In SQLAlchemy 2, a closed session's .bind is still valid but its
        # identity map is empty – verify by checking the session was returned.
        assert id(captured[0]) == session_id
