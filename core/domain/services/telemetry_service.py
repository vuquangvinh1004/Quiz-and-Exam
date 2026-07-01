"""Read lightweight telemetry summaries from application log files.

This service intentionally stays file-based so Phase 2 can improve
observability without introducing a new database table or migration.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re


@dataclass
class TelemetryWarningItem:
    timestamp: str
    level: str
    category: str
    event: str
    message: str


@dataclass
class TelemetryWarningSummary:
    import_warning_count: int = 0
    runtime_warning_count: int = 0
    total_warning_count: int = 0
    recent_items: list[TelemetryWarningItem] = field(default_factory=list)


class TelemetryService:
    """Parse recent app logs and aggregate warning-oriented telemetry."""

    _EVENT_RE = re.compile(r"\bevent=([A-Za-z0-9_]+)")
    _COUNT_RE = re.compile(r"\b(?P<key>warnings|errors)=(?P<value>\d+)")

    def load_warning_summary(
        self,
        log_dir: Path,
        *,
        max_items: int = 6,
        max_files: int = 3,
    ) -> TelemetryWarningSummary:
        summary = TelemetryWarningSummary()
        if not log_dir.exists():
            return summary

        items: list[TelemetryWarningItem] = []
        log_files = sorted(log_dir.glob("quiz_app_*.log"), reverse=True)[:max_files]
        for log_file in log_files:
            try:
                lines = log_file.read_text(encoding="utf-8").splitlines()
            except OSError:
                continue
            for line in reversed(lines):
                item = self._parse_warning_line(line)
                if item is None:
                    continue
                items.append(item)
                if item.category == "import":
                    summary.import_warning_count += 1
                elif item.category == "runtime":
                    summary.runtime_warning_count += 1

        summary.total_warning_count = (
            summary.import_warning_count + summary.runtime_warning_count
        )
        summary.recent_items = items[:max_items]
        return summary

    def _parse_warning_line(self, line: str) -> TelemetryWarningItem | None:
        if " – " not in line or " | " not in line:
            return None

        try:
            left, message = line.split(" – ", 1)
            timestamp, level, source = [part.strip() for part in left.split("|", 2)]
        except ValueError:
            return None

        category = self._categorize(level, source, message)
        if category is None:
            return None

        event = self._extract_event(message)
        return TelemetryWarningItem(
            timestamp=timestamp,
            level=level,
            category=category,
            event=event,
            message=message,
        )

    def _categorize(self, level: str, source: str, message: str) -> str | None:
        event = self._extract_event(message)
        if event.startswith("import_"):
            if level in {"WARNING", "ERROR"}:
                return "import"
            if event == "import_preview_completed":
                counts = self._extract_counts(message)
                if counts.get("warnings", 0) > 0 or counts.get("errors", 0) > 0:
                    return "import"
            return None

        if "quiz_runner_view" in source:
            if level in {"WARNING", "ERROR"}:
                return "runtime"
            if event in {"resume_invalid", "finalize_failed", "finalize_retry_ready"}:
                return "runtime"

        if event in {"resume_invalid", "finalize_failed", "finalize_retry_ready"}:
            return "runtime"
        return None

    def _extract_event(self, message: str) -> str:
        match = self._EVENT_RE.search(message)
        return match.group(1) if match else "generic"

    def _extract_counts(self, message: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for match in self._COUNT_RE.finditer(message):
            counts[match.group("key")] = int(match.group("value"))
        return counts
