"""Presentation helpers for quiz runner feedback and result summaries."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox, QWidget

from core.utils.constants import QuizMode
from modules.grading.result_builder import AttemptResultData, ModeSummaryBuilder


class QuizResultPresenter:
    """Builds display text/styles for quiz runner result UI."""

    @staticmethod
    def build_study_feedback(grade_result, explanation: str) -> tuple[str, str]:
        """Return (html_text, inline_style) for STUDY per-question feedback."""
        if grade_result.feedback_state == "skipped":
            text = "⬜ Chưa trả lời câu này."
            style = "background: #f0f0f0; color: #555;"
        elif grade_result.is_correct:
            text = "✅ Câu trả lời đúng!"
            style = "background: #d4edda; color: #155724;"
        else:
            text = f"❌ Sai. Đáp án đúng: <b>{grade_result.correct_answer_display}</b>"
            style = "background: #f8d7da; color: #721c24;"

        if explanation:
            text += f"<br><i>Giải thích: {explanation}</i>"
        return text, style

    @staticmethod
    def show_non_exam_summary(parent: QWidget, data: AttemptResultData) -> None:
        """Show summary dialog used by PRACTICE/STUDY modes."""
        msg = QMessageBox(parent)
        msg.setWindowTitle("Kết quả bài làm")
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setText(ModeSummaryBuilder.build_html(data))
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.exec()

    @staticmethod
    def build_done_summary_html(data: AttemptResultData, mode: str) -> str:
        """Return done-panel HTML summary after finishing a session."""
        mode_label = {
            QuizMode.EXAM.value: "Kiểm tra",
            QuizMode.PRACTICE.value: "Luyện tập",
            QuizMode.STUDY.value: "Học tập",
        }.get(mode, mode)
        pct = (data.score / data.max_score * 100) if data.max_score else 0
        return (
            f"<b>Chế độ:</b> {mode_label}<br>"
            f"<b>Bài:</b> {data.quiz_title}<br>"
            f"<b>Điểm:</b> {data.score:.2f} / {data.max_score:.2f} ({pct:.1f}%)<br>"
            f"<b>Đúng:</b> {data.correct_count}  |  "
            f"<b>Sai:</b> {data.incorrect_count}  |  "
            f"<b>Bỏ qua:</b> {data.skipped_count}"
        )
