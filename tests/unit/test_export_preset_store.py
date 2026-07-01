"""Unit tests for exam export preset storage."""
from __future__ import annotations

import json

import pytest

from modules.quiz_exporter.preset_store import ExportPreset, ExportPresetStore


def test_save_and_load_preset_roundtrip(tmp_path) -> None:
    store = ExportPresetStore(tmp_path / "presets")
    preset = ExportPreset(
        name="Giua ky Khoa QTKD",
        school="STU",
        department="Khoa QTKD",
        instructor="Nguyen Van A",
        subject="Quan tri hoc",
        course_code="MGT101",
        exam_title="Kiem tra giua ky",
        exam_type="Trắc nghiệm + Tự luận",
        numbering_mode="per_section",
        group_by_type=False,
        show_instructions=True,
        show_answer_sheet=False,
        show_scoring_rules=True,
        show_answer_key=False,
        show_question_points=True,
        show_question_statistics=True,
    )

    store.save_preset(preset)
    loaded = store.load_preset("Giua ky Khoa QTKD")

    assert loaded == preset


def test_list_presets_returns_display_names(tmp_path) -> None:
    store = ExportPresetStore(tmp_path / "presets")
    store.save_preset(ExportPreset(name="De 1"))
    store.save_preset(ExportPreset(name="De 2"))

    assert store.list_presets() == ["De 1", "De 2"]


def test_delete_preset_removes_file(tmp_path) -> None:
    store = ExportPresetStore(tmp_path / "presets")
    store.save_preset(ExportPreset(name="De 1"))

    assert store.delete_preset("De 1") is True
    assert store.list_presets() == []


def test_empty_name_is_rejected(tmp_path) -> None:
    store = ExportPresetStore(tmp_path / "presets")

    with pytest.raises(ValueError):
        store.save_preset(ExportPreset(name="  "))


def test_invalid_json_file_is_skipped_when_listing(tmp_path) -> None:
    presets_dir = tmp_path / "presets"
    presets_dir.mkdir(parents=True)
    (presets_dir / "broken.json").write_text("{not valid json", encoding="utf-8")
    (presets_dir / "good.json").write_text(
        json.dumps({"name": "De chuan"}, ensure_ascii=False),
        encoding="utf-8",
    )

    store = ExportPresetStore(presets_dir)

    assert store.list_presets() == ["De chuan"]


def test_resolve_default_prefers_bank_then_department_subject_then_global(tmp_path) -> None:
    store = ExportPresetStore(tmp_path / "presets")
    store.save_preset(
        ExportPreset(
            name="Default global",
            exam_title="Global",
            default_scope="global",
        )
    )
    store.save_preset(
        ExportPreset(
            name="Default khoa mon",
            exam_title="DeptSubject",
            default_scope="department_subject",
            default_department_key="khoa qtkd",
            default_subject_key="quan tri hoc",
        )
    )
    store.save_preset(
        ExportPreset(
            name="Default bank",
            exam_title="Bank",
            default_scope="bank",
            default_bank_id=7,
        )
    )

    bank = store.resolve_default_preset(bank_id=7, department="Khoa QTKD", subject="Quan tri hoc")
    assert bank is not None
    assert bank.exam_title == "Bank"

    dept_subject = store.resolve_default_preset(bank_id=8, department="Khoa QTKD", subject="Quan tri hoc")
    assert dept_subject is not None
    assert dept_subject.exam_title == "DeptSubject"

    global_default = store.resolve_default_preset(bank_id=8, department="Khac", subject="Khac")
    assert global_default is not None
    assert global_default.exam_title == "Global"
