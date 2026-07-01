"""Unit tests for dashboard facade overview loading."""
from __future__ import annotations

from pathlib import Path

import pytest
from core.database.connection import create_db_engine, init_db
from datetime import datetime, timedelta, timezone

from core.database.models import Attempt, Question, QuestionBank, Quiz
from core.database.session import get_session, reset_session_factory
from ui.facades.dashboard_facade import DashboardFacade


@pytest.fixture(autouse=True)
def _cleanup_shared_session_factory() -> None:
    yield
    cleanup_db = Path(".tmp") / "dashboard_facade_cleanup.db"
    cleanup_db.parent.mkdir(parents=True, exist_ok=True)
    engine = create_db_engine(db_path=cleanup_db)
    try:
        init_db(engine)
    finally:
        engine.dispose()
    reset_session_factory(db_path=cleanup_db)


def _init_temp_db(db_path: Path) -> None:
    engine = create_db_engine(db_path=db_path)
    try:
        init_db(engine)
    finally:
        engine.dispose()
    reset_session_factory(db_path=db_path)


def test_load_overview_includes_attempt_analytics(tmp_path) -> None:
    db_path = tmp_path / "dashboard_facade.db"
    _init_temp_db(db_path)

    with get_session() as session:
        bank = QuestionBank(name="Bank A")
        session.add(bank)
        session.flush()

        session.add(
            Question(
                bank_id=bank.id,
                question_code="MC-001",
                question_type="MC",
                content="Question 1",
                point_value=1.0,
                is_active=True,
            )
        )

        quiz = Quiz(
            title="Quiz A",
            bank_id=bank.id,
            mode="EXAM",
            time_limit_minutes=30,
            total_questions=1,
        )
        session.add(quiz)
        session.flush()

        session.add_all(
            [
                Attempt(
                    quiz_id=quiz.id,
                    mode="EXAM",
                    status="SUBMITTED",
                    score=8.0,
                    max_score=10.0,
                    correct_count=8,
                    incorrect_count=1,
                    skipped_count=1,
                    submitted_at=datetime.now(timezone.utc) - timedelta(days=1),
                ),
                Attempt(
                    quiz_id=quiz.id,
                    mode="PRACTICE",
                    status="TIME_UP",
                    score=6.0,
                    max_score=10.0,
                    correct_count=6,
                    incorrect_count=2,
                    skipped_count=2,
                    submitted_at=datetime.now(timezone.utc) - timedelta(days=2),
                ),
                Attempt(
                    quiz_id=quiz.id,
                    mode="STUDY",
                    status="IN_PROGRESS",
                    score=10.0,
                    max_score=10.0,
                    correct_count=10,
                    incorrect_count=0,
                    skipped_count=0,
                ),
            ]
        )

    overview = DashboardFacade().load_overview()

    assert overview.total_banks == 1
    assert overview.total_questions == 1
    assert overview.type_breakdown.mc == 1
    assert overview.attempt_stats.total_attempts == 2
    assert overview.attempt_stats.avg_score_pct == 70.0
    assert overview.attempt_stats.best_score_pct == 80.0
    assert overview.attempt_stats.total_correct == 14
    assert overview.attempt_stats.total_incorrect == 3
    assert overview.attempt_stats.total_skipped == 3
    assert overview.mode_breakdown.exam_count == 1
    assert overview.mode_breakdown.practice_count == 1
    assert overview.mode_breakdown.study_count == 0
    assert len(overview.recent_activity) == 7
    assert sum(point.attempts for point in overview.recent_activity) == 2
    assert overview.reporting_window_summary.total_attempts == 2
    assert overview.reporting_window_summary.active_banks == 1
    assert len(overview.reporting_bank_breakdown) == 1
    assert overview.reporting_bank_breakdown[0].bank_name == "Bank A"


def test_load_filtered_reporting_returns_snapshot(tmp_path) -> None:
    db_path = tmp_path / "dashboard_reporting.db"
    _init_temp_db(db_path)

    with get_session() as session:
        bank = QuestionBank(name="Bank Reporting")
        session.add(bank)
        session.flush()

        quiz = Quiz(
            title="Quiz Reporting",
            bank_id=bank.id,
            mode="EXAM",
            time_limit_minutes=30,
            total_questions=1,
        )
        session.add(quiz)
        session.flush()

        session.add(
            Attempt(
                quiz_id=quiz.id,
                mode="EXAM",
                status="SUBMITTED",
                score=7.0,
                max_score=10.0,
                correct_count=7,
                incorrect_count=2,
                skipped_count=1,
                submitted_at=datetime.now(timezone.utc) - timedelta(days=1),
            )
        )

    snapshot = DashboardFacade().load_filtered_reporting(
        bank_id=bank.id,
        quiz_id=quiz.id,
        days=7,
    )

    assert snapshot.mode_breakdown.exam_count == 1
    assert sum(point.attempts for point in snapshot.recent_activity) == 1
    assert snapshot.window_summary.total_attempts == 1
    assert snapshot.window_summary.active_banks == 1
    assert len(snapshot.bank_breakdown) == 1
    assert snapshot.bank_breakdown[0].bank_name == "Bank Reporting"


def test_export_reporting_csv_writes_expected_sections(tmp_path) -> None:
    db_path = tmp_path / "dashboard_reporting_csv.db"
    _init_temp_db(db_path)

    with get_session() as session:
        bank = QuestionBank(name="Bank CSV")
        session.add(bank)
        session.flush()

        quiz = Quiz(
            title="Quiz CSV",
            bank_id=bank.id,
            mode="EXAM",
            time_limit_minutes=30,
            total_questions=1,
        )
        session.add(quiz)
        session.flush()
        session.add(
            Attempt(
                quiz_id=quiz.id,
                mode="EXAM",
                status="SUBMITTED",
                score=9.0,
                max_score=10.0,
                correct_count=9,
                incorrect_count=1,
                skipped_count=0,
                submitted_at=datetime.now(timezone.utc) - timedelta(days=1),
            )
        )

    output_path = tmp_path / "reporting.csv"
    DashboardFacade().export_reporting_csv(
        output_path=output_path,
        bank_id=bank.id,
        quiz_id=quiz.id,
        days=7,
    )

    text = output_path.read_text(encoding="utf-8-sig")
    assert "section,metric,value" in text
    assert "summary,total_attempts,1" in text
    assert "mode_breakdown,exam_count,1" in text
    assert "recent_activity,date,attempts,avg_score_pct" in text
    assert "bank_breakdown,bank_name,attempt_count,quiz_count,avg_score_pct,best_score_pct,last_activity_at" in text
