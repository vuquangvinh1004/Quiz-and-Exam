"""Unit tests for QuizAnswerRenderer component."""
from __future__ import annotations

import os

import pytest
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout

from core.domain.services.quiz_service import QuizQuestionSnapshot
from ui.widgets.quiz_answer_renderer import QuizAnswerRenderer

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp_instance():
    return QApplication.instance() or QApplication([])


def _host_with_renderer(qapp_instance):
    host = QWidget()
    layout = QVBoxLayout(host)
    renderer = QuizAnswerRenderer(host)
    renderer.attach(layout)
    host.show()
    qapp_instance.processEvents()
    return host, renderer


def test_render_mc_and_collect_payload(qapp_instance):
    _, renderer = _host_with_renderer(qapp_instance)
    qq = QuizQuestionSnapshot(
        quiz_question_id=1,
        order=1,
        content="Question",
        type="MC",
        options=[
            {"key": "A", "text": "Option A"},
            {"key": "B", "text": "Option B"},
        ],
    )
    renderer.render_question(qq)

    renderer._radio_pool[0].setChecked(True)
    payload = renderer.current_payload("MC")

    assert payload == {"selected": "A"}


def test_render_ma_and_restore_payload(qapp_instance):
    _, renderer = _host_with_renderer(qapp_instance)
    qq = QuizQuestionSnapshot(
        quiz_question_id=2,
        order=2,
        content="Question",
        type="MA",
        options=[
            {"key": "A", "text": "Option A"},
            {"key": "B", "text": "Option B"},
            {"key": "C", "text": "Option C"},
        ],
    )
    renderer.render_question(qq)
    renderer.restore_answer("MA", {"selected": ["A", "C"]})

    payload = renderer.current_payload("MA")

    assert set(payload["selected"]) == {"A", "C"}


def test_render_blank_uses_multiblank_placeholder(qapp_instance):
    _, renderer = _host_with_renderer(qapp_instance)
    qq = QuizQuestionSnapshot(
        quiz_question_id=3,
        order=3,
        content="A ________ B ________",
        type="BLANK",
    )
    renderer.render_question(qq)

    ph = renderer._text_answer.placeholderText()

    assert "phân cách bằng ||" in ph


def test_text_payload_and_lock_unlock(qapp_instance):
    _, renderer = _host_with_renderer(qapp_instance)
    qq = QuizQuestionSnapshot(
        quiz_question_id=4,
        order=4,
        content="Question",
        type="SA",
    )
    renderer.render_question(qq)
    renderer._text_answer.setText(" Mercury ")

    payload = renderer.current_payload("SA")
    assert payload == {"text": "Mercury"}

    renderer.set_input_enabled(False)
    assert renderer._text_answer.isReadOnly() is True

    renderer.set_input_enabled(True)
    assert renderer._text_answer.isReadOnly() is False
