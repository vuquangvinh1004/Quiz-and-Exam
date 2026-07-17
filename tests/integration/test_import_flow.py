"""Integration tests: full import pipeline → DB persistence.

Tests the ImportService pipeline:
    preview(file_path, session) → commit(result, bank_id, session)

Verifies that valid rows land correctly in questions + question_options tables
and that invalid rows do NOT pollute the database.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy.orm import sessionmaker

from core.database.models import Question, QuestionBank, QuestionOption
from core.domain.services.import_service import ImportService
from core.utils.exceptions import ImportValidationError
from modules.question_bank.importer import QuestionFileParser

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def service() -> ImportService:
    return ImportService()


@pytest.fixture
def mem_session(in_memory_engine):
    """Transaction-based session over in-memory SQLite."""
    factory = sessionmaker(
        bind=in_memory_engine, autoflush=False, autocommit=False
    )
    session = factory()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def bank(mem_session):
    b = QuestionBank(name="TestBank")
    mem_session.add(b)
    mem_session.flush()
    return b


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FULL_CSV_HEADER = (
    "question_code,question_text,question_type,category,difficulty,score,"
    "hint,explanation,option_a,option_b,option_c,option_d,option_e,option_f,"
    "correct_answers,status,tags,case_sensitive,trim_whitespace\n"
)


def _write(tmp_path: Path, rows_csv: str, filename="import.csv") -> Path:
    p = tmp_path / filename
    p.write_text(FULL_CSV_HEADER + rows_csv, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestImportServicePreview:

    def test_preview_does_not_write_to_db(self, service, mem_session, bank, tmp_path):
        p = _write(
            tmp_path,
            "MC001,Q text?,multiple_choice,,easy,1,,,"
            "OptionA,OptionB,,,,,A,active,,,false,true\n",
        )
        result = service.preview(p, mem_session)
        # No writes should occur during preview
        count = mem_session.query(Question).count()
        assert count == 0
        assert len(result.parsed_questions) == 1

    def test_preview_with_invalid_file_raises_no_exception(
        self, service, mem_session, tmp_path
    ):
        p = _write(tmp_path, "bad_column,MC001\nno,data\n", filename="bad.csv")
        result = service.preview(p, mem_session)
        # Should return a result with errors, not raise
        assert result.has_errors

    def test_preview_large_file_adds_budget_warning(self, mem_session, tmp_path):
        service = ImportService(
            parser=QuestionFileParser(soft_row_limit=2, hard_row_limit=10)
        )
        p = _write(
            tmp_path,
            "".join(
                f"MC{i:03d},Q{i}?,multiple_choice,,easy,1,,,A{i},B{i},,,,,A,active,,false,true\n"
                for i in range(1, 4)
            ),
        )

        result = service.preview(p, mem_session)

        assert not result.has_errors
        assert any(
            issue.severity == "WARNING" and "File lớn" in issue.message
            for issue in result.issues
        )


class TestImportServiceCommit:

    def test_commit_mc_creates_question_and_options(
        self, service, mem_session, bank, tmp_path
    ):
        p = _write(
            tmp_path,
            "MC001,Thủ đô Việt Nam?,multiple_choice,Địa lý,easy,1,"
            ",,Hà Nội,HCM,Đà Nẵng,,,, A ,active,,false,true\n",
        )
        result = service.preview(p, mem_session)
        assert not result.has_errors

        summary = service.commit(result, bank.id, mem_session)
        mem_session.commit()

        assert summary.inserted == 1
        q = mem_session.query(Question).filter_by(question_code="MC001").one()
        assert q.question_type == "MC"
        assert q.content == "Thủ đô Việt Nam?"
        # Options
        opts = (
            mem_session.query(QuestionOption)
            .filter_by(question_id=q.id)
            .all()
        )
        assert len(opts) == 3
        correct_opts = [o for o in opts if o.is_correct]
        assert len(correct_opts) == 1
        assert correct_opts[0].option_key == "A"

    def test_commit_ma_saves_correct_options(
        self, service, mem_session, bank, tmp_path
    ):
        p = _write(
            tmp_path,
            "MA001,Which are interpreted?,multiple_answer,,medium,1.5,"
            ",,Python,Java,C++,JavaScript,,,A||D,active,,false,true\n",
        )
        result = service.preview(p, mem_session)
        assert not result.has_errors

        service.commit(result, bank.id, mem_session)
        mem_session.commit()

        q = mem_session.query(Question).filter_by(question_code="MA001").one()
        correct_opts = [
            o for o in mem_session.query(QuestionOption).filter_by(question_id=q.id)
            if o.is_correct
        ]
        correct_keys = {o.option_key for o in correct_opts}
        assert correct_keys == {"A", "D"}

    def test_commit_blank_saves_accepted_answers_as_json(
        self, service, mem_session, bank, tmp_path
    ):
        p = _write(
            tmp_path,
            "BL001,Thủ đô VN là ________.,blank,,easy,1,"
            ",,,,,,,, Hà Nội || Ha Noi ,active,,false,true\n",
        )
        result = service.preview(p, mem_session)
        assert not result.has_errors

        service.commit(result, bank.id, mem_session)
        mem_session.commit()

        q = mem_session.query(Question).filter_by(question_code="BL001").one()
        answers = json.loads(q.accepted_answers)
        assert "Hà Nội" in answers
        assert "Ha Noi" in answers

    def test_commit_sa_saves_accepted_answers_as_json(
        self, service, mem_session, bank, tmp_path
    ):
        p = _write(
            tmp_path,
            "SA001,EOQ là viết tắt của gì?,short_answer,,easy,1,"
            ",,,,,,,, Economic Order Quantity||EOQ ,active,,false,true\n",
        )
        result = service.preview(p, mem_session)
        assert not result.has_errors

        service.commit(result, bank.id, mem_session)
        mem_session.commit()

        q = mem_session.query(Question).filter_by(question_code="SA001").one()
        answers = json.loads(q.accepted_answers)
        assert "EOQ" in answers

    def test_commit_raises_when_has_errors(
        self, service, mem_session, bank, tmp_path
    ):
        from modules.question_bank.importer import ImportIssue, ParseResult
        bad_result = ParseResult(total_rows=1)
        bad_result.issues.append(
            ImportIssue(row=1, severity="ERROR", message="deliberately bad")
        )
        with pytest.raises(ImportValidationError):
            service.commit(bad_result, bank.id, mem_session)

    def test_commit_multiple_rows_all_inserted(
        self, service, mem_session, bank, tmp_path
    ):
        rows = (
            "MC001,Q1?,multiple_choice,,easy,1,,,OpA,OpB,,,,,A,active,,false,true\n"
            "SA001,Q2?,short_answer,,easy,1,,,,,,,,,AnswerX,active,,false,true\n"
            "BL001,Q ________?,blank,,easy,1,,,,,,,,,AnswerY,active,,false,true\n"
        )
        p = _write(tmp_path, rows)
        result = service.preview(p, mem_session)
        assert not result.has_errors

        summary = service.commit(result, bank.id, mem_session)
        mem_session.commit()

        assert summary.inserted == 3
        assert mem_session.query(Question).count() == 3

    def test_commit_flushes_in_batches_without_losing_rows(
        self, mem_session, bank, tmp_path
    ):
        service = ImportService(commit_batch_size=2)
        rows = "".join(
            f"MC{i:03d},Q{i}?,multiple_choice,,easy,1,,,A{i},B{i},,,,,A,active,,false,true\n"
            for i in range(1, 6)
        )
        p = _write(tmp_path, rows)
        result = service.preview(p, mem_session)

        summary = service.commit(result, bank.id, mem_session)
        mem_session.commit()

        assert summary.inserted == 5
        assert mem_session.query(Question).count() == 5


class TestDBDuplicateBlockCommit:

    def test_db_code_duplicate_blocked_but_others_pass(
        self, service, mem_session, bank, tmp_path
    ):
        # Pre-insert question with code "EXIST"
        existing = Question(
            bank_id=bank.id,
            question_code="EXIST",
            question_type="MC",
            content="Pre-existing question",
        )
        mem_session.add(existing)
        mem_session.commit()

        rows = (
            # This should be blocked (code collision)
            "EXIST,Pre-existing question,multiple_choice,,easy,1,,,"
            "A,B,,,,,A,active,,false,true\n"
            # This should succeed
            "NEW001,Brand new?,multiple_choice,,easy,1,,,"
            "A,B,,,,,A,active,,false,true\n"
        )
        p = _write(tmp_path, rows)
        result = service.preview(p, mem_session)

        # has_errors because of DB code duplicate ERROR
        assert result.has_errors

        # Cannot commit when has_errors
        with pytest.raises(ImportValidationError):
            service.commit(result, bank.id, mem_session)
