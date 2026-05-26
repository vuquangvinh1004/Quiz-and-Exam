"""Integration E2E test: import → question bank → quiz creation → attempt → grading.

Covers the full business flow (ARCHITECTURE §6.1 → §6.4):
  1. Import questions via CSV (ImportService)
  2. Verify questions in question bank (QuestionService)
  3. Select questions for a quiz (QuestionSelector)
  4. Create a quiz snapshot (QuizService.create_quiz)
  5. Start an attempt (QuizService.create_attempt)
  6. Save answers
  7. Finalize attempt with grading (QuizService.finalize_attempt)
  8. Verify results in history (HistoryService.list_attempts)

Each integration test is self-contained: uses an isolated in-memory DB.
"""
from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.database.models import Base, QuestionBank
from core.domain.services.history_service import HistoryService
from core.domain.services.import_service import ImportService
from core.domain.services.question_service import QuestionService
from core.domain.services.quiz_service import GradedRow, QuizConfig, QuizService
from core.utils.constants import AttemptStatus, QuizMode
from modules.quiz_builder.selector import QuestionSelector
from modules.quiz_runner.submit_handler import build_graded_result


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FULL_CSV_HEADER = (
    "question_code,question_text,question_type,category,difficulty,score,"
    "hint,explanation,option_a,option_b,option_c,option_d,option_e,option_f,"
    "correct_answers,status,tags,case_sensitive,trim_whitespace"
)


@pytest.fixture
def e2e_session():
    """Isolated in-memory DB session for each E2E test."""
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


def _make_csv_file(rows: list[str]) -> io.StringIO:
    """Build an in-memory CSV with header + rows."""
    content = FULL_CSV_HEADER + "\n" + "\n".join(rows)
    buf = io.StringIO(content)
    buf.name = "test_import.csv"
    return buf


# ---------------------------------------------------------------------------
# Full flow: MC questions
# ---------------------------------------------------------------------------

