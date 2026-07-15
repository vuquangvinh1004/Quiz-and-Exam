"""Implementation helpers for question-bank CRUD/search services."""
from __future__ import annotations

import json
from collections import Counter

from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session

from core.database.models import (
    AttemptAnswer,
    Question,
    QuestionBank,
    QuestionOption,
    QuizQuestion,
)
from core.domain.services.question_service_types import (
    BankOverviewRow,
    BankStats,
    ProblemRubricRow,
    QuestionEditData,
    QuestionTypeBreakdown,
    QuestionUsageRow,
    QuestionUsageSummary,
)
from core.utils.constants import (
    BLANK_PLACEHOLDER,
    CRQ_QUESTION_TYPES,
    DEFAULT_DIFFICULTY,
    QuestionType,
    is_crq_question_type,
)
from core.utils.validators import count_blank_placeholders


class QuestionAnalyticsService:
    """Read-only analytics and overview helpers."""

    _DIFFICULTY_LEVEL_ORDER: tuple[str, ...] = (
        "Nhớ",
        "Hiểu",
        "Vận dụng",
        "Phân tích",
        "Đánh giá",
        "Sáng tạo",
    )

    @staticmethod
    def list_banks(session: Session) -> list[QuestionBank]:
        return session.query(QuestionBank).order_by(QuestionBank.name).all()

    @staticmethod
    def get_bank_stats(session: Session) -> list[BankStats]:
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

    @staticmethod
    def get_bank_overview_rows(session: Session) -> list[BankOverviewRow]:
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

    @staticmethod
    def get_question_type_breakdown(session: Session) -> QuestionTypeBreakdown:
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
            pr=counts.get(QuestionType.PROBLEM.value, 0),
            crq=counts.get(QuestionType.ESSAY.value, 0)
            + counts.get(QuestionType.PROBLEM.value, 0),
        )

    @staticmethod
    def get_usage_banks(session: Session) -> list[BankStats]:
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

    @staticmethod
    def get_question_usage_rows(
        session: Session,
        bank_id: int,
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

    @classmethod
    def build_usage_summary(
        cls,
        usage_rows: list[QuestionUsageRow],
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
            elif row.question_type == QuestionType.PROBLEM.value:
                breakdown.pr += 1
            if is_crq_question_type(row.question_type):
                breakdown.crq += 1
            level = cls._canonical_difficulty_label(row.difficulty)
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
                for level in cls._DIFFICULTY_LEVEL_ORDER
            },
            learning_outcome_count=sum(clo_counts.values()),
            learning_outcome_top=clo_counts.most_common(5),
        )

    @staticmethod
    def get_question_by_id(session: Session, question_id: int) -> Question | None:
        return session.get(Question, question_id)

    @staticmethod
    def get_bank_by_id(session: Session, bank_id: int) -> QuestionBank | None:
        return session.get(QuestionBank, bank_id)

    @staticmethod
    def get_question_for_edit(
        session: Session,
        question_id: int,
    ) -> Question | None:
        q = session.get(Question, question_id)
        if q is None:
            return None
        _ = list(q.options)
        session.expunge(q)
        return q

    @staticmethod
    def get_question_count(session: Session) -> int:
        return session.query(func.count(Question.id)).scalar() or 0

    @staticmethod
    def get_bank_count(session: Session) -> int:
        return session.query(func.count(QuestionBank.id)).scalar() or 0

    @staticmethod
    def _canonical_difficulty_label(difficulty: str) -> str:
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


