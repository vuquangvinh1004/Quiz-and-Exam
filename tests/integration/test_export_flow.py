"""Integration test: full Word-export pipeline.

Flow tested:
    1. Seed an in-memory SQLite DB with questions of all four types.
    2. Use QuestionSelector.select() to retrieve them.
    3. Use QuestionSelector.build_snapshots() to convert to snapshot dicts.
    4. Use WordRenderer.render() to produce a docx.Document.
    5. Save the document to a temp file.
    6. Verify the saved .docx is a valid, non-empty Word file.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from sqlalchemy.orm import sessionmaker

from core.database.models import Question, QuestionBank, QuestionOption
from modules.quiz_builder.selector import QuestionSelector
from modules.quiz_exporter.word_renderer import ExamMeta, ExportConfig, WordRenderer


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mem_session(in_memory_engine):
    factory = sessionmaker(bind=in_memory_engine, autoflush=False, autocommit=False)
    session = factory()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def bank(mem_session):
    b = QuestionBank(name="ExportTestBank")
    mem_session.add(b)
    mem_session.flush()
    return b


def _add_mc(session, bank_id: int, content: str = "MC question?") -> Question:
    q = Question(
        bank_id=bank_id,
        content=content,
        question_type="MC",
        difficulty="easy",
        point_value=1.0,
        is_active=True,
    )
    session.add(q)
    session.flush()
    for idx, (key, text, correct) in enumerate(
        [("A", "Opt A", True), ("B", "Opt B", False), ("C", "Opt C", False)]
    ):
        session.add(QuestionOption(
            question_id=q.id, option_key=key,
            option_text=text, is_correct=correct, sort_order=idx
        ))
    session.flush()
    return q


def _add_ma(session, bank_id: int) -> Question:
    q = Question(
        bank_id=bank_id,
        content="MA question?",
        question_type="MA",
        difficulty="medium",
        point_value=2.0,
        is_active=True,
    )
    session.add(q)
    session.flush()
    for idx, (key, text, correct) in enumerate(
        [("A", "Opt A", True), ("B", "Opt B", True), ("C", "Opt C", False)]
    ):
        session.add(QuestionOption(
            question_id=q.id, option_key=key,
            option_text=text, is_correct=correct, sort_order=idx
        ))
    session.flush()
    return q


def _add_blank(session, bank_id: int) -> Question:
    import json
    q = Question(
        bank_id=bank_id,
        content="Fill in: ___ is the capital of Vietnam.",
        question_type="BLANK",
        difficulty="easy",
        point_value=1.5,
        is_active=True,
        accepted_answers=json.dumps(["Hà Nội", "Ha Noi"]),
        case_sensitive=False,
        trim_whitespace=True,
    )
    session.add(q)
    session.flush()
    return q


def _add_sa(session, bank_id: int) -> Question:
    import json
    q = Question(
        bank_id=bank_id,
        content="Explain gravity briefly.",
        question_type="SA",
        difficulty="hard",
        point_value=3.0,
        is_active=True,
        accepted_answers=json.dumps(["gravitational force"]),
        case_sensitive=False,
        trim_whitespace=True,
    )
    session.add(q)
    session.flush()
    return q


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestExportFlow:
    def test_full_pipeline_all_types(self, mem_session, bank):
        """Full flow: seed DB → select → snapshots → render → save."""
        _add_mc(mem_session, bank.id)
        _add_ma(mem_session, bank.id)
        _add_blank(mem_session, bank.id)
        _add_sa(mem_session, bank.id)
        mem_session.flush()

        selector = QuestionSelector()
        questions_orm = selector.select(
            mem_session,
            bank.id,
            count=4,
            question_types=["MC", "MA", "BLANK", "SA"],
            active_only=True,
            shuffle=False,
        )
        assert len(questions_orm) == 4

        snapshots = selector.build_snapshots(questions_orm, shuffle_options=False)
        assert len(snapshots) == 4
        types_in_snaps = {s["type"] for s in snapshots}
        assert types_in_snaps == {"MC", "MA", "BLANK", "SA"}

        meta = ExamMeta(
            school="Test University",
            subject="Integration Testing",
            exam_title="Full Export Test",
            duration_minutes=30,
        )
        config = ExportConfig(
            show_instructions=True,
            show_answer_sheet=True,
            show_scoring_rules=True,
            show_answer_key=True,
            numbering_mode="global",
            group_by_type=True,
        )
        doc = WordRenderer().render(snapshots, meta, config)

        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            doc.save(str(tmp_path))
            assert tmp_path.exists()
            assert tmp_path.stat().st_size > 1024  # at least 1 KB — real content
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_mc_only_export(self, mem_session, bank):
        """Export with only MC questions should produce a valid docx."""
        for i in range(3):
            _add_mc(mem_session, bank.id, content=f"MC question {i+1}?")
        mem_session.flush()

        selector = QuestionSelector()
        orm_qs = selector.select(mem_session, bank.id, count=3, shuffle=False)
        snaps = selector.build_snapshots(orm_qs, shuffle_options=False)

        meta = ExamMeta(exam_title="MC Only Exam")
        config = ExportConfig()
        doc = WordRenderer().render(snaps, meta, config)

        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            doc.save(str(tmp_path))
            assert tmp_path.stat().st_size > 0
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_snapshot_mc_options_structure(self, mem_session, bank):
        """Snapshots from the DB must have the options list in correct format."""
        _add_mc(mem_session, bank.id)
        mem_session.flush()

        selector = QuestionSelector()
        orm_qs = selector.select(mem_session, bank.id, count=1, shuffle=False)
        snaps = selector.build_snapshots(orm_qs, shuffle_options=False)

        snap = snaps[0]
        assert snap["type"] == "MC"
        assert len(snap["options"]) == 3
        keys = {o["key"] for o in snap["options"]}
        assert keys == {"A", "B", "C"}
        correct = [o for o in snap["options"] if o["is_correct"]]
        assert len(correct) == 1
        assert correct[0]["key"] == "A"

    def test_snapshot_blank_accepted_answers(self, mem_session, bank):
        """BLANK snapshots must carry accepted_answers list."""
        _add_blank(mem_session, bank.id)
        mem_session.flush()

        selector = QuestionSelector()
        orm_qs = selector.select(mem_session, bank.id, count=1, shuffle=False)
        snaps = selector.build_snapshots(orm_qs, shuffle_options=False)

        snap = snaps[0]
        assert snap["type"] == "BLANK"
        assert "Hà Nội" in snap["accepted_answers"] or "Ha Noi" in snap["accepted_answers"]

    def test_export_with_minimal_config(self, mem_session, bank):
        """All optional sections disabled — export should still succeed."""
        _add_mc(mem_session, bank.id)
        mem_session.flush()

        selector = QuestionSelector()
        orm_qs = selector.select(mem_session, bank.id, count=1, shuffle=False)
        snaps = selector.build_snapshots(orm_qs, shuffle_options=False)

        meta = ExamMeta(exam_title="Minimal")
        config = ExportConfig(
            show_instructions=False,
            show_answer_sheet=False,
            show_scoring_rules=False,
            show_answer_key=False,
        )
        doc = WordRenderer().render(snaps, meta, config)

        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            doc.save(str(tmp_path))
            assert tmp_path.stat().st_size > 0
        finally:
            tmp_path.unlink(missing_ok=True)
