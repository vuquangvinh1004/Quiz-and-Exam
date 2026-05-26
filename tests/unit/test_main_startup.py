from __future__ import annotations

from pathlib import Path

import main
from core.utils.exceptions import MigrationError


def test_can_fallback_when_db_missing(tmp_path) -> None:
    db_path = tmp_path / "missing.db"
    assert main._can_fallback_to_init_db(db_path) is True


def test_can_fallback_when_db_zero_size(tmp_path) -> None:
    db_path = tmp_path / "empty.db"
    db_path.write_bytes(b"")
    assert main._can_fallback_to_init_db(db_path) is True


def test_no_fallback_when_db_has_content(tmp_path) -> None:
    db_path = tmp_path / "existing.db"
    db_path.write_bytes(b"sqlite-header")
    assert main._can_fallback_to_init_db(db_path) is False


def test_initialize_database_runs_migration(monkeypatch) -> None:
    called = {"migrate": 0}

    def _ok() -> None:
        called["migrate"] += 1

    monkeypatch.setattr(main, "_run_startup_migrations", _ok)
    main._initialize_database()
    assert called["migrate"] == 1


def test_initialize_database_fallbacks_for_fresh_db(monkeypatch) -> None:
    called = {"init": 0}

    def _fail() -> None:
        raise MigrationError("boom")

    def _init(_engine) -> None:
        called["init"] += 1

    monkeypatch.setattr(main, "_run_startup_migrations", _fail)
    monkeypatch.setattr(main, "_can_fallback_to_init_db", lambda: True)
    monkeypatch.setattr(main, "create_db_engine", lambda: object())
    monkeypatch.setattr(main, "init_db", _init)

    main._initialize_database()
    assert called["init"] == 1


def test_initialize_database_raises_for_existing_db(monkeypatch) -> None:
    def _fail() -> None:
        raise MigrationError("boom")

    monkeypatch.setattr(main, "_run_startup_migrations", _fail)
    monkeypatch.setattr(main, "_can_fallback_to_init_db", lambda: False)

    try:
        main._initialize_database()
    except MigrationError:
        return
    assert False, "Expected MigrationError when migration fails on existing DB"
