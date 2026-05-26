"""Quota validation and allocation for multi-exam generation.

This module keeps quota complexity out of UI code. It validates whether
chapter/type/difficulty quota plans are feasible for a candidate pool and
selects questions that satisfy configured quota dimensions simultaneously.
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
    if chapter_sum > plan.total_questions:
        errors.append(
            f"Tổng quota theo Chương ({chapter_sum}) không được lớn hơn số câu mỗi đề ({plan.total_questions})."
        )

    type_sum = sum(plan.type_quota.values())
    if type_sum > plan.total_questions:
        errors.append(
            f"Tổng quota theo Loại ({type_sum}) không được lớn hơn số câu mỗi đề ({plan.total_questions})."
        )

    diff_sum = sum(plan.difficulty_quota.values())
    if diff_sum > plan.total_questions:
        errors.append(
            f"Tổng quota theo Độ khó ({diff_sum}) không được lớn hơn số câu mỗi đề ({plan.total_questions})."
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
    """Allocate one exam question set satisfying configured quotas.

    Quota semantics:
    - Keys present in a quota dict are minimum required counts.
    - Missing keys in a configured axis are unconstrained.
    - Empty quota dict means that whole axis is ignored.

    Returns None when no feasible allocation is found.
    """

    if not questions or plan.total_questions <= 0:
        return None

    excluded_question_ids = excluded_question_ids or set()
    chapter_rem = dict(plan.chapter_quota)
    type_rem = dict(plan.type_quota)
    diff_rem = dict(plan.difficulty_quota)

    pool = [q for q in questions if q.id not in excluded_question_ids]
    random.shuffle(pool)

    if len(pool) < plan.total_questions:
        return None

    selected: list[Question] = []
    used_ids: set[int] = set()
    max_nodes = max(2000, max_attempts * 40)
    nodes = 0

    def _q_meta(q: Question) -> tuple[str, str, str]:
        return (
            chapter_key(q.category),
            q.question_type,
            (q.difficulty or "").strip().lower() or "medium",
        )

    def _remaining_pool() -> list[Question]:
        return [q for q in pool if q.id not in used_ids]

    def _sum_remaining_need(values: dict[str, int]) -> int:
        return sum(v for v in values.values() if v > 0)

    def _has_capacity() -> bool:
        remaining = _remaining_pool()
        remaining_slots = plan.total_questions - len(selected)

        if _sum_remaining_need(chapter_rem) > remaining_slots:
            return False
        if _sum_remaining_need(type_rem) > remaining_slots:
            return False
        if _sum_remaining_need(diff_rem) > remaining_slots:
            return False

        for chap, need in chapter_rem.items():
            if need <= 0:
                continue
            compatible = sum(1 for q in remaining if _q_meta(q)[0] == chap)
            if compatible < need:
                return False

        for qtype, need in type_rem.items():
            if need <= 0:
                continue
            compatible = sum(1 for q in remaining if _q_meta(q)[1] == qtype)
            if compatible < need:
                return False

        for diff, need in diff_rem.items():
            if need <= 0:
                continue
            compatible = sum(1 for q in remaining if _q_meta(q)[2] == diff)
            if compatible < need:
                return False

        return True

    def _candidate_score(q: Question) -> tuple[int, int]:
        chap, qtype, diff = _q_meta(q)
        gain = 0
        if chapter_rem.get(chap, 0) > 0:
            gain += 1
        if type_rem.get(qtype, 0) > 0:
            gain += 1
        if diff_rem.get(diff, 0) > 0:
            gain += 1
        pressure = chapter_rem.get(chap, 0) + type_rem.get(qtype, 0) + diff_rem.get(diff, 0)
        return (-gain, -pressure)

    def _search() -> bool:
        nonlocal nodes
        nodes += 1
        if nodes > max_nodes:
            return False

        if len(selected) == plan.total_questions:
            return (
                all(v == 0 for v in chapter_rem.values())
                and all(v == 0 for v in type_rem.values())
                and all(v == 0 for v in diff_rem.values())
            )

        if not _has_capacity():
            return False

        candidates = [q for q in pool if q.id not in used_ids]
        remaining_slots = plan.total_questions - len(selected)
        if len(candidates) < remaining_slots:
            return False

        candidates.sort(key=_candidate_score)

        for q in candidates:
            chap, qtype, diff = _q_meta(q)
            selected.append(q)
            used_ids.add(q.id)
            prev_chap = chapter_rem.get(chap, 0)
            prev_type = type_rem.get(qtype, 0)
            prev_diff = diff_rem.get(diff, 0)
            if prev_chap > 0:
                chapter_rem[chap] = prev_chap - 1
            if prev_type > 0:
                type_rem[qtype] = prev_type - 1
            if prev_diff > 0:
                diff_rem[diff] = prev_diff - 1

            if _search():
                return True

            chapter_rem[chap] = prev_chap
            type_rem[qtype] = prev_type
            diff_rem[diff] = prev_diff
            used_ids.remove(q.id)
            selected.pop()

        return False

    if _search():
        return list(selected)
    return None


def diagnose_quota_infeasibility(
    questions: list[Question],
    plan: QuotaPlan,
    *,
    excluded_question_ids: set[int] | None = None,
) -> list[str]:
    """Return human-readable reasons when quota dimensions conflict.

    This does not try to prove all infeasibility causes, but surfaces common
    cross-dimension bottlenecks (chapter/type/difficulty intersections).
    """
    excluded_question_ids = excluded_question_ids or set()
    pool = [q for q in questions if q.id not in excluded_question_ids]

    if len(pool) < plan.total_questions:
        return [
            f"Pool hiện tại còn {len(pool)} câu sau khi loại trừ, không đủ {plan.total_questions} câu cho 1 đề."
        ]

    chapter_rem = dict(plan.chapter_quota)
    type_rem = dict(plan.type_quota)
    diff_rem = dict(plan.difficulty_quota)

    def _meta(q: Question) -> tuple[str, str, str]:
        return (
            chapter_key(q.category),
            q.question_type,
            (q.difficulty or "").strip().lower() or "medium",
        )

    reasons: list[str] = []

    chapter_sum = sum(chapter_rem.values())
    if chapter_sum > plan.total_questions:
        reasons.append(
            f"Tổng quota theo Chương ({chapter_sum}) lớn hơn số câu mỗi đề ({plan.total_questions})."
        )
    type_sum = sum(type_rem.values())
    if type_sum > plan.total_questions:
        reasons.append(
            f"Tổng quota theo Loại ({type_sum}) lớn hơn số câu mỗi đề ({plan.total_questions})."
        )
    diff_sum = sum(diff_rem.values())
    if diff_sum > plan.total_questions:
        reasons.append(
            f"Tổng quota theo Độ khó ({diff_sum}) lớn hơn số câu mỗi đề ({plan.total_questions})."
        )

    for chap, need in chapter_rem.items():
        if need <= 0:
            continue
        compatible = sum(1 for q in pool if _meta(q)[0] == chap)
        if compatible < need:
            reasons.append(
                f"Chương '{chap}' cần tối thiểu {need} câu nhưng chỉ có {compatible} câu trong pool."
            )

    for qtype, need in type_rem.items():
        if need <= 0:
            continue
        compatible = sum(1 for q in pool if _meta(q)[1] == qtype)
        if compatible < need:
            reasons.append(
                f"Loại '{qtype}' cần tối thiểu {need} câu nhưng chỉ có {compatible} câu trong pool."
            )

    for diff, need in diff_rem.items():
        if need <= 0:
            continue
        compatible = sum(1 for q in pool if _meta(q)[2] == diff)
        if compatible < need:
            reasons.append(
                f"Độ khó '{diff}' cần tối thiểu {need} câu nhưng chỉ có {compatible} câu trong pool."
            )

    if chapter_rem and type_rem:
        for chap, need in chapter_rem.items():
            if need <= 0:
                continue
            compatible = 0
            for q in pool:
                qchap, qt, _ = _meta(q)
                if qchap == chap and qt in type_rem:
                    compatible += 1
            if compatible < need:
                reasons.append(
                    f"Chương '{chap}' cần {need} câu nhưng chỉ có {compatible} câu giao nhau với các loại đã cấu hình."
                )

    if chapter_rem and diff_rem:
        for chap, need in chapter_rem.items():
            if need <= 0:
                continue
            compatible = 0
            for q in pool:
                qchap, _, qdiff = _meta(q)
                if qchap == chap and qdiff in diff_rem:
                    compatible += 1
            if compatible < need:
                reasons.append(
                    f"Chương '{chap}' cần {need} câu nhưng chỉ có {compatible} câu giao nhau với độ khó đã cấu hình."
                )

    if type_rem and diff_rem:
        for qtype, need in type_rem.items():
            if need <= 0:
                continue
            compatible = 0
            for q in pool:
                _, qt, qdiff = _meta(q)
                if qt == qtype and qdiff in diff_rem:
                    compatible += 1
            if compatible < need:
                reasons.append(
                    f"Loại '{qtype}' cần {need} câu nhưng chỉ có {compatible} câu giao nhau với độ khó đã cấu hình."
                )

    return reasons
