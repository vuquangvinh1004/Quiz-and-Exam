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
    clo: str,
    qtype: str,
    difficulty: str,
) -> Question:
    return Question(
        id=qid,
        bank_id=1,
        question_type=qtype,
        content=f"Q{qid}",
        category=chapter,
        learning_outcome_code=clo,
        difficulty=difficulty,
        is_active=True,
    )


def _sample_questions() -> list[Question]:
    return [
        _q(1, chapter="Chương 1", clo="CLO_A", qtype="MC", difficulty="easy"),
        _q(2, chapter="Chương 1", clo="CLO_A", qtype="MA", difficulty="medium"),
        _q(3, chapter="Chương 2", clo="CLO_B", qtype="BLANK", difficulty="easy"),
        _q(4, chapter="Chương 2", clo="CLO_B", qtype="SA", difficulty="hard"),
        _q(5, chapter="Chương 3", clo="CLO_C", qtype="MC", difficulty="Phân tích"),
        _q(6, chapter="Chương 3", clo="CLO_C", qtype="MA", difficulty="Sáng tạo"),
    ]


def test_chapter_key_returns_fallback_for_empty() -> None:
    assert chapter_key(None) == "(Chưa gán chương)"
    assert chapter_key("") == "(Chưa gán chương)"


def test_build_inventory_groups_by_clo_and_level() -> None:
    inv = build_inventory(_sample_questions())
    assert inv.by_clo[("CLO_A", "Nhớ")] == 1
    assert inv.by_clo[("CLO_A", "Hiểu")] == 1
    assert inv.by_clo[("CLO_B", "Nhớ")] == 1
    assert inv.by_clo[("CLO_B", "Vận dụng")] == 1
    assert inv.by_clo[("CLO_C", "Phân tích")] == 1
    assert inv.by_clo[("CLO_C", "Sáng tạo")] == 1


def test_validate_quota_plan_allows_partial_quota() -> None:
    inv = build_inventory(_sample_questions())
    plan = QuotaPlan(
        total_questions=4,
        chapter_quota={"Chương 1": 1},
        type_quota={},
        clo_quota={},
    )

    result = validate_quota_plan(plan, inv)
    assert result.is_valid


def test_validate_quota_plan_detects_axis_sum_exceeds_total() -> None:
    inv = build_inventory(_sample_questions())
    plan = QuotaPlan(
        total_questions=2,
        chapter_quota={"Chương 1": 2, "Chương 2": 1},
        type_quota={},
        clo_quota={("CLO_A", "Nhớ"): 1},
    )

    result = validate_quota_plan(plan, inv)
    assert not result.is_valid
    assert any("không được lớn hơn" in msg for msg in result.errors)


def test_validate_quota_plan_detects_clo_overflow() -> None:
    inv = build_inventory(_sample_questions())
    plan = QuotaPlan(
        total_questions=4,
        chapter_quota={"Chương 1": 1, "Chương 2": 1},
        type_quota={"MC": 2, "MA": 1, "BLANK": 1},
        clo_quota={
            ("CLO_A", "Nhớ"): 1,
            ("CLO_A", "Hiểu"): 2,
        },
    )

    result = validate_quota_plan(plan, inv)
    assert not result.is_valid
    assert ("CLO_A", "Hiểu") in result.clo_overflow


def test_allocate_questions_for_plan_success() -> None:
    questions = _sample_questions()
    plan = QuotaPlan(
        total_questions=2,
        chapter_quota={"Chương 1": 1, "Chương 2": 1},
        type_quota={"MC": 1, "SA": 1},
        clo_quota={("CLO_A", "Nhớ"): 1, ("CLO_B", "Vận dụng"): 1},
    )

    picked = allocate_questions_for_plan(questions, plan, max_attempts=500)
    assert picked is not None
    assert len(picked) == 2
    picked_ids = {q.id for q in picked}
    assert picked_ids == {1, 4}


def test_allocate_respects_excluded_ids() -> None:
    questions = _sample_questions()
    plan = QuotaPlan(
        total_questions=2,
        chapter_quota={"Chương 1": 1, "Chương 2": 1},
        type_quota={"MC": 1, "SA": 1},
        clo_quota={("CLO_A", "Nhớ"): 1, ("CLO_B", "Vận dụng"): 1},
    )

    picked = allocate_questions_for_plan(
        questions,
        plan,
        excluded_question_ids={1, 4},
        max_attempts=300,
    )
    assert picked is None


