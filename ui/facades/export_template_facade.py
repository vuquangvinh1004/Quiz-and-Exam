"""Facade for export preset/template workflows used by UI."""
from __future__ import annotations

from config.paths import TEMPLATES_DIR
from modules.quiz_exporter.preset_store import ExportPreset, ExportPresetStore


class ExportTemplateFacade:
    """Centralize export preset storage outside UI widgets."""

    def __init__(self) -> None:
        self._store = ExportPresetStore(TEMPLATES_DIR / "exam_export_presets")

    def list_preset_names(self) -> list[str]:
        return self._store.list_presets()

    def save_preset(self, preset: ExportPreset) -> None:
        self._store.save_preset(preset)

    def load_preset(self, name: str) -> ExportPreset:
        return self._store.load_preset(name)

    def delete_preset(self, name: str) -> bool:
        return self._store.delete_preset(name)

    def resolve_default_preset(
        self,
        *,
        bank_id: int | None,
        department: str,
        subject: str,
    ) -> ExportPreset | None:
        return self._store.resolve_default_preset(
            bank_id=bank_id,
            department=department,
            subject=subject,
        )
