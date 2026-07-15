from __future__ import annotations

from types import SimpleNamespace

from core.domain.services.question_service_types import ProblemRubricTemplateSummary
from ui.dialogs.problem_template_picker_dialog import ProblemTemplatePickerDialog


class _FakeFacade:
    def get_problem_template(self, template_id: int):
        return SimpleNamespace(
            template_id=template_id,
            bank_id=1,
            name="Mẫu kiểm định",
            rows=[
                SimpleNamespace(marker="B1", content="Nội dung 1", score=1.0),
                SimpleNamespace(marker="", content="Nội dung 2", score=2.0),
            ],
        )


def test_problem_template_picker_shows_detailed_preview(qtbot) -> None:
    templates = [
        ProblemRubricTemplateSummary(
            template_id=11,
            bank_id=1,
            name="Mẫu kiểm định",
            row_count=2,
            total_score=3.0,
        )
    ]
    dlg = ProblemTemplatePickerDialog(templates, facade=_FakeFacade(), bank_id=1)
    qtbot.addWidget(dlg)

    html = dlg._format_preview(templates[0])
    assert "Xem trước mẫu rubric" in html
    assert "Tên mẫu:" in html
    assert "<table" in html
    assert "Nội dung 1" in html
    assert "Nội dung 2" in html
