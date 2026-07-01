"""Helpers for batch exam export packaging and naming."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from collections import Counter
from pathlib import Path
import re


@dataclass
class BatchExportPackage:
    """Represents a batch export package directory and file naming scheme."""

    package_dir: Path
    package_code: str

    def build_exam_path(self, exam_title: str, exam_index: int) -> Path:
        safe_title = _slug(exam_title) or "DeThi"
        return self.package_dir / f"{self.package_code}_DE_{exam_index:02d}_{safe_title}.docx"

    def build_answer_key_path(
        self,
        *,
        exam_index: int,
        policy: str = "suffix",
    ) -> Path:
        if policy == "prefix":
            name = f"DAP_AN_{self.package_code}_DE_{exam_index:02d}.docx"
        else:
            name = f"{self.package_code}_DE_{exam_index:02d}_DAP_AN.docx"
        return self.package_dir / name

    def write_manifest(self, *, exam_title: str, exam_count: int, note: str = "") -> Path:
        manifest_path = self.package_dir / f"{self.package_code}_README.txt"
        manifest_path.write_text(
            self.build_manifest_text(
                exam_title=exam_title,
                exam_count=exam_count,
                note=note,
            ),
            encoding="utf-8",
        )
        return manifest_path

    def build_manifest_text(
        self,
        *,
        exam_title: str,
        exam_count: int,
        note: str = "",
        planned_paths: list[Path] | None = None,
        section_lines: list[str] | None = None,
        print_profile_lines: list[str] | None = None,
        content_preview_lines: list[str] | None = None,
    ) -> str:
        lines = [
            f"Goi xuat de: {self.package_code}",
            f"Tieu de: {exam_title}",
            f"So de: {exam_count}",
            f"Thu muc dich: {self.package_dir}",
        ]
        if note.strip():
            lines.append(f"Ghi chu: {note.strip()}")
        if section_lines:
            lines.append("")
            lines.append("Noi dung in:")
            lines.extend(f"- {line}" for line in section_lines)
        if print_profile_lines:
            lines.append("")
            lines.append("Print profile:")
            lines.extend(f"- {line}" for line in print_profile_lines)
        if content_preview_lines:
            lines.append("")
            lines.append("Preview noi dung:")
            lines.extend(f"- {line}" for line in content_preview_lines)
        if planned_paths:
            lines.append("")
            lines.append("Danh sach file du kien:")
            lines.extend(f"- {path.name}" for path in planned_paths)
        return "\n".join(lines)

    def plan_document_paths(
        self,
        *,
        exam_title: str,
        exam_count: int,
        separate_answer_key: bool,
        answer_key_policy: str = "suffix",
    ) -> list[Path]:
        paths: list[Path] = []
        for exam_index in range(1, max(exam_count, 0) + 1):
            paths.append(self.build_exam_path(exam_title, exam_index))
            if separate_answer_key:
                paths.append(
                    self.build_answer_key_path(
                        exam_index=exam_index,
                        policy=answer_key_policy,
                    )
                )
        return paths

    @staticmethod
    def find_existing_conflicts(paths: list[Path]) -> list[Path]:
        return [path for path in paths if path.exists()]

    @staticmethod
    def find_duplicate_names(paths: list[Path]) -> list[str]:
        counts = Counter(path.name for path in paths)
        return sorted(name for name, count in counts.items() if count > 1)


def create_batch_export_package(
    *,
    root_dir: Path,
    exam_title: str,
    subject: str,
    course_code: str,
) -> BatchExportPackage:
    """Create a timestamped package directory for multi-exam export."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    title_part = _slug(exam_title) or "DeThi"
    subject_part = _slug(subject) or "MonHoc"
    course_part = _slug(course_code) or "GEN"
    package_code = f"{course_part}_{subject_part}_{title_part}_{timestamp}"
    package_dir = root_dir / package_code
    package_dir.mkdir(parents=True, exist_ok=True)
    return BatchExportPackage(package_dir=package_dir, package_code=package_code)


def _slug(value: str) -> str:
    compact = re.sub(r"\s+", "_", value.strip())
    return re.sub(r"[^A-Za-z0-9_-]+", "", compact)
