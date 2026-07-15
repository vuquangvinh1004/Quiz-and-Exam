"""Persistence helpers for problem rubric templates."""
from __future__ import annotations

from sqlalchemy.orm import Session

from core.database.models import QuestionRubricTemplate
from core.domain.services.question_service_types import (
    ProblemRubricRow,
    ProblemRubricTemplateData,
    ProblemRubricTemplateSummary,
)


class ProblemTemplateService:
    """Store and retrieve reusable problem rubric templates."""

    @staticmethod
    def list_templates(session: Session, bank_id: int) -> list[ProblemRubricTemplateSummary]:
        rows = (
            session.query(QuestionRubricTemplate)
            .filter(QuestionRubricTemplate.bank_id == bank_id)
            .order_by(QuestionRubricTemplate.name)
            .all()
        )
        return [
            ProblemRubricTemplateSummary(
                template_id=row.id,
                bank_id=row.bank_id,
                name=row.name,
                row_count=len(row.get_rows()),
                total_score=ProblemTemplateService._total_score(row.get_rows()),
            )
            for row in rows
        ]

    @staticmethod
    def get_template(
        session: Session,
        template_id: int,
    ) -> ProblemRubricTemplateData | None:
        row = session.get(QuestionRubricTemplate, template_id)
        if row is None:
            return None
        return ProblemRubricTemplateData(
            template_id=row.id,
            bank_id=row.bank_id,
            name=row.name,
            rows=ProblemTemplateService._rows_to_dtos(row.get_rows()),
        )

    @staticmethod
    def save_template(
        session: Session,
        bank_id: int,
        name: str,
        rows: list[ProblemRubricRow],
    ) -> ProblemRubricTemplateSummary:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Tên mẫu không được để trống.")
        clean_rows = ProblemTemplateService._clean_rows(rows)
        if not clean_rows:
            raise ValueError("Mẫu phải có ít nhất một dòng đáp án.")

        template = (
            session.query(QuestionRubricTemplate)
            .filter(
                QuestionRubricTemplate.bank_id == bank_id,
                QuestionRubricTemplate.name == clean_name,
            )
            .one_or_none()
        )
        if template is None:
            template = QuestionRubricTemplate(
                bank_id=bank_id,
                name=clean_name,
                template_payload="",
            )
            session.add(template)

        template.set_rows(
            [
                {
                    "marker": row.marker,
                    "content": row.content,
                    "score": row.score,
                }
                for row in clean_rows
            ]
        )
        session.flush()
        return ProblemRubricTemplateSummary(
            template_id=template.id,
            bank_id=template.bank_id,
            name=template.name,
            row_count=len(clean_rows),
            total_score=ProblemTemplateService._total_score(clean_rows),
        )

    @staticmethod
    def delete_template(session: Session, template_id: int) -> None:
        template = session.get(QuestionRubricTemplate, template_id)
        if template is None:
            raise ValueError(f"Không tìm thấy mẫu id={template_id}.")
        session.delete(template)
        session.flush()

    @staticmethod
    def rename_template(
        session: Session,
        template_id: int,
        new_name: str,
    ) -> ProblemRubricTemplateSummary:
        clean_name = new_name.strip()
        if not clean_name:
            raise ValueError("Tên mẫu không được để trống.")
        template = session.get(QuestionRubricTemplate, template_id)
        if template is None:
            raise ValueError(f"Không tìm thấy mẫu id={template_id}.")
        existing = (
            session.query(QuestionRubricTemplate)
            .filter(
                QuestionRubricTemplate.bank_id == template.bank_id,
                QuestionRubricTemplate.name == clean_name,
                QuestionRubricTemplate.id != template_id,
            )
            .one_or_none()
        )
        if existing is not None:
            raise ValueError(f"Ngân hàng đã có mẫu '{clean_name}'.")
        template.name = clean_name
        session.flush()
        rows = template.get_rows()
        return ProblemRubricTemplateSummary(
            template_id=template.id,
            bank_id=template.bank_id,
            name=template.name,
            row_count=len(rows),
            total_score=ProblemTemplateService._total_score(rows),
        )

    @staticmethod
    def _clean_rows(rows: list[ProblemRubricRow]) -> list[ProblemRubricRow]:
        clean_rows: list[ProblemRubricRow] = []
        for row in rows:
            marker = str(row.marker or "").strip()
            content = str(row.content or "").strip()
            score = float(row.score or 0.0)
            if not marker and not content and score <= 0:
                continue
            clean_rows.append(ProblemRubricRow(marker=marker, content=content, score=score))
        return clean_rows

    @staticmethod
    def _rows_to_dtos(rows: list[dict[str, object]]) -> list[ProblemRubricRow]:
        return [
            ProblemRubricRow(
                marker=str(row.get("marker", "")).strip(),
                content=str(row.get("content", "")).strip(),
                score=float(row.get("score", 0.0) or 0.0),
            )
            for row in rows
            if isinstance(row, dict)
        ]

    @staticmethod
    def _total_score(rows: list[ProblemRubricRow] | list[dict[str, object]]) -> float:
        total = 0.0
        for row in rows:
            if isinstance(row, ProblemRubricRow):
                total += float(row.score or 0.0)
            elif isinstance(row, dict):
                total += float(row.get("score", 0.0) or 0.0)
        return total


__all__ = ["ProblemTemplateService"]
