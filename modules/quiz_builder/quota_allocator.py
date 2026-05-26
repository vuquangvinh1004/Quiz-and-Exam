"""Quota validation and allocation for multi-exam generation.

This module keeps quota complexity out of UI code. It validates whether
chapter/type/difficulty quota plans are feasible for a candidate pool and
selects questions that satisfy all three quota dimensions simultaneously.
"""
from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Optional

from core.database.models import Question

_UNCATEGORIZED_CHAPTER = "(Chưa gán chương)"


@dataclass(frozen=True)
class QuotaPlan:
    """Requested quota for one exam."""

    total_questions: int
    chapter_quota: dict[str, int]
    type_quota: dict[str, int]
    difficulty_quota: dict[str, int]


@dataclass(frozen=True)
class Inventory:
    """Available counts in a candidate question pool."""

    total: int
    by_chapter: dict[str, int]
    by_type: dict[str, int]
    by_difficulty: dict[str, int]


@dataclass(frozen=True)
class QuotaValidationResult:
    """Validation outcome for one quota plan against an inventory."""

    is_valid: bool
    errors: list[str]
    chapter_overflow: set[str]
    type_overflow: set[str]
    difficulty_overflow: set[str]


def chapter_key(value: Optional[str]) -> str:
    text = (value or "").strip()
    return text or _UNCATEGORIZED_CHAPTER


def build_inventory(questions: list[Question]) -> Inventory:
    by_chapter: dict[str, int] = {}
    by_type: dict[str, int] = {}
    by_difficulty: dict[str, int] = {}

    for q in questions:
        chap = chapter_key(q.category)
        by_chapter[chap] = by_chapter.get(chap, 0) + 1

        qtype = q.question_type
        by_type[qtype] = by_type.get(qtype, 0) + 1

        diff = (q.difficulty or "").strip().lower() or "medium"
        by_difficulty[diff] = by_difficulty.get(diff, 0) + 1

    return Inventory(
        total=len(questions),
        by_chapter=by_chapter,
        by_type=by_type,
        by_difficulty=by_difficulty,
    )


def validate_quota_plan(plan: QuotaPlan, inventory: Inventory) -> QuotaValidationResult:
    errors: list[str] = []
    chapter_overflow: set[str] = set()
    type_overflow: set[str] = set()
    difficulty_overflow: set[str] = set()

    if plan.total_questions <= 0:
        errors.append("Số câu mỗi đề phải lớn hơn 0.")

    if inventory.total < plan.total_questions:
        errors.append(
            f"Nguồn câu hỏi hiện tại chỉ có {inventory.total} câu, không đủ {plan.total_questions} câu cho mỗi đề."
        )

    chapter_sum = sum(plan.chapter_quota.values())
    if chapter_sum != plan.total_questions:
        errors.append(
            f"Tổng quota theo Chương ({chapter_sum}) phải bằng số câu mỗi đề ({plan.total_questions})."
        )

    type_sum = sum(plan.type_quota.values())
    if type_sum != plan.total_questions:
        errors.append(
            f"Tổng quota theo Loại ({type_sum}) phải bằng số câu mỗi đề ({plan.total_questions})."
        )

    diff_sum = sum(plan.difficulty_quota.values())
    if diff_sum != plan.total_questions:
        errors.append(
            f"Tổng quota theo Độ khó ({diff_sum}) phải bằng số câu mỗi đề ({plan.total_questions})."
        )

    for chap, requested in plan.chapter_quota.items():
        if requested > inventory.by_chapter.get(chap, 0):
            chapter_overflow.add(chap)
            errors.append(
                f"Chương '{chap}' yêu cầu {requested} câu, nhưng chỉ có {inventory.by_chapter.get(chap, 0)} câu."
            )

    for qtype, requested in plan.type_quota.items():
        if requested > inventory.by_type.get(qtype, 0):
            type_overflow.add(qtype)
            errors.append(
                f"Loại '{qtype}' yêu cầu {requested} câu, nhưng chỉ có {inventory.by_type.get(qtype, 0)} câu."
            )

    for diff, requested in plan.difficulty_quota.items():
        if requested > inventory.by_difficulty.get(diff, 0):
            difficulty_overflow.add(diff)
            errors.append(
                f"Độ khó '{diff}' yêu cầu {requested} câu, nhưng chỉ có {inventory.by_difficulty.get(diff, 0)} câu."
            )

    return QuotaValidationResult(
        is_valid=not errors,
        errors=errors,
        chapter_overflow=chapter_overflow,
        type_overflow=type_overflow,
        difficulty_overflow=difficulty_overflow,
    )


def allocate_questions_for_plan(
    questions: list[Question],
    plan: QuotaPlan,
    *,
    excluded_question_ids: set[int] | None = None,
    max_attempts: int = 300,
) -> list[Question] | None:
    """Allocate one exam question set satisfying chapter/type/difficulty quotas.

    Uses randomized greedy retries to balance practicality and simplicity.
    Returns None when no feasible allocation is found within max_attempts.
    """

    if not questions or plan.total_questions <= 0:
        return None

    excluded_question_ids = excluded_question_ids or set()

    for _ in range(max_attempts):
        chapter_rem = dict(plan.chapter_quota)
        type_rem = dict(plan.type_quota)
        diff_rem = dict(plan.difficulty_quota)

        pool = questions[:]
        random.shuffle(pool)

        selected: list[Question] = []
        used_ids: set[int] = set()

        while len(selected) < plan.total_questions:
            best_q: Question | None = None
            best_score = -1.0

            for q in pool:
                if q.id in excluded_question_ids:
                    continue
                if q.id in used_ids:
                    continue
                chap = chapter_key(q.category)
                qtype = q.question_type
                diff = (q.difficulty or "").strip().lower() or "medium"

                if chapter_rem.get(chap, 0) <= 0:
                    continue
                if type_rem.get(qtype, 0) <= 0:
                    continue
                if diff_rem.get(diff, 0) <= 0:
                    continue

                # Prioritize the most constrained remaining buckets.
                score = (
                    (chapter_rem.get(chap, 0) * 1.3)
                    + (type_rem.get(qtype, 0) * 1.1)
                    + (diff_rem.get(diff, 0) * 1.0)
                )
                if score > best_score:
                    best_score = score
                    best_q = q

            if best_q is None:
                break

            selected.append(best_q)
            used_ids.add(best_q.id)

            chap = chapter_key(best_q.category)
            qtype = best_q.question_type
            diff = (best_q.difficulty or "").strip().lower() or "medium"
            chapter_rem[chap] -= 1
            type_rem[qtype] -= 1
            diff_rem[diff] -= 1

        if len(selected) != plan.total_questions:
            continue

        if any(v != 0 for v in chapter_rem.values()):
            continue
        if any(v != 0 for v in type_rem.values()):
            continue
        if any(v != 0 for v in diff_rem.values()):
            continue

        return selected

    return None
