"""File-based store for exam export presets."""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class ExportPreset:
    """Serializable export/print preset for exam document generation."""

    name: str
    school: str = ""
    department: str = ""
    instructor: str = ""
    subject: str = ""
    course_code: str = ""
    exam_title: str = ""
    exam_type: str = "Trắc nghiệm"
    numbering_mode: str = "global"
    group_by_type: bool = True
    show_instructions: bool = True
    show_answer_sheet: bool = True
    show_scoring_rules: bool = True
    show_answer_key: bool = True
    show_question_points: bool = False
    show_question_statistics: bool = False
    show_cover_sheet: bool = False
    split_answer_key_file: bool = False
    raw_latex_answer_key: bool = False
    watermark_text: str = ""
    watermark_preset: str = "custom"
    cover_sheet_template: str = "standard"
    answer_key_naming_policy: str = "suffix"
    page_size: str = "A4"
    top_margin_cm: float = 1.5
    bottom_margin_cm: float = 1.5
    left_margin_cm: float = 2.0
    right_margin_cm: float = 1.5
    show_student_info_block: bool = True
    default_scope: str = "manual"  # manual | global | bank | department_subject
    default_bank_id: int | None = None
    default_bank_name: str = ""
    default_department_key: str = ""
    default_subject_key: str = ""


class ExportPresetStore:
    """Manage user-defined export presets as JSON files."""

    def __init__(self, presets_dir: Path) -> None:
        self._presets_dir = presets_dir

    def list_presets(self) -> list[str]:
        self._presets_dir.mkdir(parents=True, exist_ok=True)
        names: list[str] = []
        for path in sorted(self._presets_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            preset_name = str(data.get("name") or path.stem).strip()
            if preset_name:
                names.append(preset_name)
        return names

    def save_preset(self, preset: ExportPreset) -> Path:
        name = preset.name.strip()
        if not name:
            raise ValueError("Preset name must not be empty.")

        self._presets_dir.mkdir(parents=True, exist_ok=True)
        path = self._path_for_name(name)
        path.write_text(
            json.dumps(asdict(preset), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return path

    def load_preset(self, name: str) -> ExportPreset:
        path = self._path_for_name(name)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ValueError(f"Preset not found: {name}") from exc
        except json.JSONDecodeError as exc:
            raise ValueError(f"Preset file is invalid JSON: {name}") from exc
        return ExportPreset(**data)

    def delete_preset(self, name: str) -> bool:
        path = self._path_for_name(name)
        if not path.exists():
            return False
        path.unlink()
        return True

    def resolve_default_preset(
        self,
        *,
        bank_id: int | None,
        department: str,
        subject: str,
    ) -> ExportPreset | None:
        presets = self._load_all_presets()
        dep_key = self._normalize_key(department)
        subject_key = self._normalize_key(subject)

        for preset in presets:
            if preset.default_scope == "bank" and bank_id is not None and preset.default_bank_id == bank_id:
                return preset

        for preset in presets:
            if (
                preset.default_scope == "department_subject"
                and preset.default_department_key == dep_key
                and preset.default_subject_key == subject_key
                and dep_key
                and subject_key
            ):
                return preset

        for preset in presets:
            if preset.default_scope == "global":
                return preset

        return None

    def _path_for_name(self, name: str) -> Path:
        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", name.strip()).strip("._")
        if not safe_name:
            raise ValueError("Preset name is invalid.")
        return self._presets_dir / f"{safe_name}.json"

    def _load_all_presets(self) -> list[ExportPreset]:
        self._presets_dir.mkdir(parents=True, exist_ok=True)
        presets: list[ExportPreset] = []
        for path in sorted(self._presets_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                presets.append(ExportPreset(**data))
            except (OSError, json.JSONDecodeError, TypeError):
                continue
        return presets

    @staticmethod
    def _normalize_key(value: str) -> str:
        return " ".join(value.strip().lower().split())
