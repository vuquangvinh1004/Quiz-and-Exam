from __future__ import annotations

import json

from core.database.models import Question, QuestionOption
from modules.quiz_builder.selector import QuestionSelector


def _mc_question() -> Question:
    q = Question(
        id=1,
        bank_id=1,
        question_type="MC",
        content="Sample MC",
        difficulty="easy",
        learning_outcome_code="CLO_1",
        category="Chuong 1",
        is_active=True,
    )
    q.options = [
        QuestionOption(option_key="A", option_text="Opt A", is_correct=False, sort_order=1),
        QuestionOption(option_key="B", option_text="Opt B", is_correct=True, sort_order=2),
        QuestionOption(option_key="C", option_text="Opt C", is_correct=False, sort_order=3),
        QuestionOption(option_key="D", option_text="Opt D", is_correct=False, sort_order=4),
    ]
    return q


def test_build_snapshots_relabels_option_keys_when_shuffled() -> None:
    selector = QuestionSelector()
    q = _mc_question()

    snapshots = selector.build_snapshots([q], shuffle_options=True)
    options = snapshots[0]["options"]

    assert [o["key"] for o in options] == ["A", "B", "C", "D"]
    assert sum(1 for o in options if o["is_correct"]) == 1


def test_build_snapshots_keeps_original_keys_without_shuffle() -> None:
    selector = QuestionSelector()
    q = _mc_question()

    snapshots = selector.build_snapshots([q], shuffle_options=False)
    options = snapshots[0]["options"]

    assert [o["key"] for o in options] == ["A", "B", "C", "D"]


def test_build_snapshots_carries_statistics_metadata() -> None:
    selector = QuestionSelector()
    q = _mc_question()

    snapshot = selector.build_snapshots([q], shuffle_options=False)[0]

    assert snapshot["difficulty"] == "easy"
    assert snapshot["learning_outcome_code"] == "CLO_1"
    assert snapshot["category"] == "Chuong 1"


def test_build_snapshots_carries_problem_rubric_metadata() -> None:
    selector = QuestionSelector()
    q = Question(
        id=2,
        bank_id=1,
        question_type="ES",
        content="Giải bài toán",
        difficulty="Phân tích",
        accepted_answers=json.dumps(
            {
                "kind": "problem",
                "answers": ["Bước 1", "Bước 2"],
                "rubric": [
                    {"marker": "B1", "content": "Bước 1", "score": 2.0},
                    {"marker": "B2", "content": "Bước 2", "score": 4.0},
                ],
            }
        ),
        is_active=True,
    )

    snapshot = selector.build_snapshots([q], shuffle_options=False)[0]

    assert snapshot["question_variant"] == "problem"
    assert snapshot["problem_rubric"][0]["marker"] == "B1"
    assert snapshot["accepted_answers"] == ["Bước 1", "Bước 2"]
