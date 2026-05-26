"""Quiz Exporter module.

Provides WordRenderer for generating .docx exam documents from
question snapshots and exam metadata. No DB access in this module.
"""
from modules.quiz_exporter.word_renderer import ExportConfig, WordRenderer

__all__ = ["WordRenderer", "ExportConfig"]
