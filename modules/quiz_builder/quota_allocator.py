"""Quota validation and allocation for multi-exam generation.

This module keeps quota complexity out of UI code. It validates whether
chapter/CLO quota plans are feasible for a candidate pool and selects
questions that satisfy configured quota dimensions simultaneously.
"""
from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Optional

from core.database.models import Question

_UNCATEGORIZED_CHAPTER = "(Chưa gán chương)"
_DIFFICULTY_CANONICAL_MAP = {
    "easy": "Nhớ",
    "medium": "Hiểu",
    "hard": "Vận dụng",
}
_DIFFICULTY_LEVEL_ORDER = (
    "Nhớ",
    "Hiểu",
    "Vận dụng",
    "Phân tích",
    "Đánh giá",
    "Sáng tạo",
)


@dataclass(frozen=True)
class QuotaPlan:
    """Requested quota for one exam."""

    total_questions: int
    chapter_quota: dict[str, int]
    type_quota: dict[str, int]
    clo_quota: dict[tuple[str, str], int]


@dataclass(frozen=True)
class Inventory:
    """Available counts in a candidate question pool."""

    total: int
    by_chapter: dict[str, int]
    by_type: dict[str, int]
    by_clo: dict[tuple[str, str], int]


@dataclass(frozen=True)
class QuotaValidationResult:
    """Validation outcome for one quota plan against an inventory."""

    is_valid: bool
    errors: list[str]
    chapter_overflow: set[str]
    type_overflow: set[str]
    clo_overflow: set[tuple[str, str]]


def chapter_key(value: Optional[str]) -> str:
    text = (value or "").strip()
    return text or _UNCATEGORIZED_CHAPTER


def _canonical_difficulty(value: str | None) -> str:
    raw = (value or "").strip()
    if not raw:
        return "Hiểu"
    return _DIFFICULTY_CANONICAL_MAP.get(raw.lower(), raw)


def _canonical_clo_key(key: tuple[str, str] | str) -> tuple[str, str]:
    if isinstance(key, tuple) and len(key) == 2:
        clo, diff = key
        return (str(clo).strip() or "(Chưa gắn CLO)", _canonical_difficulty(str(diff)))
    raw = str(key).strip()
    if not raw:
        return ("(Chưa gắn CLO)", "Hiểu")
    if "||" in raw:
        clo, diff = raw.split("||", 1)
        return (clo.strip() or "(Chưa gắn CLO)", _canonical_difficulty(diff))
    return (raw, "Hiểu")


def _canonical_clo_quota(quota: dict[tuple[str, str] | str, int]) -> dict[tuple[str, str], int]:
    result: dict[tuple[str, str], int] = {}
    for key, value in quota.items():
        canon = _canonical_clo_key(key)
        result[canon] = result.get(canon, 0) + value
    return result


def build_inventory(questions: list[Question]) -> Inventory:
    by_chapter: dict[str, int] = {}
    by_type: dict[str, int] = {}
    by_clo: dict[tuple[str, str], int] = {}

    for q in questions:
        chap = chapter_key(q.category)
        by_chapter[chap] = by_chapter.get(chap, 0) + 1

        qtype = q.question_type
        by_type[qtype] = by_type.get(qtype, 0) + 1

        diff = _canonical_difficulty(q.difficulty)
        clo = (q.learning_outcome_code or "").strip() or "(Chưa gắn CLO)"
        key = (clo, diff)
        by_clo[key] = by_clo.get(key, 0) + 1

    return Inventory(
        total=len(questions),
        by_chapter=by_chapter,
        by_type=by_type,
        by_clo=by_clo,
    )


