"""CRUD and search service for questions and question banks.

All database writes go through this service so the UI layer stays clean.
Business rules enforced here:
  - A bank name must be non-empty and unique.
  - A question must belong to an existing bank.
  - Deleting a bank cascades to its questions (handled by FK ondelete=CASCADE).
  - Search/filter is case-insensitive.
"""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session

from core.database.models import (
    AttemptAnswer,
    Question,
    QuestionBank,
    QuestionOption,
    QuizQuestion,
)
from core.utils.constants import (
    BLANK_PLACEHOLDER,
    DEFAULT_DIFFICULTY,
    DEFAULT_SCORE,
    DEFAULT_STATUS,
    QuestionType,
)
from core.utils.validators import count_blank_placeholders


# ---------------------------------------------------------------------------
# Data transfer objects
# ---------------------------------------------------------------------------

@dataclass
class BankStats:
    bank_id: int
    bank_name: str
    question_count: int


@dataclass
class BankOverviewRow:
    bank_id: int
    bank_name: str
    assessment_type: str
    course_learning_outcomes: list[dict[str, str]]
    question_count: int


@dataclass
class QuestionEditData:
    """DTO used to create or update a question via the editor dialog."""
    bank_id: int
    question_type: QuestionType
    content: str
    difficulty: str = field(default_factory=lambda: DEFAULT_DIFFICULTY.value)
    score: float = DEFAULT_SCORE
    hint: str = ""
    explanation: str = ""
    learning_outcome_code: str = ""
    category: str = ""
    tags: str = ""
    status: str = field(default_factory=lambda: DEFAULT_STATUS.value)
    case_sensitive: bool = False
    trim_whitespace: bool = True
    question_code: str = ""
    # MC / MA: list of (label, text, is_correct)
    options: list[tuple[str, str, bool]] = field(default_factory=list)
    # BLANK / SA: list of accepted answer strings
    accepted_answers: list[str] = field(default_factory=list)


@dataclass
class QuestionTypeBreakdown:
    mc: int = 0
    ma: int = 0
    blank: int = 0
    tf: int = 0
    sa: int = 0
    es: int = 0


@dataclass
class QuestionUsageRow:
    question_id: int
    question_code: str
    question_type: str
    learning_outcome_code: str
    difficulty: str
    point_value: float
    is_active: bool
    content: str
    used_count: int
    correct_count: int


