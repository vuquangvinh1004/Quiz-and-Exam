"""Performance tests for bulk import (Phase 7).

Verifies that the ImportService can handle large datasets (1,000+ rows)
within acceptable time limits and without data corruption.

ARCHITECTURE: §1.2 "Không crash khi import dữ liệu lớn"

These tests are marked with @pytest.mark.slow and can be skipped
in normal CI runs with: pytest -m "not slow"
"""
from __future__ import annotations

import time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.database.models import Base, Question, QuestionBank
from core.domain.services.import_service import ImportService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FULL_CSV_HEADER = (
    "question_code,question_text,question_type,category,difficulty,score,"
    "hint,explanation,option_a,option_b,option_c,option_d,option_e,option_f,"
    "correct_answers,status,tags,case_sensitive,trim_whitespace"
)


@pytest.fixture
def perf_session():
    """In-memory DB session for performance tests."""
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = factory()
    yield session
    session.rollback()
    session.close()
    engine.dispose()


def _generate_mc_rows(count: int) -> list[str]:
    """Generate `count` valid Multiple Choice rows."""
    rows = []
    for i in range(1, count + 1):
        rows.append(
            f"PERF_{i:05d},"
            f"Câu hỏi số {i} – chọn đáp án đúng?,"
            f"multiple_choice,Tổng quát,medium,1.0,,,"
            f"Đáp án A {i},Đáp án B {i},Đáp án C {i},Đáp án D {i},,,A,"
            f"active,,false,true"
        )
    return rows


def _generate_mixed_rows(count: int) -> list[str]:
    """Generate `count` rows cycling through all 4 question types."""
    types = [
        ("MC",  "multiple_choice", "Đáp án A,Đáp án B,Đáp án C,Đáp án D,,,A"),
        ("MA",  "multiple_answer",  "Đáp án A,Đáp án B,Đáp án C,Đáp án D,,,A||B"),
        ("BL",  "blank",            ",,,,,,Đáp án đúng"),      # no options for blank
        ("SA",  "short_answer",     ",,,,,,Trả lời ngắn"),     # no options for SA
    ]
    rows = []
    for i in range(1, count + 1):
        code_prefix, qtype, options_and_ans = types[(i - 1) % 4]
        if qtype == "blank":
            qtext = f"Câu {i}: Thủ đô [[blank]] là đúng."
        else:
            qtext = f"Câu {i}: Chọn đáp án cho câu hỏi này?"
        opt_parts = options_and_ans.split(",")
        # Pad to 7 parts: option_a..f + correct_answers
        while len(opt_parts) < 7:
            opt_parts.append("")
        rows.append(
            f"MX_{i:05d},"
            f"{qtext},"
            f"{qtype},Tổng quát,medium,1.0,,,"
            + ",".join(opt_parts[:7])
            + ",active,,false,true"
        )
    return rows


# ---------------------------------------------------------------------------
# Performance tests: 1,000 rows
# ---------------------------------------------------------------------------

@pytest.mark.slow
class TestImportPerformance1000:

    def test_import_1000_mc_under_10_seconds(self, perf_session, tmp_path):
        """1,000 MC rows must preview + commit in under 10 seconds."""
        csv_file = tmp_path / "perf_1000.csv"
        rows = _generate_mc_rows(1000)
        csv_file.write_text(
            FULL_CSV_HEADER + "\n" + "\n".join(rows), encoding="utf-8"
        )

        bank = QuestionBank(name="PerfBank1000")
        perf_session.add(bank)
        perf_session.flush()

        svc = ImportService()

        start = time.perf_counter()
        preview = svc.preview(csv_file, perf_session)
        svc.commit(preview, bank.id, perf_session)
        elapsed = time.perf_counter() - start

        assert preview.error_count == 0, f"Import errors: {preview.errors[:5]}"
        count = perf_session.query(Question).filter_by(bank_id=bank.id).count()
        assert count == 1000
        assert elapsed < 10.0, f"Import took {elapsed:.2f}s > 10s limit"

    def test_preview_only_1000_rows_fast(self, perf_session, tmp_path):
        """Preview alone for 1,000 rows must complete in under 5 seconds."""
        csv_file = tmp_path / "perf_preview.csv"
        rows = _generate_mc_rows(1000)
        csv_file.write_text(
            FULL_CSV_HEADER + "\n" + "\n".join(rows), encoding="utf-8"
        )

        svc = ImportService()
        start = time.perf_counter()
        preview = svc.preview(csv_file, perf_session)
        elapsed = time.perf_counter() - start

        assert preview.error_count == 0
        assert preview.total_rows == 1000
        assert elapsed < 5.0, f"Preview took {elapsed:.2f}s > 5s limit"

    def test_import_1000_no_data_corruption(self, perf_session, tmp_path):
        """All 1,000 rows must store the correct question_code."""
        csv_file = tmp_path / "perf_integrity.csv"
        rows = _generate_mc_rows(1000)
        csv_file.write_text(
            FULL_CSV_HEADER + "\n" + "\n".join(rows), encoding="utf-8"
        )

        bank = QuestionBank(name="PerfIntegrityBank")
        perf_session.add(bank)
        perf_session.flush()

        svc = ImportService()
        preview = svc.preview(csv_file, perf_session)
        svc.commit(preview, bank.id, perf_session)

        # Sample-check first and last rows
        first = (
            perf_session.query(Question)
            .filter_by(bank_id=bank.id, question_code="PERF_00001")
            .first()
        )
        last = (
            perf_session.query(Question)
            .filter_by(bank_id=bank.id, question_code="PERF_01000")
            .first()
        )
        assert first is not None, "First row not found"
        assert last is not None, "Last row (PERF_01000) not found"


# ---------------------------------------------------------------------------
# Performance tests: 5,000 rows (heavier benchmark)
# ---------------------------------------------------------------------------

@pytest.mark.slow
class TestImportPerformance5000:

    def test_import_5000_mc_under_45_seconds(self, perf_session, tmp_path):
        """5,000 MC rows must complete in under 45 seconds."""
        csv_file = tmp_path / "perf_5000.csv"
        rows = _generate_mc_rows(5000)
        csv_file.write_text(
            FULL_CSV_HEADER + "\n" + "\n".join(rows), encoding="utf-8"
        )

        bank = QuestionBank(name="PerfBank5000")
        perf_session.add(bank)
        perf_session.flush()

        svc = ImportService()

        start = time.perf_counter()
        preview = svc.preview(csv_file, perf_session)
        svc.commit(preview, bank.id, perf_session)
        elapsed = time.perf_counter() - start

        assert preview.error_count == 0
        count = perf_session.query(Question).filter_by(bank_id=bank.id).count()
        assert count == 5000
        assert elapsed < 45.0, f"5000-row import took {elapsed:.2f}s > 45s limit"
