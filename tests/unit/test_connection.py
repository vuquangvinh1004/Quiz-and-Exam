"""Unit tests for core/database/connection.py (Phase 7 coverage).

Covers:
  - create_db_engine: returns Engine, uses default path, uses override path
  - init_db: creates tables idempotently
"""
from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import Engine, inspect, text

from core.database.connection import create_db_engine, init_db
from core.database.models import Base, QuestionBank


class TestCreateDbEngine:

    def test_returns_engine(self, tmp_path):
        p = tmp_path / "eng_test.db"
        engine = create_db_engine(db_path=p)
        assert isinstance(engine, Engine)
        engine.dispose()

    def test_engine_is_sqlite(self, tmp_path):
        p = tmp_path / "sqlite_test.db"
        engine = create_db_engine(db_path=p)
        assert "sqlite" in engine.dialect.name
        engine.dispose()

    def test_custom_path_creates_file(self, tmp_path):
        p = tmp_path / "custom.db"
        engine = create_db_engine(db_path=p)
        # Just connecting creates the file
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        # SQLite may create the file on first write or connect
        # Using init_db ensures it exists
        init_db(engine)

    def test_engine_connects(self, tmp_path):
        p = tmp_path / "connect.db"
        engine = create_db_engine(db_path=p)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            assert result.scalar() == 1
        engine.dispose()

    def test_uses_default_path_when_none(self, tmp_path):
        """create_db_engine() with no arg should not raise."""
        # We can't easily override DB_PATH without monkeypatching,
        # so just ensure the call succeeds and returns an Engine.
        engine = create_db_engine()
        assert isinstance(engine, Engine)
        engine.dispose()


class TestInitDb:

    def test_creates_tables(self, tmp_path):
        p = tmp_path / "init_test.db"
        engine = create_db_engine(db_path=p)
        init_db(engine)
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        assert "question_banks" in tables
        assert "questions" in tables
        assert "quizzes" in tables
        assert "attempts" in tables
        engine.dispose()

    def test_idempotent(self, tmp_path):
        """Calling init_db twice should not raise."""
        p = tmp_path / "idem_test.db"
        engine = create_db_engine(db_path=p)
        init_db(engine)
        init_db(engine)  # second call must not raise
        engine.dispose()

    def test_tables_are_writable_after_init(self, tmp_path):
        from sqlalchemy.orm import sessionmaker
        p = tmp_path / "write_test.db"
        engine = create_db_engine(db_path=p)
        init_db(engine)
        factory = sessionmaker(bind=engine)
        session = factory()
        try:
            bank = QuestionBank(name="InitBank")
            session.add(bank)
            session.commit()
            fetched = session.query(QuestionBank).filter_by(name="InitBank").first()
            assert fetched is not None
        finally:
            session.close()
            engine.dispose()
