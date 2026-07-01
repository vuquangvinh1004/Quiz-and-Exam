from __future__ import annotations

from PySide6.QtCore import Qt
from core.database.models import Question

from ui.facades.question_bank_facade import QuestionBankFacade
from ui.views.question_bank_view import QuestionBankView


def test_question_bank_view_shows_bank_context_summary(monkeypatch, qtbot) -> None:
    monkeypatch.setattr(
        QuestionBankFacade,
        "list_bank_overview_items",
        lambda self: [
            {
                "id": 1,
                "name": "NHCH Python",
                "assessment_type": "Thường xuyên",
                "course_learning_outcomes": [
                    {"code": "CLO_1", "description": "Mô tả 1"},
                    {"code": "CLO_2", "description": "Mô tả 2"},
                ],
                "question_count": 10,
            }
        ],
    )
    monkeypatch.setattr(QuestionBankFacade, "list_questions", lambda self, **kwargs: [])

    view = QuestionBankView()
    qtbot.addWidget(view)
    view._load_banks()

    item = view._bank_list.item(0)
    assert item is not None
    assert item.data(Qt.ItemDataRole.UserRole) == 1
    assert "Thường xuyên | CLO_1, CLO_2 | 10 câu hỏi" in item.text()


def test_question_bank_table_uses_short_type_labels_and_reordered_headers(monkeypatch, qtbot) -> None:
    monkeypatch.setattr(
        QuestionBankFacade,
        "list_bank_overview_items",
        lambda self: [
            {
                "id": 1,
                "name": "NHCH Python",
                "assessment_type": "Thường xuyên",
                "course_learning_outcomes": [],
                "question_count": 1,
            }
        ],
    )
    monkeypatch.setattr(
        QuestionBankFacade,
        "list_questions",
        lambda self, **kwargs: [
            Question(
                id=1,
                bank_id=1,
                question_code="Q001",
                question_type="MC",
                content="Noi dung",
                learning_outcome_code="CLO_1",
                category="1",
                difficulty="medium",
                point_value=1.0,
                is_active=True,
            )
        ],
    )

    view = QuestionBankView()
    qtbot.addWidget(view)
    view._load_banks()
    view._refresh_questions()

    headers = [view._q_table.horizontalHeaderItem(i).text() for i in range(view._q_table.columnCount())]
    assert headers == ["STT", "Mã", "Nội dung", "Chương", "CLO", "Mức độ", "Loại", "Điểm", "Trạng thái"]
    assert view._q_table.item(0, 3).text() == "1"
    assert view._q_table.item(0, 4).text() == "CLO_1"
    assert view._q_table.item(0, 5).text() == "Hiểu"
    assert view._q_table.item(0, 6).text() == "MC"
    assert view._q_table.item(0, 3).textAlignment() == int(Qt.AlignmentFlag.AlignCenter)
    assert view._q_table.item(0, 4).textAlignment() == int(Qt.AlignmentFlag.AlignCenter)
    assert view._q_table.item(0, 5).textAlignment() == int(Qt.AlignmentFlag.AlignCenter)
    assert view._q_table.item(0, 6).textAlignment() == int(Qt.AlignmentFlag.AlignCenter)
    assert view._q_table.wordWrap() is True
    assert view._q_table.verticalHeader().defaultSectionSize() == 58