class TestE2EMultipleChoiceFlow:
    """Complete flow with Multiple Choice questions."""

    MC_ROWS = [
        "MC_E2E_01,Thủ đô Việt Nam là gì?,multiple_choice,Địa lý,easy,1.0,,,Hà Nội,Hồ Chí Minh,Đà Nẵng,Cần Thơ,,,A,active,,false,true",
        "MC_E2E_02,2 + 2 bằng bao nhiêu?,multiple_choice,Toán,easy,1.0,,,3,4,5,6,,,B,active,,false,true",
        "MC_E2E_03,Python là gì?,multiple_choice,IT,medium,1.0,,,Ngôn ngữ lập trình,Hệ điều hành,Database,IDE,,,A,active,,false,true",
    ]

    def test_import_questions(self, e2e_session, tmp_path):
        """Step 1-2: Import questions and verify in bank."""
        bank = QuestionBank(name="E2E Bank MC")
        e2e_session.add(bank)
        e2e_session.flush()

        csv_file = tmp_path / "mc_e2e.csv"
        csv_file.write_text(FULL_CSV_HEADER + "\n" + "\n".join(self.MC_ROWS), encoding="utf-8")

        svc = ImportService()
        preview = svc.preview(csv_file, e2e_session)
        assert preview.error_count == 0
        svc.commit(preview, bank.id, e2e_session)

        qs_svc = QuestionService()
        questions = qs_svc.list_questions(e2e_session, bank_id=bank.id)
        assert len(questions) == 3

    def test_create_quiz_and_attempt(self, e2e_session, tmp_path):
        """Step 3-5: Select questions, create quiz, start attempt."""
        bank = QuestionBank(name="E2E Bank MC2")
        e2e_session.add(bank)
        e2e_session.flush()

        csv_file = tmp_path / "mc2.csv"
        csv_file.write_text(FULL_CSV_HEADER + "\n" + "\n".join(self.MC_ROWS), encoding="utf-8")

        importer = ImportService()
        preview = importer.preview(csv_file, e2e_session)
        importer.commit(preview, bank.id, e2e_session)

        selector = QuestionSelector()
        snapshots = selector.build_snapshots(
            selector.select(e2e_session, bank.id, count=3, shuffle=False),
            shuffle_options=False,
        )
        assert len(snapshots) == 3

        config = QuizConfig(
            title="E2E Quiz MC",
            bank_id=bank.id,
            mode=QuizMode.EXAM.value,
            time_limit_minutes=30,
            question_count=3,
        )
        quiz_svc = QuizService()
        quiz = quiz_svc.create_quiz(e2e_session, config, snapshots)
        assert quiz.id is not None

        attempt = quiz_svc.create_attempt(e2e_session, quiz.id)
        assert attempt.id is not None
        assert attempt.status == AttemptStatus.IN_PROGRESS.value

    def test_save_answers_and_finalize(self, e2e_session, tmp_path):
        """Step 6-7: Answer questions and finalize with grading."""
        bank = QuestionBank(name="E2E Bank MC3")
        e2e_session.add(bank)
        e2e_session.flush()

        csv_file = tmp_path / "mc3.csv"
        csv_file.write_text(FULL_CSV_HEADER + "\n" + "\n".join(self.MC_ROWS), encoding="utf-8")

        importer = ImportService()
        preview = importer.preview(csv_file, e2e_session)
        importer.commit(preview, bank.id, e2e_session)

        selector = QuestionSelector()
        snapshots = selector.build_snapshots(
            selector.select(e2e_session, bank.id, count=3, shuffle=False),
            shuffle_options=False,
        )

        quiz_svc = QuizService()
        quiz = quiz_svc.create_quiz(
            e2e_session,
            QuizConfig(
                title="E2E Finalize",
                bank_id=bank.id,
                mode=QuizMode.EXAM.value,
                time_limit_minutes=30,
                question_count=3,
            ),
            snapshots,
        )
        attempt = quiz_svc.create_attempt(e2e_session, quiz.id)
        qqs = quiz_svc.get_quiz_questions(e2e_session, quiz.id)

        # Grade each answer
        graded_rows = []
        for qq in qqs:
            payload = {"selected": "A"}
            result = QuizService.grade_answer(qq, payload)
            graded_rows.append(
                GradedRow(
                    quiz_question_id=qq.id,
                    answer_payload=payload,
                    is_correct=result.is_correct,
                    score_awarded=result.score_awarded,
                    feedback_state=result.feedback_state,
                )
            )

        finalized = quiz_svc.finalize_attempt(
            e2e_session,
            attempt.id,
            AttemptStatus.SUBMITTED.value,
            graded_rows,
            duration_seconds=120,
        )
        assert finalized.status == AttemptStatus.SUBMITTED.value
        assert finalized.duration_seconds == 120
        assert finalized.max_score == 3.0

    def test_history_after_finalize(self, e2e_session, tmp_path):
        """Step 8: Verify finalized attempt appears in history."""
        bank = QuestionBank(name="E2E Bank MC4")
        e2e_session.add(bank)
        e2e_session.flush()

        csv_file = tmp_path / "mc4.csv"
        csv_file.write_text(FULL_CSV_HEADER + "\n" + "\n".join(self.MC_ROWS), encoding="utf-8")

        importer = ImportService()
        preview = importer.preview(csv_file, e2e_session)
        importer.commit(preview, bank.id, e2e_session)

        selector = QuestionSelector()
        snapshots = selector.build_snapshots(
            selector.select(e2e_session, bank.id, count=3, shuffle=False),
            shuffle_options=False,
        )

        quiz_svc = QuizService()
        quiz = quiz_svc.create_quiz(
            e2e_session,
            QuizConfig(
                title="History Quiz",
                bank_id=bank.id,
                mode=QuizMode.EXAM.value,
                time_limit_minutes=30,
                question_count=3,
            ),
            snapshots,
        )
        attempt = quiz_svc.create_attempt(e2e_session, quiz.id)
        qqs = quiz_svc.get_quiz_questions(e2e_session, quiz.id)
        graded_rows = [
            GradedRow(
                quiz_question_id=qq.id,
                answer_payload={"selected": "A"},
                is_correct=True,
                score_awarded=1.0,
                feedback_state="correct",
            )
            for qq in qqs
        ]
        quiz_svc.finalize_attempt(
            e2e_session,
            attempt.id,
            AttemptStatus.SUBMITTED.value,
            graded_rows,
            duration_seconds=90,
        )

        history = HistoryService.list_attempts(e2e_session)
        assert len(history) == 1
        assert history[0]["quiz_title"] == "History Quiz"
        assert history[0]["status"] == AttemptStatus.SUBMITTED.value


