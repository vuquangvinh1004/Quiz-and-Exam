"""One-off schema repair helpers for legacy SQLite databases."""
from __future__ import annotations

import sqlite3
from pathlib import Path


_LEGACY_QUESTION_TYPE_CONSTRAINT = "question_type IN ('MC', 'MA', 'BLANK', 'SA')"
_CURRENT_QUESTION_TYPE_CONSTRAINT = "question_type IN ('MC', 'MA', 'BLANK', 'TF', 'SA', 'ES')"


def repair_questions_type_constraint(db_path: Path) -> bool:
    """Repair legacy question_type constraint if the SQLite schema is stale.

    Returns True when a repair was applied.
    """
    if not db_path.exists() or db_path.stat().st_size == 0:
        return False

    con = sqlite3.connect(str(db_path))
    try:
        cur = con.cursor()
        row = cur.execute(
            "select sql from sqlite_master where type='table' and name='questions'"
        ).fetchone()
        if row is None:
            return False
        sql = row[0] or ""
        if "ES" in sql and "TF" in sql:
            return False
        if _LEGACY_QUESTION_TYPE_CONSTRAINT not in sql:
            return False
        columns = [info[1] for info in cur.execute("pragma table_info(questions)").fetchall()]
        has_learning_outcome = "learning_outcome_code" in columns

        create_columns = [
            "id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT",
            "bank_id INTEGER NOT NULL",
            "question_code TEXT",
            "question_type TEXT NOT NULL",
            "content TEXT NOT NULL",
            "hint TEXT",
            "explanation TEXT",
            "difficulty TEXT",
        ]
        if has_learning_outcome:
            create_columns.append("learning_outcome_code TEXT")
        create_columns.extend(
            [
                "category TEXT",
                "tags TEXT",
                "accepted_answers TEXT",
                "point_value FLOAT NOT NULL",
                "case_sensitive BOOLEAN NOT NULL",
                "trim_whitespace BOOLEAN NOT NULL",
                "is_active BOOLEAN NOT NULL",
                "created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL",
                "updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL",
            ]
        )
        insert_columns = [
            "id",
            "bank_id",
            "question_code",
            "question_type",
            "content",
            "hint",
            "explanation",
            "difficulty",
        ]
        select_columns = list(insert_columns)
        if has_learning_outcome:
            insert_columns.append("learning_outcome_code")
            select_columns.append("learning_outcome_code")
        insert_columns.extend(
            [
                "category",
                "tags",
                "accepted_answers",
                "point_value",
                "case_sensitive",
                "trim_whitespace",
                "is_active",
                "created_at",
                "updated_at",
            ]
        )
        select_columns.extend(
            [
                "category",
                "tags",
                "accepted_answers",
                "point_value",
                "case_sensitive",
                "trim_whitespace",
                "is_active",
                "created_at",
                "updated_at",
            ]
        )

        cur.execute("PRAGMA foreign_keys=OFF")
        cur.execute("BEGIN")
        try:
            cur.executescript(
                f"""
                CREATE TABLE questions_new (
                    {",\n                    ".join(create_columns)},
                    CONSTRAINT ck_questions_type CHECK ({_CURRENT_QUESTION_TYPE_CONSTRAINT}),
                    CONSTRAINT uq_questions_question_code UNIQUE (question_code),
                    CONSTRAINT fk_questions_bank_id FOREIGN KEY(bank_id) REFERENCES question_banks (id) ON DELETE CASCADE
                );
                INSERT INTO questions_new (
                    {", ".join(insert_columns)}
                )
                SELECT
                    {", ".join(select_columns)}
                FROM questions;
                DROP TABLE questions;
                ALTER TABLE questions_new RENAME TO questions;
                CREATE INDEX ix_questions_bank_id ON questions (bank_id);
                """
            )
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            cur.execute("PRAGMA foreign_keys=ON")
        return True
    finally:
        con.close()


__all__ = ["repair_questions_type_constraint"]
