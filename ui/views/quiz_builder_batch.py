"""Batch generation helper for QuizBuilderView.

Keeps heavy generation flow out of the view class to control file size/cognitive load.
"""
from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QMessageBox

from modules.quiz_builder.quota_allocator import (
    QuotaPlan,
    allocate_questions_for_plan,
    build_inventory,
    diagnose_quota_infeasibility,
    validate_quota_plan,
)
from modules.quiz_exporter.word_renderer import (
    ExportQuestionSnapshot,
    WordRenderer,
    build_output_path,
)


def run_batch_generation(view) -> None:
    bank_id = view._current_bank_id()
    if bank_id is None:
        QMessageBox.warning(view, "Thiếu thông tin", "Vui lòng chọn ngân hàng câu hỏi.")
        return

    if not view._selected_types():
        QMessageBox.warning(view, "Thiếu thông tin", "Chọn ít nhất một loại câu hỏi.")
        return

    if not view._selected_difficulties():
        QMessageBox.warning(view, "Thiếu thông tin", "Chọn ít nhất một mức độ khó.")
        return

    title_error = view._export_panel.validate_required_fields()
    if title_error:
        QMessageBox.warning(view, "Thiếu thông tin", title_error)
        return

    questions = view._eligible_questions()
    plan = QuotaPlan(
        total_questions=view._count_spin.value(),
        chapter_quota=view._quota_dict(view._chapter_spins),
        type_quota=view._quota_dict(view._type_spins),
        difficulty_quota=view._quota_dict(view._difficulty_spins),
    )

    inv = build_inventory(questions)
    validation = validate_quota_plan(plan, inv)
    view._refresh_quota_warnings(questions)
    if not validation.is_valid:
        QMessageBox.warning(
            view,
            "Quota không hợp lệ",
            "\n".join(validation.errors[:8]),
        )
        return

    output_dir = QFileDialog.getExistingDirectory(view, "Chọn thư mục lưu đề thi")
    if not output_dir:
        return

    renderer = WordRenderer()
    exam_count = view._exam_count_spin.value()
    no_repeat_between_exams = view._cb_no_repeat_between_exams.isChecked()
    generated_paths: list[Path] = []
    used_across_exams: set[int] = set()

    for exam_index in range(1, exam_count + 1):
        try:
            selected = allocate_questions_for_plan(
                questions,
                plan,
                excluded_question_ids=used_across_exams if no_repeat_between_exams else None,
            )
        except (RuntimeError, ValueError, TypeError, KeyError, AttributeError) as exc:
            QMessageBox.critical(
                view,
                "Lỗi tạo đề",
                f"Không thể phân bổ câu hỏi cho đề số {exam_index}:\n{exc}",
            )
            break

        if not selected:
            reason = " (do bật tùy chọn không lặp câu giữa các đề)." if no_repeat_between_exams else "."
            diagnostic = diagnose_quota_infeasibility(
                questions,
                plan,
                excluded_question_ids=used_across_exams if no_repeat_between_exams else None,
            )
            detail = "\n\nChi tiết:\n- " + "\n- ".join(diagnostic[:4]) if diagnostic else ""
            QMessageBox.warning(
                view,
                "Không thể tạo đủ đề",
                f"Không tìm được tổ hợp câu hỏi hợp lệ cho đề số {exam_index}{reason}{detail}",
            )
            break

        if no_repeat_between_exams:
            used_across_exams.update(q.id for q in selected)

        raw_snapshots = view._selector.build_snapshots(
            selected,
            shuffle_options=view._cb_shuffle_opts.isChecked(),
        )
        typed_snapshots = [ExportQuestionSnapshot.from_dict(s) for s in raw_snapshots]

        meta = view._export_panel.build_meta(duration_minutes=view._duration_spin.value())
        if exam_count > 1:
            meta.exam_title = f"{meta.exam_title} - Đề {exam_index}"
        render_config = view._export_panel.build_render_config()

        try:
            doc = renderer.render(typed_snapshots, meta, render_config)
        except (RuntimeError, ValueError, TypeError) as exc:
            QMessageBox.critical(
                view,
                "Lỗi render",
                f"Không thể render đề số {exam_index}:\n{exc}",
            )
            break

        output_path = build_output_path(
            f"{meta.exam_title}_De_{exam_index:02d}",
            Path(output_dir),
        )
        try:
            doc.save(output_path)
        except (OSError, PermissionError, FileNotFoundError) as exc:
            QMessageBox.critical(
                view,
                "Lỗi lưu file",
                f"Không thể lưu đề số {exam_index}:\n{exc}",
            )
            break
        generated_paths.append(output_path)

    if not generated_paths:
        return

    QMessageBox.information(
        view,
        "Hoàn tất",
        f"Đã tạo {len(generated_paths)} đề tại:\n{output_dir}",
    )
    if os.name == "nt":
        os.startfile(output_dir)