# ---------------------------------------------------------------------------
# Mixed question types flow
# ---------------------------------------------------------------------------

class TestE2EMixedQuestionTypes:
    """E2E with all four question types."""

    MIXED_ROWS = [
        "MX_E2E_01,Python là gì?,multiple_choice,IT,easy,1.0,,,Ngôn ngữ lập trình,Hệ điều hành,DBMS,IDE,,,A,active,,false,true",
        "MX_E2E_02,Ngôn ngữ nào kiểu thông dịch?,multiple_answer,IT,medium,2.0,,,Python,Java,C,JavaScript,,,A||D,active,,false,true",
        "MX_E2E_03,Thủ đô Pháp là ________.,blank,Địa lý,easy,1.0,,,,,,,,,Paris||paris,active,,false,false",
        "MX_E2E_04,Viết tắt của CPU.,short_answer,IT,easy,1.0,,,,,,,,,Central Processing Unit||CPU,active,,false,true",
    ]

    def test_import_four_question_types(self, e2e_session, tmp_path):
        bank = QuestionBank(name="E2E Mixed Bank")
        e2e_session.add(bank)
        e2e_session.flush()

        csv_file = tmp_path / "mixed.csv"
        csv_file.write_text(FULL_CSV_HEADER + "\n" + "\n".join(self.MIXED_ROWS), encoding="utf-8")

        importer = ImportService()
        preview = importer.preview(csv_file, e2e_session)
        assert preview.error_count == 0
        importer.commit(preview, bank.id, e2e_session)

        qs_svc = QuestionService()
        questions = qs_svc.list_questions(e2e_session, bank_id=bank.id)
        types = {q.question_type for q in questions}
        assert "MC" in types
        assert "MA" in types
        assert "BLANK" in types
        assert "SA" in types

    def test_quiz_with_all_types_finalizes(self, e2e_session, tmp_path):
        bank = QuestionBank(name="E2E Mixed Bank2")
        e2e_session.add(bank)
        e2e_session.flush()

        csv_file = tmp_path / "mixed2.csv"
        csv_file.write_text(FULL_CSV_HEADER + "\n" + "\n".join(self.MIXED_ROWS), encoding="utf-8")

        importer = ImportService()
        preview = importer.preview(csv_file, e2e_session)
        importer.commit(preview, bank.id, e2e_session)

        selector = QuestionSelector()
        snapshots = selector.build_snapshots(
            selector.select(e2e_session, bank.id, count=4, shuffle=False),
            shuffle_options=False,
        )

        quiz_svc = QuizService()
        quiz = quiz_svc.create_quiz(
            e2e_session,
            QuizConfig(
                title="Mixed Quiz",
                bank_id=bank.id,
                mode=QuizMode.STUDY.value,
                time_limit_minutes=None,
                question_count=4,
            ),
            snapshots,
        )
        attempt = quiz_svc.create_attempt(e2e_session, quiz.id)
        qqs = quiz_svc.get_quiz_questions(e2e_session, quiz.id)

        graded_rows = []
        for qq in qqs:
            qtype = qq.snapshot_type
            if qtype == "MC":
                payload = {"selected": "A"}
            elif qtype == "MA":
                payload = {"selected": ["A", "D"]}
            elif qtype in ("BLANK", "SA"):
                payload = {"text": "Paris"}
            else:
                payload = {}
            result = QuizService.grade_answer(qq, payload)
            graded_rows.append(
                GradedRow(
                    quiz_question_id=qq.id,
                    answer_payload=payload,
                    is_correct=result.is_correct,
                    score_awarded=result.score_awarded,
                    feedback_state=result.feedback_state,
                )
            )

        finalized = quiz_svc.finalize_attempt(
            e2e_session,
            attempt.id,
            AttemptStatus.COMPLETED.value,
            graded_rows,
            duration_seconds=300,
        )
        assert finalized.status == AttemptStatus.COMPLETED.value
        assert finalized.score >= 0.0


