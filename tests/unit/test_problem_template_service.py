from __future__ import annotations

import pytest

from core.database.models import QuestionBank
from core.domain.services.problem_template_service import ProblemTemplateService
from core.domain.services.question_service_types import ProblemRubricRow


def test_problem_template_service_roundtrip(db_session) -> None:
    bank = QuestionBank(name="Template Bank")
    db_session.add(bank)
    db_session.flush()

    service = ProblemTemplateService()
    summary = service.save_template(
        db_session,
        bank.id,
        "Template 1",
        [
            ProblemRubricRow(marker="B1", content="Dòng 1", score=1.5),
            ProblemRubricRow(marker="", content="Dòng 2", score=2.5),
        ],
    )

    assert summary.name == "Template 1"
    assert summary.row_count == 2
    assert summary.total_score == 4.0

    templates = service.list_templates(db_session, bank.id)
    assert len(templates) == 1
    assert templates[0].name == "Template 1"

    data = service.get_template(db_session, summary.template_id)
    assert data is not None
    assert data.rows[0].marker == "B1"
    assert data.rows[1].content == "Dòng 2"

    service.delete_template(db_session, summary.template_id)
    assert service.list_templates(db_session, bank.id) == []


def test_problem_template_service_rename_roundtrip(db_session) -> None:
    bank = QuestionBank(name="Template Bank Rename")
    db_session.add(bank)
    db_session.flush()

    service = ProblemTemplateService()
    summary = service.save_template(
        db_session,
        bank.id,
        "Template A",
        [ProblemRubricRow(marker="B1", content="Dòng 1", score=1.0)],
    )

    renamed = service.rename_template(db_session, summary.template_id, "Template B")
    assert renamed.name == "Template B"

    templates = service.list_templates(db_session, bank.id)
    assert len(templates) == 1
    assert templates[0].name == "Template B"


def test_problem_template_service_rename_rejects_duplicates(db_session) -> None:
    bank = QuestionBank(name="Template Bank Duplicate")
    db_session.add(bank)
    db_session.flush()

    service = ProblemTemplateService()
    first = service.save_template(
        db_session,
        bank.id,
        "Template A",
        [ProblemRubricRow(marker="B1", content="Dòng 1", score=1.0)],
    )
    service.save_template(
        db_session,
        bank.id,
        "Template B",
        [ProblemRubricRow(marker="B2", content="Dòng 2", score=2.0)],
    )

    with pytest.raises(ValueError, match="đã có mẫu"):
        service.rename_template(db_session, first.template_id, "Template B")
