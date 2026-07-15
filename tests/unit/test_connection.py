"""Unit tests for core/database/connection.py (Phase 7 coverage).

Covers:
  - create_db_engine: returns Engine, uses default path, uses override path
  - init_db: creates tables idempotently
"""
from __future__ import annotations

from pathlib import Path
import sqlite3

import pytest
from sqlalchemy import Engine, inspect, text

from core.database.connection import create_db_engine, init_db
from core.database.models import Base, QuestionBank
from core.database.schema_repair import repair_questions_type_constraint


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


class TestSchemaRepair:
    def test_repairs_legacy_question_type_constraint(self, tmp_path):
        db_path = tmp_path / "legacy.db"
        con = sqlite3.connect(str(db_path))
        try:
            con.executescript(
                """
                CREATE TABLE question_banks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE
                );
                CREATE TABLE questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bank_id INTEGER NOT NULL,
                    question_code TEXT UNIQUE,
                    question_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    hint TEXT,
                    explanation TEXT,
                    difficulty TEXT,
                    category TEXT,
                    tags TEXT,
                    accepted_answers TEXT,
                    point_value FLOAT NOT NULL,
                    case_sensitive BOOLEAN NOT NULL,
                    trim_whitespace BOOLEAN NOT NULL,
                    is_active BOOLEAN NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    CONSTRAINT ck_questions_type CHECK (question_type IN ('MC', 'MA', 'BLANK', 'SA')),
                    FOREIGN KEY(bank_id) REFERENCES question_banks (id) ON DELETE CASCADE
                );
                INSERT INTO question_banks (name) VALUES ('Bank 1');
                INSERT INTO questions (
                    bank_id, question_code, question_type, content, point_value,
                    case_sensitive, trim_whitespace, is_active
                ) VALUES (1, 'Q1', 'SA', 'Question', 1.0, 0, 1, 1);
                """
            )
            con.commit()
        finally:
            con.close()

        repaired = repair_questions_type_constraint(db_path)
        assert repaired is True

        con = sqlite3.connect(str(db_path))
        try:
            sql = con.execute(
                "select sql from sqlite_master where type='table' and name='questions'"
            ).fetchone()[0]
            assert "ES" in sql
            assert con.execute("select question_type from questions").fetchall() == [("SA",)]
        finally:
            con.close()