class QuestionBankMutatorService:
    """Create/update/delete question banks."""

    _ASSESSMENT_TYPES: tuple[str, ...] = ("Thường xuyên", "Định kỳ", "Tổng kết")

    @staticmethod
    def create_bank(
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
        existing = session.query(QuestionBank).filter_by(name=name).first()
        if existing:
            raise ValueError(f"Ngân hàng '{name}' đã tồn tại.")
        clean_assessment_type = QuestionBankMutatorService._validate_assessment_type(
            assessment_type
        )
        clean_clos = QuestionBankMutatorService._normalize_course_learning_outcomes(
            course_learning_outcomes or []
        )
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

    @staticmethod
    def rename_bank(session: Session, bank_id: int, new_name: str) -> None:
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

    @staticmethod
    def update_bank(
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
        clean_assessment_type = QuestionBankMutatorService._validate_assessment_type(
            assessment_type
        )
        clean_clos = QuestionBankMutatorService._normalize_course_learning_outcomes(
            course_learning_outcomes or []
        )
        bank.name = name
        bank.school = school.strip() or None
        bank.department = department.strip() or None
        bank.subject = subject.strip() or None
        bank.course_code = course_code.strip() or None
        bank.exam_title = exam_title.strip() or None
        bank.assessment_type = clean_assessment_type or None
        bank.set_course_learning_outcomes(clean_clos)

    @staticmethod
    def delete_bank(session: Session, bank_id: int) -> None:
        bank = session.get(QuestionBank, bank_id)
        if bank is None:
            raise ValueError(f"Không tìm thấy ngân hàng id={bank_id}.")
        session.delete(bank)

    @staticmethod
    def _validate_assessment_type(value: str) -> str:
        clean = value.strip()
        if clean and clean not in QuestionBankMutatorService._ASSESSMENT_TYPES:
            raise ValueError("Loại đánh giá không hợp lệ.")
        return clean

    @staticmethod
    def _normalize_course_learning_outcomes(
        items: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        clean_items: list[dict[str, str]] = []
        for row in items:
            code = str(row.get("code", "")).strip()
            description = str(row.get("description", "")).strip()
            if not code and not description:
                continue
            if not code or not description:
                raise ValueError(
                    "Mỗi chuẩn đầu ra học phần phải có đủ Mã CLO và Mô tả CLO."
                )
            clean_items.append({"code": code, "description": description})
        return clean_items


class QuestionQueryService:
    """Search and filter helpers for questions."""

    @staticmethod
    def list_questions(
        session: Session,
        bank_id: int | None = None,
        search: str = "",
        question_type: str | None = None,
        difficulty: str | None = None,
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
            if question_type == "CRQ":
                q = q.filter(
                    Question.question_type.in_(
                        [qt.value for qt in CRQ_QUESTION_TYPES]
                    )
                )
            else:
                q = q.filter(Question.question_type == question_type)
        if difficulty:
            q = q.filter(Question.difficulty.in_(QuestionQueryService._difficulty_filter_values(difficulty)))
        if active_only:
            q = q.filter(Question.is_active.is_(True))
        return q.order_by(Question.id).all()

    @staticmethod
    def _difficulty_filter_values(difficulty: str) -> list[str]:
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


class QuestionMutationService:
    _PROBLEM_VARIANT = "problem"

    """Create, update and delete question rows."""

    @staticmethod
    def create_question(session: Session, data: QuestionEditData) -> Question:
        QuestionMutationService._validate_edit_data(session, data)
        q = QuestionMutationService._build_question(data)
        session.add(q)
        session.flush()
        QuestionMutationService._save_options(session, q, data)
        return q

    @staticmethod
    def update_question(
        session: Session,
        question_id: int,
        data: QuestionEditData,
    ) -> Question:
        QuestionMutationService._validate_edit_data(session, data)
        q = session.get(Question, question_id)
        if q is None:
            raise ValueError(f"Không tìm thấy câu hỏi id={question_id}.")
        for opt in list(q.options):
            session.delete(opt)
        session.flush()
        QuestionMutationService._apply_edit_data(q, data)
        QuestionMutationService._save_options(session, q, data)
        return q

    @staticmethod
    def delete_question(session: Session, question_id: int) -> None:
        q = session.get(Question, question_id)
        if q is None:
            raise ValueError(f"Không tìm thấy câu hỏi id={question_id}.")
        session.delete(q)

    @staticmethod
    def delete_questions_bulk(session: Session, question_ids: list[int]) -> int:
        if not question_ids:
            return 0
        deleted: int = (
            session.query(Question)
            .filter(Question.id.in_(question_ids))
            .delete(synchronize_session=False)
        )
        return deleted

    @staticmethod
    def _validate_edit_data(session: Session, data: QuestionEditData) -> None:
        if not data.content.strip():
            raise ValueError("Nội dung câu hỏi không được để trống.")
        if data.score <= 0:
            raise ValueError("Điểm phải là số dương.")
        QuestionMutationService._validate_learning_outcome_code(
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
        ):
            if not any(a.strip() for a in data.accepted_answers):
                raise ValueError("Cần ít nhất một đáp án chấp nhận được.")
            if data.question_type == QuestionType.BLANK:
                if count_blank_placeholders(data.content) == 0:
                    raise ValueError(
                        f"Câu hỏi BLANK phải chứa ít nhất một {BLANK_PLACEHOLDER} trong nội dung."
                    )
        elif data.question_type in CRQ_QUESTION_TYPES:
            QuestionMutationService._validate_crq_rubric(data)

    @staticmethod
    def _validate_crq_rubric(data: QuestionEditData) -> None:
        rubric_rows = QuestionMutationService._clean_crq_rubric(data.problem_rubric)
        if not rubric_rows:
            raise ValueError("Cần ít nhất một dòng đáp án chấp nhận cho CRQ.")

    @staticmethod
    def _clean_crq_rubric(rows: list[ProblemRubricRow]) -> list[ProblemRubricRow]:
        clean_rows: list[ProblemRubricRow] = []
        for row in rows:
            marker = str(row.marker or "").strip()
            content = str(row.content or "").strip()
            score = float(row.score or 0.0)
            if not marker and not content and score <= 0:
                continue
            clean_rows.append(
                ProblemRubricRow(
                    marker=marker,
                    content=content,
                    score=score,
                )
            )
        return clean_rows

    @staticmethod
    def _resolve_crq_subtype(data: QuestionEditData) -> str:
        variant = str(getattr(data, "editor_variant", "") or "").strip().lower()
        if variant in {"essay", "problem"}:
            return variant
        if data.question_type == QuestionType.PROBLEM:
            return "problem"
        return "essay"

    @staticmethod
    def _serialize_crq_payload(data: QuestionEditData) -> dict[str, object]:
        rubric_rows = QuestionMutationService._clean_crq_rubric(data.problem_rubric)
        payload: dict[str, object] = {
            "kind": "crq",
            "subtype": QuestionMutationService._resolve_crq_subtype(data),
            "answers": [row.content for row in rubric_rows if row.content],
            "rubric": [
                {
                    "marker": row.marker,
                    "content": row.content,
                    "score": row.score,
                }
                for row in rubric_rows
            ],
        }
        template_name = str(getattr(data, "problem_template_name", "") or "").strip()
        template_id = getattr(data, "problem_template_id", None)
        if template_name:
            payload["template_name"] = template_name
        if template_id is not None:
            payload["template_id"] = template_id
        return payload

    @staticmethod
    def _serialize_accepted_answers_payload(data: QuestionEditData) -> list[str] | dict[str, object]:
        if data.question_type in CRQ_QUESTION_TYPES:
            return QuestionMutationService._serialize_crq_payload(data)
        return [a.strip() for a in data.accepted_answers if a.strip()]

    @staticmethod
    def _build_question(data: QuestionEditData) -> Question:
        q = Question(
            bank_id=data.bank_id,
            question_code=data.question_code.strip() or None,
            question_type=data.question_type.value
            if isinstance(data.question_type, QuestionType)
            else data.question_type,
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
            QuestionType.PROBLEM,
        ):
            q.accepted_answers = json.dumps(
                QuestionMutationService._serialize_accepted_answers_payload(data),
                ensure_ascii=False,
            )
        return q

    @staticmethod
    def _apply_edit_data(q: Question, data: QuestionEditData) -> None:
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
        q.is_active = data.status == "active"
        if data.question_type in (
            QuestionType.BLANK,
            QuestionType.SHORT_ANSWER,
            QuestionType.ESSAY,
            QuestionType.PROBLEM,
        ):
            q.accepted_answers = json.dumps(
                QuestionMutationService._serialize_accepted_answers_payload(data),
                ensure_ascii=False,
            )
        else:
            q.accepted_answers = None

    @staticmethod
    def _save_options(session: Session, q: Question, data: QuestionEditData) -> None:
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

    @staticmethod
    def _validate_learning_outcome_code(
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
            raise ValueError(
                "Chuẩn đầu ra của câu hỏi phải thuộc danh sách CLO của ngân hàng."
            )


__all__ = [
    "QuestionAnalyticsService",
    "QuestionBankMutatorService",
    "QuestionMutationService",
    "QuestionQueryService",
]
