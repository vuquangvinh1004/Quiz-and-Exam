"""Unit tests for batch export package naming helpers."""
from __future__ import annotations

import re

from modules.quiz_exporter.package_builder import create_batch_export_package


def test_create_batch_export_package_builds_timestamped_folder(tmp_path) -> None:
    package = create_batch_export_package(
        root_dir=tmp_path,
        exam_title="Giua ky",
        subject="Quan tri hoc",
        course_code="MGT101",
    )

    assert package.package_dir.exists()
    assert re.search(r"MGT101_Quan_tri_hoc_Giua_ky_\d{8}_\d{6}", package.package_dir.name)


def test_build_exam_path_uses_standard_print_naming(tmp_path) -> None:
    package = create_batch_export_package(
        root_dir=tmp_path,
        exam_title="Cuoi ky",
        subject="Ke toan",
        course_code="ACC201",
    )

    path = package.build_exam_path("Cuoi ky", 2)

    assert path.parent == package.package_dir
    assert path.name.startswith(f"{package.package_code}_DE_02_")
    assert path.suffix == ".docx"


def test_write_manifest_creates_readme(tmp_path) -> None:
    package = create_batch_export_package(
        root_dir=tmp_path,
        exam_title="Cuoi ky",
        subject="Ke toan",
        course_code="ACC201",
    )

    manifest = package.write_manifest(exam_title="Cuoi ky", exam_count=3, note="Batch test")

    text = manifest.read_text(encoding="utf-8")
    assert "So de: 3" in text
    assert "Batch test" in text


def test_build_answer_key_path_supports_prefix_policy(tmp_path) -> None:
    package = create_batch_export_package(
        root_dir=tmp_path,
        exam_title="Cuoi ky",
        subject="Ke toan",
        course_code="ACC201",
    )

    path = package.build_answer_key_path(exam_index=2, policy="prefix")

    assert path.name.startswith("DAP_AN_")
    assert path.suffix == ".docx"


def test_plan_document_paths_includes_exam_and_answer_key_files(tmp_path) -> None:
    package = create_batch_export_package(
        root_dir=tmp_path,
        exam_title="Giua ky",
        subject="Quan tri",
        course_code="MGT101",
    )

    paths = package.plan_document_paths(
        exam_title="Giua ky",
        exam_count=2,
        separate_answer_key=True,
        answer_key_policy="suffix",
    )

    assert len(paths) == 4
    assert any(path.name.endswith("_DAP_AN.docx") for path in paths)
    assert sum(1 for path in paths if "_DE_" in path.name) == 4


def test_find_existing_conflicts_and_duplicate_names(tmp_path) -> None:
    package = create_batch_export_package(
        root_dir=tmp_path,
        exam_title="Cuoi ky",
        subject="Ke toan",
        course_code="ACC201",
    )
    existing = package.build_exam_path("Cuoi ky", 1)
    existing.write_text("occupied", encoding="utf-8")
    duplicate_a = package.package_dir / "same.docx"
    duplicate_b = package.package_dir / "same.docx"
    unique = package.package_dir / "other.docx"

    conflicts = package.find_existing_conflicts([existing, unique])
    duplicate_names = package.find_duplicate_names([duplicate_a, duplicate_b, unique])

    assert conflicts == [existing]
    assert duplicate_names == ["same.docx"]


def test_build_manifest_text_supports_dry_run_details(tmp_path) -> None:
    package = create_batch_export_package(
        root_dir=tmp_path,
        exam_title="Cuoi ky",
        subject="Ke toan",
        course_code="ACC201",
    )
    planned = package.plan_document_paths(
        exam_title="Cuoi ky",
        exam_count=2,
        separate_answer_key=True,
        answer_key_policy="prefix",
    )

    text = package.build_manifest_text(
        exam_title="Cuoi ky",
        exam_count=2,
        note="Dry run",
        planned_paths=planned,
        section_lines=["Cover sheet: Co", "File dap an rieng: Co"],
        print_profile_lines=["Kho giay: A4"],
        content_preview_lines=["So de se render: 2"],
    )

    assert "Danh sach file du kien:" in text
    assert "Noi dung in:" in text
    assert "Print profile:" in text
    assert "Preview noi dung:" in text
    assert any(path.name in text for path in planned)
