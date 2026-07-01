from __future__ import annotations

from core.domain.services.telemetry_service import TelemetryService


def test_load_warning_summary_returns_zero_when_log_dir_missing(tmp_path) -> None:
    svc = TelemetryService()

    summary = svc.load_warning_summary(tmp_path / "missing")

    assert summary.total_warning_count == 0
    assert summary.recent_items == []


def test_load_warning_summary_counts_import_and_runtime_events(tmp_path) -> None:
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    (log_dir / "quiz_app_2026-06-30.log").write_text(
        "\n".join(
            [
                "2026-06-30 15:00:00 | WARNING  | modules.question_bank.importer:295 – event=import_file_size_warning path=big.csv size=4000000 soft_limit=3145728",
                "2026-06-30 15:00:01 | INFO     | core.domain.services.import_service:91 – event=import_preview_completed file=warn.csv total_rows=12001 parsed=12001 errors=0 warnings=1 infos=0",
                "2026-06-30 15:00:02 | INFO     | ui.views.quiz_runner_view:85 – event=resume_invalid attempt_id=15 mode=EXAM remaining=120 has_submitter=False",
                "2026-06-30 15:00:03 | ERROR    | ui.views.quiz_runner_view:472 – finalize_attempt failed: db locked",
            ]
        ),
        encoding="utf-8",
    )

    svc = TelemetryService()
    summary = svc.load_warning_summary(log_dir)

    assert summary.import_warning_count == 2
    assert summary.runtime_warning_count == 2
    assert summary.total_warning_count == 4
    assert len(summary.recent_items) == 4
    assert any(item.event == "import_file_size_warning" for item in summary.recent_items)
    assert any(item.category == "runtime" for item in summary.recent_items)


def test_load_warning_summary_reads_newest_files_first(tmp_path) -> None:
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    (log_dir / "quiz_app_2026-06-29.log").write_text(
        "2026-06-29 10:00:00 | WARNING  | modules.question_bank.importer:250 – event=import_row_limit_exceeded rows=30001 hard_limit=30000\n",
        encoding="utf-8",
    )
    (log_dir / "quiz_app_2026-06-30.log").write_text(
        "2026-06-30 11:00:00 | WARNING  | ui.views.quiz_runner_view:383 – Autosave failed: db down\n",
        encoding="utf-8",
    )

    svc = TelemetryService()
    summary = svc.load_warning_summary(log_dir, max_items=2, max_files=2)

    assert summary.recent_items[0].timestamp == "2026-06-30 11:00:00"
    assert summary.recent_items[1].timestamp == "2026-06-29 10:00:00"