@dataclass
class QuestionUsageSummary:
    total_questions: int
    active_questions: int
    total_uses: int
    total_correct: int
    type_breakdown: QuestionTypeBreakdown
    difficulty_breakdown: dict[str, int] = field(default_factory=dict)
    learning_outcome_count: int = 0
    learning_outcome_top: list[tuple[str, int]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class QuestionService:
    """Encapsulates all question-bank CRUD and search operations."""

    _ASSESSMENT_TYPES: tuple[str, ...] = ("Thường xuyên", "Định kỳ", "Tổng kết")
    _DIFFICULTY_LEVELS_BY_TYPE: dict[str, tuple[str, ...]] = {
        QuestionType.TRUE_FALSE.value: ("Nhớ", "Hiểu"),
        QuestionType.MULTIPLE_CHOICE.value: ("Nhớ", "Hiểu", "Vận dụng"),
        QuestionType.MULTIPLE_ANSWER.value: ("Nhớ", "Hiểu", "Vận dụng", "Phân tích"),
        QuestionType.SHORT_ANSWER.value: ("Vận dụng", "Phân tích", "Đánh giá"),
        QuestionType.ESSAY.value: ("Phân tích", "Đánh giá", "Sáng tạo"),
        QuestionType.BLANK.value: ("Nhớ", "Hiểu", "Vận dụng", "Phân tích", "Đánh giá", "Sáng tạo"),
    }
    _DIFFICULTY_LEVEL_ORDER: tuple[str, ...] = (
        "Nhớ",
        "Hiểu",
        "Vận dụng",
        "Phân tích",
        "Đánh giá",
        "Sáng tạo",
    )

    # -----------------------------------------------------------------------
    # Bank operations
    # -----------------------------------------------------------------------

    def list_banks(self, session: Session) -> list[QuestionBank]:
        return (
            session.query(QuestionBank)
            .order_by(QuestionBank.name)
            .all()
        )

    def get_bank_stats(self, session: Session) -> list[BankStats]:
        rows = (
            session.query(
                QuestionBank.id,
                QuestionBank.name,
                func.count(Question.id).label("cnt"),
            )
            .outerjoin(Question, Question.bank_id == QuestionBank.id)
            .group_by(QuestionBank.id)
            .order_by(QuestionBank.name)
            .all()
        )
        return [BankStats(r.id, r.name, r.cnt) for r in rows]

    def get_bank_overview_rows(self, session: Session) -> list[BankOverviewRow]:
        rows = (
            session.query(
                QuestionBank.id,
                QuestionBank.name,
                QuestionBank.assessment_type,
                QuestionBank.course_learning_outcomes,
                func.count(Question.id).label("cnt"),
            )
            .outerjoin(Question, Question.bank_id == QuestionBank.id)
            .group_by(QuestionBank.id)
            .order_by(QuestionBank.name)
            .all()
        )
        items: list[BankOverviewRow] = []
        for row in rows:
            bank = QuestionBank(
                id=int(row.id),
                name=row.name,
                assessment_type=row.assessment_type,
                course_learning_outcomes=row.course_learning_outcomes,
            )
            items.append(
                BankOverviewRow(
                    bank_id=int(row.id),
                    bank_name=row.name,
                    assessment_type=row.assessment_type or "",
                    course_learning_outcomes=bank.get_course_learning_outcomes(),
                    question_count=int(row.cnt or 0),
                )
            )
        return items

    def get_question_type_breakdown(self, session: Session) -> QuestionTypeBreakdown:
        rows = (
            session.query(
                Question.question_type,
                func.count(Question.id).label("cnt"),
            )
            .group_by(Question.question_type)
            .all()
        )
        counts: dict[str, int] = {r.question_type: int(r.cnt) for r in rows}
        return QuestionTypeBreakdown(
            mc=counts.get(QuestionType.MULTIPLE_CHOICE.value, 0),
            ma=counts.get(QuestionType.MULTIPLE_ANSWER.value, 0),
            blank=counts.get(QuestionType.BLANK.value, 0),
            tf=counts.get(QuestionType.TRUE_FALSE.value, 0),
            sa=counts.get(QuestionType.SHORT_ANSWER.value, 0),
            es=counts.get(QuestionType.ESSAY.value, 0),
        )

    def get_usage_banks(self, session: Session) -> list[BankStats]:
        rows = (
            session.query(
                QuestionBank.id,
                QuestionBank.name,
                func.count(Question.id).label("cnt"),
            )
            .outerjoin(Question, Question.bank_id == QuestionBank.id)
            .group_by(QuestionBank.id)
            .order_by(QuestionBank.name)
            .all()
        )
        return [BankStats(r.id, r.name, int(r.cnt)) for r in rows]

    def get_question_usage_rows(
        self, session: Session, bank_id: int
    ) -> list[QuestionUsageRow]:
        rows = (
            session.query(
                Question.id,
                Question.question_code,
                Question.question_type,
                Question.learning_outcome_code,
                Question.difficulty,
                Question.point_value,
                Question.is_active,
                Question.content,
                func.count(QuizQuestion.id.distinct()).label("used_count"),
                func.coalesce(
                    func.sum(
                        case(
                            (AttemptAnswer.is_correct.is_(True), 1),
                            else_=0,
                        )
                    ),
                    0,
                ).label("correct_count"),
            )
            .outerjoin(QuizQuestion, QuizQuestion.question_id == Question.id)
            .outerjoin(
                AttemptAnswer,
                AttemptAnswer.quiz_question_id == QuizQuestion.id,
            )
            .filter(Question.bank_id == bank_id)
            .group_by(Question.id)
            .order_by(Question.id)
            .all()
        )
        return [
            QuestionUsageRow(
                question_id=int(r.id),
                question_code=r.question_code or "",
                question_type=r.question_type,
                learning_outcome_code=r.learning_outcome_code or "",
                difficulty=r.difficulty or "",
                point_value=float(r.point_value or 0.0),
                is_active=bool(r.is_active),
                content=r.content or "",
                used_count=int(r.used_count or 0),
                correct_count=int(r.correct_count or 0),
            )
            for r in rows
        ]

    def build_usage_summary(
        self, usage_rows: list[QuestionUsageRow]
    ) -> QuestionUsageSummary:
        breakdown = QuestionTypeBreakdown()
        difficulty_counts: Counter[str] = Counter()
        clo_counts: Counter[str] = Counter()
        for row in usage_rows:
            if row.question_type == QuestionType.MULTIPLE_CHOICE.value:
                breakdown.mc += 1
            elif row.question_type == QuestionType.MULTIPLE_ANSWER.value:
                breakdown.ma += 1
            elif row.question_type == QuestionType.BLANK.value:
                breakdown.blank += 1
            elif row.question_type == QuestionType.TRUE_FALSE.value:
                breakdown.tf += 1
            elif row.question_type == QuestionType.SHORT_ANSWER.value:
                breakdown.sa += 1
            elif row.question_type == QuestionType.ESSAY.value:
                breakdown.es += 1
            level = self._canonical_difficulty_label(row.difficulty)
            if level:
                difficulty_counts[level] += 1
            clo = row.learning_outcome_code.strip()
            if clo:
                clo_counts[clo] += 1

        return QuestionUsageSummary(
            total_questions=len(usage_rows),
            active_questions=sum(1 for r in usage_rows if r.is_active),
            total_uses=sum(r.used_count for r in usage_rows),
            total_correct=sum(r.correct_count for r in usage_rows),
            type_breakdown=breakdown,
            difficulty_breakdown={
                level: difficulty_counts.get(level, 0)
                for level in self._DIFFICULTY_LEVEL_ORDER
            },
            learning_outcome_count=sum(clo_counts.values()),
            learning_outcome_top=clo_counts.most_common(5),
        )

    def get_question_by_id(self, session: Session, question_id: int) -> Question | None:
        return session.get(Question, question_id)

    def get_bank_by_id(self, session: Session, bank_id: int) -> QuestionBank | None:
        return session.get(QuestionBank, bank_id)

    def get_question_for_edit(self, session: Session, question_id: int) -> Question | None:
        """Load one question with options and detach it for UI editor usage."""
        q = session.get(Question, question_id)
        if q is None:
            return None
        _ = list(q.options)
        session.expunge(q)
        return q

    def create_bank(
        self,
        session: Session,
        name: str,
        *,
        school: str = "",
        department: str = "",
        subject: str = "",
        course_code: str = "",
        exam_title: str = "",
        assessment_type: str = "",
        course_learning_outcomes: list[dict[str, str]] | None = None,
    ) -> QuestionBank:
        name = name.strip()
        if not name:
            raise ValueError("Tên ngân hàng không được để trống.")
        existing = (
            session.query(QuestionBank).filter_by(name=name).first()
        )
        if existing:
            raise ValueError(f"Ngân hàng '{name}' đã tồn tại.")
        clean_assessment_type = self._validate_assessment_type(assessment_type)
        clean_clos = self._normalize_course_learning_outcomes(course_learning_outcomes or [])
        bank = QuestionBank(
            name=name,
            school=school.strip() or None,
            department=department.strip() or None,
            subject=subject.strip() or None,
            course_code=course_code.strip() or None,
            exam_title=exam_title.strip() or None,
            assessment_type=clean_assessment_type or None,
        )
        bank.set_course_learning_outcomes(clean_clos)
        session.add(bank)
        session.flush()
        return bank

    def rename_bank(self, session: Session, bank_id: int, new_name: str) -> None:
        new_name = new_name.strip()
        if not new_name:
            raise ValueError("Tên ngân hàng không được để trống.")
        existing = (
            session.query(QuestionBank)
            .filter(QuestionBank.name == new_name, QuestionBank.id != bank_id)
            .first()
        )
        if existing:
            raise ValueError(f"Ngân hàng '{new_name}' đã tồn tại.")
        bank = session.get(QuestionBank, bank_id)
        if bank is None:
            raise ValueError(f"Không tìm thấy ngân hàng id={bank_id}.")
        bank.name = new_name

    def update_bank(
        self,
        session: Session,
        bank_id: int,
        name: str,
        *,
        school: str = "",
        department: str = "",
        subject: str = "",
        course_code: str = "",
        exam_title: str = "",
        assessment_type: str = "",
        course_learning_outcomes: list[dict[str, str]] | None = None,
    ) -> None:
        """Update bank name and all optional metadata fields."""
        name = name.strip()
        if not name:
            raise ValueError("Tên ngân hàng không được để trống.")
        existing = (
            session.query(QuestionBank)
            .filter(QuestionBank.name == name, QuestionBank.id != bank_id)
            .first()
        )
        if existing:
            raise ValueError(f"Ngân hàng '{name}' đã tồn tại.")
        bank = session.get(QuestionBank, bank_id)
        if bank is None:
            raise ValueError(f"Không tìm thấy ngân hàng id={bank_id}.")
        clean_assessment_type = self._validate_assessment_type(assessment_type)
        clean_clos = self._normalize_course_learning_outcomes(course_learning_outcomes or [])
        bank.name = name
        bank.school = school.strip() or None
        bank.department = department.strip() or None
        bank.subject = subject.strip() or None
        bank.course_code = course_code.strip() or None
        bank.exam_title = exam_title.strip() or None
        bank.assessment_type = clean_assessment_type or None
        bank.set_course_learning_outcomes(clean_clos)

    def delete_bank(self, session: Session, bank_id: int) -> None:
        bank = session.get(QuestionBank, bank_id)
        if bank is None:
            raise ValueError(f"Không tìm thấy ngân hàng id={bank_id}.")
        session.delete(bank)

    # -----------------------------------------------------------------------
    # Question listing / search
    # -----------------------------------------------------------------------

    def list_questions(
        self,
        session: Session,
        bank_id: Optional[int] = None,
        search: str = "",
        question_type: Optional[str] = None,
        difficulty: Optional[str] = None,
        active_only: bool = False,
    ) -> list[Question]:
        q = session.query(Question)
        if bank_id is not None:
            q = q.filter(Question.bank_id == bank_id)
        if search:
            term = f"%{search.strip()}%"
            q = q.filter(
                or_(
                    Question.content.ilike(term),
                    Question.learning_outcome_code.ilike(term),
                    Question.category.ilike(term),
                    Question.question_code.ilike(term),
                    Question.tags.ilike(term),
                )
            )
        if question_type:
            q = q.filter(Question.question_type == question_type)
        if difficulty:
            q = q.filter(Question.difficulty.in_(self._difficulty_filter_values(difficulty)))
        if active_only:
            q = q.filter(Question.is_active.is_(True))
        return q.order_by(Question.id).all()

    def get_question_count(self, session: Session) -> int:
        return session.query(func.count(Question.id)).scalar() or 0

    def get_bank_count(self, session: Session) -> int:
        return session.query(func.count(QuestionBank.id)).scalar() or 0

    # -----------------------------------------------------------------------
    # Question create / update / delete
    # -----------------------------------------------------------------------

    def create_question(
        self, session: Session, data: QuestionEditData
    ) -> Question:
        self._validate_edit_data(session, data)
        q = self._build_question(data)
        session.add(q)
        session.flush()
        self._save_options(session, q, data)
        return q

    def update_question(
        self, session: Session, question_id: int, data: QuestionEditData
    ) -> Question:
        self._validate_edit_data(session, data)
        q = session.get(Question, question_id)
        if q is None:
            raise ValueError(f"Không tìm thấy câu hỏi id={question_id}.")
        # Clear old options
        for opt in list(q.options):
            session.delete(opt)
        session.flush()
        # Update fields
        self._apply_edit_data(q, data)
        self._save_options(session, q, data)
        return q

    def delete_question(self, session: Session, question_id: int) -> None:
        q = session.get(Question, question_id)
        if q is None:
            raise ValueError(f"Không tìm thấy câu hỏi id={question_id}.")
        session.delete(q)

    def delete_questions_bulk(
        self, session: Session, question_ids: list[int]
    ) -> int:
        if not question_ids:
            return 0
        deleted: int = (
            session.query(Question)
            .filter(Question.id.in_(question_ids))
            .delete(synchronize_session=False)
        )
        return deleted

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    def _validate_edit_data(self, session: Session, data: QuestionEditData) -> None:
        if not data.content.strip():
            raise ValueError("Nội dung câu hỏi không được để trống.")
        if data.score <= 0:
            raise ValueError("Điểm phải là số dương.")
        self._validate_learning_outcome_code(
            session,
            data.bank_id,
            data.learning_outcome_code,
        )
        if data.question_type in (
            QuestionType.MULTIPLE_CHOICE,
            QuestionType.MULTIPLE_ANSWER,
            QuestionType.TRUE_FALSE,
        ):
            valid_opts = [o for o in data.options if o[1].strip()]
            min_opts = 2
            if data.question_type == QuestionType.TRUE_FALSE:
                if len(valid_opts) != 2:
                    raise ValueError("True/False cần đúng 2 lựa chọn.")
            elif len(valid_opts) < 2:
                raise ValueError("MC/MA cần ít nhất 2 lựa chọn.")
            correct = [o for o in valid_opts if o[2]]
            if data.question_type == QuestionType.MULTIPLE_CHOICE and len(correct) != 1:
                raise ValueError("Multiple Choice cần đúng 1 đáp án đúng.")
            if data.question_type == QuestionType.MULTIPLE_ANSWER and len(correct) < 2:
                raise ValueError("Multiple Answer cần ít nhất 2 đáp án đúng.")
            if data.question_type == QuestionType.TRUE_FALSE and len(correct) != 1:
                raise ValueError("True/False cần đúng 1 đáp án đúng.")
        elif data.question_type in (
            QuestionType.BLANK,
            QuestionType.SHORT_ANSWER,
            QuestionType.ESSAY,
        ):
            if not any(a.strip() for a in data.accepted_answers):
                raise ValueError("Cần ít nhất một đáp án chấp nhận được.")
            if data.question_type == QuestionType.BLANK:
                if count_blank_placeholders(data.content) == 0:
                    raise ValueError(
                        f"Câu hỏi BLANK phải chứa ít nhất một {BLANK_PLACEHOLDER} "
                        "trong nội dung."
                    )

    def _build_question(self, data: QuestionEditData) -> Question:
        q = Question(
            bank_id=data.bank_id,
            question_code=data.question_code.strip() or None,
            question_type=data.question_type.value if isinstance(data.question_type, QuestionType) else data.question_type,
            content=data.content.strip(),
            hint=data.hint.strip() or None,
            explanation=data.explanation.strip() or None,
            difficulty=data.difficulty or DEFAULT_DIFFICULTY.value,
            learning_outcome_code=data.learning_outcome_code.strip() or None,
            category=data.category.strip() or None,
            tags=data.tags.strip() or None,
            point_value=data.score,
            case_sensitive=data.case_sensitive,
            trim_whitespace=data.trim_whitespace,
            is_active=(data.status == "active"),
        )
        if data.question_type in (
            QuestionType.BLANK,
            QuestionType.SHORT_ANSWER,
            QuestionType.ESSAY,
        ):
            q.accepted_answers = json.dumps(
                [a.strip() for a in data.accepted_answers if a.strip()],
                ensure_ascii=False,
            )
        return q

    def _apply_edit_data(self, q: Question, data: QuestionEditData) -> None:
        q.bank_id = data.bank_id
        q.question_code = data.question_code.strip() or None
        q.question_type = data.question_type.value if isinstance(data.question_type, QuestionType) else data.question_type
        q.content = data.content.strip()
        q.hint = data.hint.strip() or None
        q.explanation = data.explanation.strip() or None
        q.difficulty = data.difficulty or DEFAULT_DIFFICULTY.value
        q.learning_outcome_code = data.learning_outcome_code.strip() or None
        q.category = data.category.strip() or None
        q.tags = data.tags.strip() or None
        q.point_value = data.score
        q.case_sensitive = data.case_sensitive
        q.trim_whitespace = data.trim_whitespace
        q.is_active = (data.status == "active")
        if data.question_type in (
            QuestionType.BLANK,
            QuestionType.SHORT_ANSWER,
            QuestionType.ESSAY,
        ):
            q.accepted_answers = json.dumps(
                [a.strip() for a in data.accepted_answers if a.strip()],
                ensure_ascii=False,
            )
        else:
            q.accepted_answers = None

    def _save_options(
        self, session: Session, q: Question, data: QuestionEditData
    ) -> None:
        if data.question_type not in (
            QuestionType.MULTIPLE_CHOICE,
            QuestionType.MULTIPLE_ANSWER,
            QuestionType.TRUE_FALSE,
        ):
            return
        for sort_idx, (label, text, is_correct) in enumerate(data.options):
            if not text.strip():
                continue
            opt = QuestionOption(
                question_id=q.id,
                option_key=label.upper(),
                option_text=text.strip(),
                is_correct=is_correct,
                sort_order=sort_idx,
            )
            session.add(opt)

    def _validate_assessment_type(self, value: str) -> str:
        clean = value.strip()
        if clean and clean not in self._ASSESSMENT_TYPES:
            raise ValueError("Loại đánh giá không hợp lệ.")
        return clean

    def _normalize_course_learning_outcomes(
        self,
        items: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        clean_items: list[dict[str, str]] = []
        for row in items:
            code = str(row.get("code", "")).strip()
            description = str(row.get("description", "")).strip()
            if not code and not description:
                continue
            if not code or not description:
                raise ValueError("Mỗi chuẩn đầu ra học phần phải có đủ Mã CLO và Mô tả CLO.")
            clean_items.append({"code": code, "description": description})
        return clean_items

    def _validate_learning_outcome_code(
        self,
        session: Session,
        bank_id: int,
        value: str,
    ) -> None:
        code = value.strip()
        if not code:
            return
        bank = session.get(QuestionBank, bank_id)
        if bank is None:
            raise ValueError(f"Không tìm thấy ngân hàng id={bank_id}.")
        allowed_codes = {
            str(row.get("code", "")).strip()
            for row in bank.get_course_learning_outcomes()
            if str(row.get("code", "")).strip()
        }
        if code not in allowed_codes:
            raise ValueError("Chuẩn đầu ra của câu hỏi phải thuộc danh sách CLO của ngân hàng.")

    def _difficulty_filter_values(self, difficulty: str) -> list[str]:
        clean = difficulty.strip()
        if not clean:
            return []
        mapping = {
            "Nhớ": ["Nhớ", "easy"],
            "Hiểu": ["Hiểu", "medium"],
            "Vận dụng": ["Vận dụng", "hard"],
            "Phân tích": ["Phân tích"],
            "Đánh giá": ["Đánh giá"],
            "Sáng tạo": ["Sáng tạo"],
        }
        return mapping.get(clean, [clean])

    def _canonical_difficulty_label(self, difficulty: str) -> str:
        raw = difficulty.strip()
        if not raw:
            return ""
        lower = raw.lower()
        if lower == "easy":
            return "Nhớ"
        if lower == "medium":
            return "Hiểu"
        if lower == "hard":
            return "Vận dụng"
        return raw