class TestE2EStudyModeFullFlow:
    """Full STUDY-mode flow with typed grading-result assembly."""

    STUDY_ROWS = [
        "ST_E2E_01,2 + 2 bằng bao nhiêu?,multiple_choice,Toán,easy,1.0,,,3,4,5,6,,,B,active,,false,true",
        "ST_E2E_02,Thủ đô Pháp là ________.,blank,Địa lý,easy,1.0,,,,,,,,,Paris||paris,active,,false,true",
    ]

    def test_study_mode_create_attempt_grade_finalize(self, e2e_session, tmp_path):
        bank = QuestionBank(name="E2E Study Bank")
        e2e_session.add(bank)
        e2e_session.flush()

        csv_file = tmp_path / "study_flow.csv"
        csv_file.write_text(
            FULL_CSV_HEADER + "\n" + "\n".join(self.STUDY_ROWS),
            encoding="utf-8",
        )

        importer = ImportService()
        preview = importer.preview(csv_file, e2e_session)
        assert preview.error_count == 0
        importer.commit(preview, bank.id, e2e_session)

        selector = QuestionSelector()
        selected = selector.select(e2e_session, bank.id, count=2, shuffle=False)
        snapshots = selector.build_snapshots(selected, shuffle_options=False)

        quiz_svc = QuizService()
        quiz = quiz_svc.create_quiz(
            e2e_session,
            QuizConfig(
                title="Study Full Flow",
                bank_id=bank.id,
                mode=QuizMode.STUDY.value,
                time_limit_minutes=None,
                question_count=2,
            ),
            snapshots,
        )
        attempt = quiz_svc.create_attempt(e2e_session, quiz.id)
        qqs = quiz_svc.get_quiz_questions(e2e_session, quiz.id)

        runtime_questions = []
        answers: dict[int, dict] = {}
        for qq in qqs:
            cfg = qq.get_snapshot_answer_config()
            runtime_questions.append(
                {
                    "quiz_question_id": qq.id,
                    "order": qq.question_order,
                    "content": qq.snapshot_content or "",
                    "type": qq.snapshot_type,
                    "point_value": qq.snapshot_point_value or 1.0,
                    "options": qq.get_snapshot_options() or [],
                    "accepted_answers": qq.get_snapshot_accepted_answers(),
                    "case_sensitive": cfg.get("case_sensitive", False),
                    "trim_whitespace": cfg.get("trim_whitespace", True),
                    "question_code": None,
                }
            )
            if qq.snapshot_type == "MC":
                answers[qq.id] = {"selected": "B"}
            elif qq.snapshot_type == "BLANK":
                answers[qq.id] = {"text": "Paris"}

        # Use submit_handler hardening path to produce graded_rows + summary.
        from core.domain.services.quiz_service import QuizQuestionSnapshot

        typed_questions = [QuizQuestionSnapshot(**q) for q in runtime_questions]
        graded_rows, result = build_graded_result(
            quiz_questions=typed_questions,
            answers=answers,
            started_at=datetime.now(timezone.utc),
            submitter_name="",
            submitter_id="",
            quiz_title=quiz.title,
            mode=quiz.mode,
        )

        finalized = quiz_svc.finalize_attempt(
            e2e_session,
            attempt.id,
            AttemptStatus.COMPLETED.value,
            graded_rows,
            duration_seconds=result.duration_seconds,
        )

        assert finalized.mode == QuizMode.STUDY.value
        assert finalized.status == AttemptStatus.COMPLETED.value
        assert finalized.correct_count >= 1
        assert finalized.score >= 1.0
