from __future__ import annotations

from core.database.models import Question
from modules.quiz_builder.quota_allocator import (
    QuotaPlan,
    allocate_questions_for_plan,
    build_inventory,
    chapter_key,
    diagnose_quota_infeasibility,
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


def test_validate_quota_plan_allows_partial_quota() -> None:
    questions = _sample_questions()
    inv = build_inventory(questions)

    plan = QuotaPlan(
        total_questions=4,
        chapter_quota={"Chương 1": 1},
        type_quota={},
        difficulty_quota={},
    )

    result = validate_quota_plan(plan, inv)
    assert result.is_valid


def test_validate_quota_plan_detects_axis_sum_exceeds_total() -> None:
    questions = _sample_questions()
    inv = build_inventory(questions)

    plan = QuotaPlan(
        total_questions=2,
        chapter_quota={"Chương 1": 2, "Chương 2": 1},
        type_quota={},
        difficulty_quota={},
    )

    result = validate_quota_plan(plan, inv)
    assert not result.is_valid
    assert any("không được lớn hơn" in msg for msg in result.errors)


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


def test_allocate_respects_exact_type_quota_mc_ma() -> None:
    questions = _sample_questions()
    plan = QuotaPlan(
        total_questions=2,
        chapter_quota={"Chương 1": 2},
        type_quota={"MC": 1, "MA": 1},
        difficulty_quota={"easy": 1, "medium": 1},
    )

    picked = allocate_questions_for_plan(questions, plan, max_attempts=400)
    assert picked is not None
    picked_types = sorted(q.question_type for q in picked)
    assert picked_types == ["MA", "MC"]


def test_allocate_with_single_axis_quota_fills_remaining_freely() -> None:
    questions = _sample_questions()
    plan = QuotaPlan(
        total_questions=2,
        chapter_quota={},
        type_quota={"MC": 1},
        difficulty_quota={},
    )

    picked = allocate_questions_for_plan(questions, plan, max_attempts=120)
    assert picked is not None
    assert len(picked) == 2
    assert sum(1 for q in picked if q.question_type == "MC") >= 1


def test_allocate_ignores_empty_axes() -> None:
    questions = _sample_questions()
    plan = QuotaPlan(
        total_questions=2,
        chapter_quota={},
        type_quota={},
        difficulty_quota={"hard": 1},
    )

    picked = allocate_questions_for_plan(questions, plan, max_attempts=120)
    assert picked is not None
    assert len(picked) == 2
    assert sum(1 for q in picked if (q.difficulty or "").lower() == "hard") >= 1


def test_allocate_finds_feasible_combination_with_multi_axis_quota() -> None:
    questions = [
        _q(1, chapter="Chương 1", qtype="MC", difficulty="medium"),
        _q(2, chapter="Chương 1", qtype="MA", difficulty="hard"),
        _q(3, chapter="Chương 2", qtype="MC", difficulty="hard"),
        _q(4, chapter="Chương 2", qtype="BLANK", difficulty="medium"),
        _q(5, chapter="Chương 2", qtype="BLANK", difficulty="hard"),
    ]
    plan = QuotaPlan(
        total_questions=2,
        chapter_quota={"Chương 1": 1, "Chương 2": 1},
        type_quota={"MC": 1, "BLANK": 1},
        difficulty_quota={"medium": 1, "hard": 1},
    )

    picked = allocate_questions_for_plan(questions, plan, max_attempts=80)
    assert picked is not None
    assert len(picked) == 2
    picked_ids = {q.id for q in picked}
    assert picked_ids == {1, 5}


def test_diagnose_quota_infeasibility_returns_cross_axis_reason() -> None:
    questions = [
        _q(1, chapter="Chương 1", qtype="MC", difficulty="easy"),
        _q(2, chapter="Chương 2", qtype="BLANK", difficulty="easy"),
        _q(3, chapter="Chương 2", qtype="MA", difficulty="hard"),
    ]
    plan = QuotaPlan(
        total_questions=2,
        chapter_quota={"Chương 1": 1, "Chương 2": 1},
        type_quota={"MC": 1, "BLANK": 1},
        difficulty_quota={"medium": 1, "hard": 1},
    )

    reasons = diagnose_quota_infeasibility(questions, plan)
    assert reasons
    assert any("Độ khó 'medium'" in msg or "giao nhau" in msg for msg in reasons)
