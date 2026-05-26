"""Pytest configuration and shared fixtures for all tests."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.database.connection import init_db
from core.database.models import Base
from core.database.session import reset_session_factory


@pytest.fixture(scope="function")
def in_memory_engine():
    """Create an isolated SQLite in-memory engine for each test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(in_memory_engine):
    """Return a transactional session backed by the in-memory engine.

    Automatically rolls back after each test so state does not bleed over.
    """
    factory = sessionmaker(bind=in_memory_engine, autoflush=False, autocommit=False)
    session = factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