def validate_quota_plan(plan: QuotaPlan, inventory: Inventory) -> QuotaValidationResult:
    errors: list[str] = []
    chapter_overflow: set[str] = set()
    type_overflow: set[str] = set()
    clo_overflow: set[tuple[str, str]] = set()
    clo_quota = _canonical_clo_quota(plan.clo_quota)

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

    clo_sum = sum(clo_quota.values())
    if clo_sum > plan.total_questions:
        errors.append(
            f"Tổng quota theo CLO ({clo_sum}) không được lớn hơn số câu mỗi đề ({plan.total_questions})."
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

    for clo, requested in clo_quota.items():
        if requested > inventory.by_clo.get(clo, 0):
            clo_overflow.add(clo)
            errors.append(
                f"CLO '{clo[0]}' / mức độ '{clo[1]}' yêu cầu {requested} câu, nhưng chỉ có {inventory.by_clo.get(clo, 0)} câu."
            )

    return QuotaValidationResult(
        is_valid=not errors,
        errors=errors,
        chapter_overflow=chapter_overflow,
        type_overflow=type_overflow,
        clo_overflow=clo_overflow,
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
    clo_rem = _canonical_clo_quota(plan.clo_quota)

    pool = [q for q in questions if q.id not in excluded_question_ids]
    random.shuffle(pool)

    if len(pool) < plan.total_questions:
        return None

    selected: list[Question] = []
    used_ids: set[int] = set()
    max_nodes = max(2000, max_attempts * 40)
    nodes = 0

    def _q_meta(q: Question) -> tuple[str, str, tuple[str, str]]:
        return (
            chapter_key(q.category),
            q.question_type,
            ((q.learning_outcome_code or "").strip() or "(Chưa gắn CLO)", _canonical_difficulty(q.difficulty)),
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
        if _sum_remaining_need(clo_rem) > remaining_slots:
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

        for clo, need in clo_rem.items():
            if need <= 0:
                continue
            compatible = sum(1 for q in remaining if _q_meta(q)[2] == clo)
            if compatible < need:
                return False

        return True

    def _candidate_score(q: Question) -> tuple[int, int]:
        chap, qtype, clo = _q_meta(q)
        gain = 0
        if chapter_rem.get(chap, 0) > 0:
            gain += 1
        if type_rem.get(qtype, 0) > 0:
            gain += 1
        if clo_rem.get(clo, 0) > 0:
            gain += 1
        pressure = chapter_rem.get(chap, 0) + type_rem.get(qtype, 0) + clo_rem.get(clo, 0)
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
                and all(v == 0 for v in clo_rem.values())
            )

        if not _has_capacity():
            return False

        candidates = [q for q in pool if q.id not in used_ids]
        remaining_slots = plan.total_questions - len(selected)
        if len(candidates) < remaining_slots:
            return False

        candidates.sort(key=_candidate_score)

        for q in candidates:
            chap, qtype, clo = _q_meta(q)
            selected.append(q)
            used_ids.add(q.id)
            prev_chap = chapter_rem.get(chap, 0)
            if prev_chap > 0:
                chapter_rem[chap] = prev_chap - 1
            prev_type = type_rem.get(qtype, 0)
            if prev_type > 0:
                type_rem[qtype] = prev_type - 1
            prev_clo = clo_rem.get(clo, 0)
            if prev_clo > 0:
                clo_rem[clo] = prev_clo - 1

            if _search():
                return True

            chapter_rem[chap] = prev_chap
            type_rem[qtype] = prev_type
            clo_rem[clo] = prev_clo
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
    cross-dimension bottlenecks (chapter/CLO intersections).
    """
    excluded_question_ids = excluded_question_ids or set()
    pool = [q for q in questions if q.id not in excluded_question_ids]

    if len(pool) < plan.total_questions:
        return [
            f"Pool hiện tại còn {len(pool)} câu sau khi loại trừ, không đủ {plan.total_questions} câu cho 1 đề."
        ]

    chapter_rem = dict(plan.chapter_quota)
    type_rem = dict(plan.type_quota)
    clo_rem = _canonical_clo_quota(plan.clo_quota)

    def _meta(q: Question) -> tuple[str, str, tuple[str, str]]:
        return (
            chapter_key(q.category),
            q.question_type,
            ((q.learning_outcome_code or "").strip() or "(Chưa gắn CLO)", _canonical_difficulty(q.difficulty)),
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
    clo_sum = sum(clo_rem.values())
    if clo_sum > plan.total_questions:
        reasons.append(
            f"Tổng quota theo CLO ({clo_sum}) lớn hơn số câu mỗi đề ({plan.total_questions})."
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

    for clo, need in clo_rem.items():
        if need <= 0:
            continue
        compatible = sum(1 for q in pool if _meta(q)[2] == clo)
        if compatible < need:
            reasons.append(
                f"CLO '{clo[0]}' / mức độ '{clo[1]}' cần tối thiểu {need} câu nhưng chỉ có {compatible} câu trong pool."
            )

    if chapter_rem and type_rem:
        for chap, need in chapter_rem.items():
            if need <= 0:
                continue
            compatible = 0
            for q in pool:
                qchap, qtype, _ = _meta(q)
                if qchap == chap and qtype in type_rem:
                    compatible += 1
            if compatible < need:
                reasons.append(
                    f"Chương '{chap}' cần {need} câu nhưng chỉ có {compatible} câu giao nhau với các loại đã cấu hình."
                )

    if chapter_rem and clo_rem:
        for chap, need in chapter_rem.items():
            if need <= 0:
                continue
            compatible = 0
            for q in pool:
                qchap, _, qclo = _meta(q)
                if qchap == chap and qclo in clo_rem:
                    compatible += 1
            if compatible < need:
                reasons.append(
                    f"Chương '{chap}' cần {need} câu nhưng chỉ có {compatible} câu giao nhau với các CLO đã cấu hình."
                )

    return reasons
