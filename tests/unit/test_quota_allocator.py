from __future__ import annotations

from core.database.models import Question
from modules.quiz_builder.quota_allocator import (
    QuotaPlan,
    allocate_questions_for_plan,
    build_inventory,
    chapter_key,
    validate_quota_plan,
)


def _q(
    qid: int,
    *,
    chapter: str,
    qtype: str,
    difficulty: str,
) -> Question:
    return Question(
        id=qid,
        bank_id=1,
        question_type=qtype,
        content=f"Q{qid}",
        category=chapter,
        difficulty=difficulty,
        is_active=True,
    )


def _sample_questions() -> list[Question]:
    return [
        _q(1, chapter="Chương 1", qtype="MC", difficulty="easy"),
        _q(2, chapter="Chương 1", qtype="MA", difficulty="medium"),
        _q(3, chapter="Chương 2", qtype="BLANK", difficulty="easy"),
        _q(4, chapter="Chương 2", qtype="SA", difficulty="medium"),
        _q(5, chapter="Chương 3", qtype="MC", difficulty="hard"),
        _q(6, chapter="Chương 3", qtype="MA", difficulty="hard"),
    ]


def test_chapter_key_returns_fallback_for_empty() -> None:
    assert chapter_key(None) == "(Chưa gán chương)"
    assert chapter_key("") == "(Chưa gán chương)"


def test_validate_quota_plan_detects_sum_mismatch() -> None:
    questions = _sample_questions()
    inv = build_inventory(questions)

    plan = QuotaPlan(
        total_questions=4,
        chapter_quota={"Chương 1": 1},
        type_quota={"MC": 2, "MA": 2},
        difficulty_quota={"easy": 2, "medium": 2},
    )

    result = validate_quota_plan(plan, inv)
    assert not result.is_valid
    assert any("Tổng quota theo Chương" in msg for msg in result.errors)


def test_validate_quota_plan_detects_overflow() -> None:
    questions = _sample_questions()
    inv = build_inventory(questions)

    plan = QuotaPlan(
        total_questions=4,
        chapter_quota={"Chương 1": 3, "Chương 2": 1},
        type_quota={"MC": 2, "MA": 1, "BLANK": 1},
        difficulty_quota={"easy": 2, "medium": 1, "hard": 1},
    )

    result = validate_quota_plan(plan, inv)
    assert not result.is_valid
    assert "Chương 1" in result.chapter_overflow


def test_allocate_questions_for_plan_success() -> None:
    questions = _sample_questions()
    plan = QuotaPlan(
        total_questions=4,
        chapter_quota={"Chương 1": 2, "Chương 2": 1, "Chương 3": 1},
        type_quota={"MC": 1, "MA": 2, "BLANK": 1},
        difficulty_quota={"easy": 2, "medium": 1, "hard": 1},
    )

    picked = allocate_questions_for_plan(questions, plan, max_attempts=500)
    assert picked is not None
    assert len(picked) == 4


def test_allocate_respects_excluded_ids() -> None:
    questions = _sample_questions()
    plan = QuotaPlan(
        total_questions=2,
        chapter_quota={"Chương 1": 1, "Chương 2": 1},
        type_quota={"MA": 1, "BLANK": 1},
        difficulty_quota={"easy": 1, "medium": 1},
    )

    picked = allocate_questions_for_plan(
        questions,
        plan,
        excluded_question_ids={2},
        max_attempts=300,
    )
    assert picked is None


def test_allocate_no_repeat_two_batches() -> None:
    questions = _sample_questions()
    plan = QuotaPlan(
        total_questions=2,
        chapter_quota={"Chương 3": 2},
        type_quota={"MC": 1, "MA": 1},
        difficulty_quota={"hard": 2},
    )

    first = allocate_questions_for_plan(questions, plan, max_attempts=300)
    assert first is not None
    used = {q.id for q in first}

    second = allocate_questions_for_plan(
        questions,
        plan,
        excluded_question_ids=used,
        max_attempts=300,
    )
    assert second is None
