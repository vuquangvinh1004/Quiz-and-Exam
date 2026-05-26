"""Architecture guardrails for UI layer boundaries.

Enforces that UI modules avoid direct SQLAlchemy usage and query-layer access.
"""
from __future__ import annotations

from pathlib import Path
import re


FORBIDDEN_PATTERNS = (
    "from sqlalchemy",
    "import sqlalchemy",
    "session.query(",
    "session.get(",
)


def test_ui_folder_has_no_direct_query_layer_usage() -> None:
    offenders: list[str] = []
    ui_root = Path("ui")

    for path in ui_root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_PATTERNS:
            if pattern in text:
                offenders.append(f"{path.as_posix()}: contains '{pattern}'")
                break

    assert not offenders, "\n".join(offenders)


def test_main_window_uses_public_refresh_protocol() -> None:
    """main_window must call view.refresh() not view._refresh()."""
    mw_path = Path("ui/main_window.py")
    text = mw_path.read_text(encoding="utf-8")
    assert "view._refresh(" not in text, (
        "main_window.py calls private view._refresh() — use the Refreshable protocol"
    )
    assert "hasattr(view, \"refresh\")" in text or "Refreshable" in text, (
        "main_window.py should check for public refresh() method"
    )


def test_all_views_expose_public_refresh_method() -> None:
    """Every *View class under ui/views must provide refresh()."""
    view_root = Path("ui/views")
    offenders: list[str] = []

    for path in view_root.glob("*_view.py"):
        text = path.read_text(encoding="utf-8")
        has_view_class = re.search(r"class\s+\w+View\s*\(", text) is not None
        has_refresh = "def refresh(self)" in text
        if has_view_class and not has_refresh:
            offenders.append(path.as_posix())

    assert not offenders, (
        "These views are missing public refresh() contract: "
        + ", ".join(offenders)
    )


def test_runner_pipeline_avoids_dict_style_snapshot_access() -> None:
    """Runner pipeline should use typed snapshot attributes, not qq["..."] access."""
    paths = [
        Path("ui/views/quiz_runner_view.py"),
        Path("modules/quiz_runner/session_controller.py"),
        Path("modules/quiz_runner/submit_handler.py"),
    ]
    offenders: list[str] = []

    for path in paths:
        text = path.read_text(encoding="utf-8")
        if 'qq["' in text or "qq['" in text or "qq.get(" in text:
            offenders.append(path.as_posix())

    assert not offenders, (
        "Runner typed contract regression (dict-style qq access): "
        + ", ".join(offenders)
    )


def test_builder_uses_typed_creation_snapshots_for_create_quiz() -> None:
    """QuizBuilder should call typed creation snapshot API before create_quiz."""
    path = Path("ui/views/quiz_builder_view.py")
    text = path.read_text(encoding="utf-8")
    assert "build_creation_snapshots(" in text, (
        "quiz_builder_view.py should use build_creation_snapshots() for typed contract"
    )


def test_export_panel_uses_typed_export_snapshots_for_renderer() -> None:
    """ExamExportPanel should adapt dict snapshots to typed export DTOs."""
    path = Path("ui/widgets/exam_export_panel.py")
    text = path.read_text(encoding="utf-8")
    assert "ExportQuestionSnapshot" in text, (
        "exam_export_panel.py should use ExportQuestionSnapshot typed DTO"
    )
    assert "from_dict(" in text and "renderer.render(typed_snapshots" in text, (
        "exam_export_panel.py should convert snapshots to typed_snapshots before render"
    )


def test_largest_view_file_under_500_lines() -> None:
    """Phase-4 KPI: largest view file should stay below 500 lines."""
    view_root = Path("ui/views")
    line_counts: list[tuple[str, int]] = []

    for path in view_root.glob("*_view.py"):
        lines = path.read_text(encoding="utf-8").splitlines()
        line_counts.append((path.as_posix(), len(lines)))

    worst = max(line_counts, key=lambda x: x[1])
    assert worst[1] < 500, (
        f"Largest view is too big: {worst[0]} has {worst[1]} lines (target < 500)"
    )


def test_ui_broad_exception_count_is_controlled() -> None:
    """Phase-4 KPI: keep broad `except Exception` usage bounded in UI layer."""
    ui_root = Path("ui")
    broad_count = 0
    for path in ui_root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        broad_count += text.count("except Exception")

    assert broad_count <= 42, (
        f"UI has too many broad catches: {broad_count} (expected <= 42)"
    )


def test_import_ui_uses_facade_instead_of_direct_session() -> None:
    """Sprint-C guardrail: import UI should not open DB sessions directly."""
    paths = [
        Path("ui/views/import_view.py"),
        Path("ui/dialogs/import_preview_dialog.py"),
    ]
    offenders: list[str] = []

    for path in paths:
        text = path.read_text(encoding="utf-8")
        if "get_session(" in text:
            offenders.append(path.as_posix())

    assert not offenders, (
        "Import UI must use ImportFacade instead of direct get_session(): "
        + ", ".join(offenders)
    )


def test_settings_and_question_bank_ui_use_facade_instead_of_direct_session() -> None:
    """Sprint-C guardrail: migrated settings/question-bank UI files must not open sessions directly."""
    paths = [
        Path("ui/views/settings_view.py"),
        Path("ui/views/question_bank_view.py"),
        Path("ui/dialogs/question_editor_dialog.py"),
    ]
    offenders: list[str] = []

    for path in paths:
        text = path.read_text(encoding="utf-8")
        if "get_session(" in text:
            offenders.append(path.as_posix())

    assert not offenders, (
        "Migrated settings/question-bank UI must use facades instead of direct get_session(): "
        + ", ".join(offenders)
    )


def test_dashboard_and_submission_dialog_ui_use_facade_instead_of_direct_session() -> None:
    """Sprint-C guardrail: dashboard/submission settings UI files must not open sessions directly."""
    paths = [
        Path("ui/views/dashboard_view.py"),
        Path("ui/dialogs/submission_settings_dialog.py"),
    ]
    offenders: list[str] = []

    for path in paths:
        text = path.read_text(encoding="utf-8")
        if "get_session(" in text:
            offenders.append(path.as_posix())

    assert not offenders, (
        "Migrated dashboard/submission settings UI must use facades instead of direct get_session(): "
        + ", ".join(offenders)
    )