def test_allocate_no_repeat_two_batches() -> None:
    questions = _sample_questions()
    plan = QuotaPlan(
        total_questions=2,
        chapter_quota={"Chương 1": 1, "Chương 2": 1},
        type_quota={"MC": 1, "SA": 1},
        clo_quota={("CLO_A", "Nhớ"): 1, ("CLO_B", "Vận dụng"): 1},
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


def test_allocate_with_single_axis_quota_fills_remaining_freely() -> None:
    questions = _sample_questions()
    plan = QuotaPlan(
        total_questions=2,
        chapter_quota={},
        type_quota={"MC": 1},
        clo_quota={("CLO_A", "Nhớ"): 1},
    )

    picked = allocate_questions_for_plan(questions, plan, max_attempts=120)
    assert picked is not None
    assert len(picked) == 2
    assert any(q.question_type == "MC" for q in picked)
    assert any(
        (q.learning_outcome_code or "").strip() == "CLO_A"
        and q.difficulty in {"easy", "Nhớ"}
        for q in picked
    )


def test_allocate_ignores_empty_axes() -> None:
    questions = _sample_questions()
    plan = QuotaPlan(
        total_questions=2,
        chapter_quota={},
        type_quota={},
        clo_quota={("CLO_C", "Sáng tạo"): 1},
    )

    picked = allocate_questions_for_plan(questions, plan, max_attempts=120)
    assert picked is not None
    assert len(picked) == 2
    assert any((q.learning_outcome_code or "", q.difficulty or "") == ("CLO_C", "Sáng tạo") for q in picked)


def test_allocate_finds_feasible_combination_with_multi_axis_quota() -> None:
    questions = [
        _q(1, chapter="Chương 1", clo="CLO_A", qtype="MC", difficulty="medium"),
        _q(2, chapter="Chương 1", clo="CLO_A", qtype="MA", difficulty="hard"),
        _q(3, chapter="Chương 2", clo="CLO_B", qtype="MC", difficulty="hard"),
        _q(4, chapter="Chương 2", clo="CLO_B", qtype="BLANK", difficulty="medium"),
        _q(5, chapter="Chương 2", clo="CLO_B", qtype="BLANK", difficulty="hard"),
    ]
    plan = QuotaPlan(
        total_questions=2,
        chapter_quota={"Chương 1": 1, "Chương 2": 1},
        type_quota={"MC": 1, "BLANK": 1},
        clo_quota={("CLO_A", "Hiểu"): 1, ("CLO_B", "hard"): 1},
    )

    picked = allocate_questions_for_plan(questions, plan, max_attempts=80)
    assert picked is not None
    assert len(picked) == 2
    assert any(q.question_type == "MC" for q in picked)
    assert any(q.question_type == "BLANK" for q in picked)
    assert any(
        (q.learning_outcome_code or "").strip() == "CLO_A"
        and q.difficulty in {"medium", "Hiểu"}
        for q in picked
    )
    assert any(
        (q.learning_outcome_code or "").strip() == "CLO_B"
        and q.difficulty in {"hard", "Vận dụng"}
        for q in picked
    )


def test_diagnose_quota_infeasibility_returns_cross_axis_reason() -> None:
    questions = [
        _q(1, chapter="Chương 1", clo="CLO_A", qtype="MC", difficulty="easy"),
        _q(2, chapter="Chương 2", clo="CLO_B", qtype="BLANK", difficulty="easy"),
        _q(3, chapter="Chương 2", clo="CLO_B", qtype="MA", difficulty="hard"),
    ]
    plan = QuotaPlan(
        total_questions=2,
        chapter_quota={"Chương 1": 1, "Chương 2": 1},
        type_quota={"MC": 1, "BLANK": 1},
        clo_quota={("CLO_A", "Vận dụng"): 1, ("CLO_B", "Vận dụng"): 1},
    )

    reasons = diagnose_quota_infeasibility(questions, plan)
    assert reasons
    assert any("CLO 'CLO_A'" in msg or "giao nhau" in msg for msg in reasons)
