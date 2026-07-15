"""Question selector for quiz builder.

Selects a randomized (or ordered) subset of questions from a bank, applying
optional filters, then builds the snapshot payload that QuizService stores as
quiz_questions rows.

No UI logic here – pure data-layer operations.
"""
from __future__ import annotations

import random
from typing import Optional

from sqlalchemy.orm import Session

from core.database.models import Question
from core.domain.services.quiz_service import QuizCreationSnapshot

_DIFFICULTY_FILTER_MAP = {
    "Nhớ": ("Nhớ", "easy"),
    "Hiểu": ("Hiểu", "medium"),
    "Vận dụng": ("Vận dụng", "hard"),
    "Phân tích": ("Phân tích",),
    "Đánh giá": ("Đánh giá",),
    "Sáng tạo": ("Sáng tạo",),
}


def _expand_difficulties(difficulties: list[str]) -> list[str]:
    expanded: list[str] = []
    for diff in difficulties:
        expanded.extend(_DIFFICULTY_FILTER_MAP.get(diff, (diff,)))
    return expanded


class QuestionSelector:
    """Selects and prepares questions for a quiz snapshot."""

    # -----------------------------------------------------------------------
    # Selection
    # -----------------------------------------------------------------------

    def select(
        self,
        session: Session,
        bank_id: int,
        count: int,
        question_types: Optional[list[str]] = None,
        difficulties: Optional[list[str]] = None,
        chapters: Optional[list[str]] = None,
        candidate_question_ids: Optional[list[int]] = None,
        active_only: bool = True,
        shuffle: bool = True,
    ) -> list[Question]:
        """Return up to *count* questions matching the given filters.

        If *shuffle* is True, the subset is randomised; otherwise questions
        are returned in ascending id order, first-in first-out.
        """
        q = session.query(Question).filter(Question.bank_id == bank_id)
        if active_only:
            q = q.filter(Question.is_active.is_(True))
        if question_types:
            q = q.filter(Question.question_type.in_(question_types))
        if difficulties:
            q = q.filter(Question.difficulty.in_(_expand_difficulties(difficulties)))
        if chapters:
            q = q.filter(Question.category.in_(chapters))
        if candidate_question_ids:
            q = q.filter(Question.id.in_(candidate_question_ids))
        questions = q.order_by(Question.id).all()
        if shuffle:
            random.shuffle(questions)
        return questions[:count]

    def available_count(
        self,
        session: Session,
        bank_id: int,
        question_types: Optional[list[str]] = None,
        difficulties: Optional[list[str]] = None,
        chapters: Optional[list[str]] = None,
        candidate_question_ids: Optional[list[int]] = None,
        active_only: bool = True,
    ) -> int:
        """Return how many questions match the given filters."""
        q = session.query(Question).filter(Question.bank_id == bank_id)
        if active_only:
            q = q.filter(Question.is_active.is_(True))
        if question_types:
            q = q.filter(Question.question_type.in_(question_types))
        if difficulties:
            q = q.filter(Question.difficulty.in_(_expand_difficulties(difficulties)))
        if chapters:
            q = q.filter(Question.category.in_(chapters))
        if candidate_question_ids:
            q = q.filter(Question.id.in_(candidate_question_ids))
        return q.count()

    # -----------------------------------------------------------------------
    # Snapshot building
    # -----------------------------------------------------------------------

    def build_snapshots(
        self,
        questions: list[Question],
        shuffle_options: bool = True,
    ) -> list[dict]:
        """Convert ORM Question objects into snapshot dicts for QuizService.

        The returned dicts contain all fields needed to:
          1. Persist the snapshot in quiz_questions (via QuizService.create_quiz)
          2. Grade answers (via QuizService.grade_answer_from_dict) without
             querying the live Question or QuestionOption tables again.
        """
        result: list[dict] = []
        for q in questions:
            snap: dict = {
                "question_id": q.id,
                "content": q.content,
                "type": q.question_type,
                "hint": q.hint or "",
                "explanation": q.explanation or "",
                "point_value": q.point_value or 1.0,
                "difficulty": q.difficulty or "",
                "learning_outcome_code": q.learning_outcome_code or "",
                "category": q.category or "",
                # Matching config for BLANK/SA
                "case_sensitive": q.case_sensitive,
                "trim_whitespace": q.trim_whitespace,
            }
            if q.question_type in ("MC", "MA", "TF"):
                opts = [
                    {
                        "key": o.option_key,
                        "text": o.option_text,
                        "is_correct": o.is_correct,
                    }
                    for o in q.options
                ]
                if shuffle_options:
                    random.shuffle(opts)
                    self._relabel_option_keys(opts)
                snap["options"] = opts
                snap["accepted_answers"] = []
            else:
                snap["options"] = []
                snap["accepted_answers"] = q.get_accepted_answers()
                if q.is_crq_question():
                    subtype = q.get_crq_subtype() or "essay"
                    snap["question_family"] = "CRQ"
                    snap["crq_subtype"] = subtype
                    snap["question_variant"] = subtype
                    snap["crq_rubric"] = q.get_crq_rubric()
                    snap["problem_rubric"] = q.get_crq_rubric()
                    template_name = q.get_crq_template_name()
                    if template_name:
                        snap["crq_template_name"] = template_name
                        snap["problem_template_name"] = template_name
                    template_id = q.get_crq_template_id()
                    if template_id is not None:
                        snap["crq_template_id"] = template_id
                        snap["problem_template_id"] = template_id
            result.append(snap)
        return result

    @staticmethod
    def _relabel_option_keys(options: list[dict]) -> None:
        """Normalize option labels to A/B/C... after shuffling display order."""
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        for i, opt in enumerate(options):
            if i < len(alphabet):
                opt["key"] = alphabet[i]
            else:
                # Defensive fallback for unusually long option lists.
                opt["key"] = f"A{i + 1}"

    def build_creation_snapshots(
        self,
        questions: list[Question],
        shuffle_options: bool = True,
    ) -> list[QuizCreationSnapshot]:
        """Typed variant of build_snapshots for create_quiz contract hardening."""
        raw = self.build_snapshots(questions, shuffle_options=shuffle_options)
        return [QuizCreationSnapshot.from_dict(s) for s in raw]
