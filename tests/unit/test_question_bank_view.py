from __future__ import annotations

from PySide6.QtCore import Qt
from sqlalchemy.exc import SQLAlchemyError
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


def test_question_bank_table_renders_latex_preview(monkeypatch, qtbot) -> None:
    monkeypatch.setattr(
        QuestionBankFacade,
        "list_bank_overview_items",
        lambda self: [
            {
                "id": 1,
                "name": "NHCH Latex",
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
                question_code="Q-LTX",
                question_type="ES",
                content=r"Chứng minh $t_{\alpha; n-1}=\begin{bmatrix}1 & 2 \\ 3 & 4\end{bmatrix}$",
                learning_outcome_code="CLO_1",
                category="1",
                difficulty="Phân tích",
                point_value=1.0,
                is_active=True,
            )
        ],
    )

    view = QuestionBankView()
    qtbot.addWidget(view)
    view._load_banks()
    view._refresh_questions()

    assert "t" in view._q_table.item(0, 2).text()
    assert "α" in view._q_table.item(0, 2).toolTip()
    assert "1" in view._q_table.item(0, 2).text()
    assert "[" in view._q_table.item(0, 2).text() or "(" in view._q_table.item(0, 2).text()


def test_question_bank_add_bank_handles_database_errors(monkeypatch, qtbot) -> None:
    class _FakeDialog:
        def __init__(self, *args, **kwargs):
            pass

        def exec(self):
            return _FakeDialog.DialogCode.Accepted

        def get_data(self):
            return {
                "name": "Bank Crash",
                "school": "",
                "department": "",
                "subject": "",
                "course_code": "",
                "exam_title": "",
                "assessment_type": "",
                "course_learning_outcomes": [],
            }

    _FakeDialog.DialogCode = type("DialogCode", (), {"Accepted": 1})

    errors: list[tuple[str, str]] = []

    monkeypatch.setattr(
        "ui.views.question_bank_actions_mixin.BankMetaDialog",
        _FakeDialog,
    )
    monkeypatch.setattr(
        QuestionBankFacade,
        "create_bank",
        lambda self, data: (_ for _ in ()).throw(SQLAlchemyError("db failed")),
    )
    monkeypatch.setattr(
        "ui.views.question_bank_actions_mixin.show_critical_error",
        lambda parent, title, message, exc=None: errors.append((title, message)),
    )
    monkeypatch.setattr(
        QuestionBankFacade,
        "list_bank_overview_items",
        lambda self: [],
    )
    monkeypatch.setattr(
        QuestionBankFacade,
        "list_questions",
        lambda self, **kwargs: [],
    )

    view = QuestionBankView()
    qtbot.addWidget(view)

    view._add_bank()

    assert errors == [("Lỗi", "Không thể tạo ngân hàng.")]


def test_question_bank_add_problem_handles_constructor_errors(monkeypatch, qtbot) -> None:
    errors: list[tuple[str, str]] = []

    class _ExplodingProblemEditorDialog:
        DialogCode = type("DialogCode", (), {"Accepted": 1})

        def __init__(self, *args, **kwargs):
            raise ValueError("bad bank metadata")

    monkeypatch.setattr(
        QuestionBankFacade,
        "list_bank_overview_items",
        lambda self: [
            {
                "id": 1,
                "name": "NHCH Problem",
                "assessment_type": "Thường xuyên",
                "course_learning_outcomes": [],
                "question_count": 0,
            }
        ],
    )
    monkeypatch.setattr(
        QuestionBankFacade,
        "list_questions",
        lambda self, **kwargs: [],
    )
    monkeypatch.setattr(
        "ui.views.question_bank_actions_mixin.ProblemEditorDialog",
        _ExplodingProblemEditorDialog,
    )
    monkeypatch.setattr(
        "ui.views.question_bank_actions_mixin.show_critical_error",
        lambda parent, title, message, exc=None: errors.append((title, message)),
    )

    view = QuestionBankView()
    qtbot.addWidget(view)
    view._load_banks()
    view._current_bank_id = 1

    view._add_problem()

    assert errors == [("Lỗi", "Không thể mở cửa sổ thêm bài toán.")]
