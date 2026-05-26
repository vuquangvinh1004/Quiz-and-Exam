"""Persistent JSON queue for failed Google Sheets submissions.

When a Google Sheets submission fails during exam submission, the pre-built
rows plus connection settings are saved here.  The user can retry later
from the ResultHistoryView without re-doing the entire submission flow.

File location: data/exports/gsheets_pending.json
Format: list of PendingItem dicts, persisted atomically via a temp-file swap.
"""
from __future__ import annotations

import json
import os
import tempfile
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from config.paths import EXPORTS_DIR
from core.utils.logger import get_logger

logger = get_logger(__name__)

_QUEUE_FILE: Path = EXPORTS_DIR / "gsheets_pending.json"


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class PendingItem:
    """One queued Google Sheets submission."""

    item_id: str                   # UUID
    queued_at: str                 # ISO-8601
    quiz_title: str
    submitter_name: str
    submitter_id: str
    score: float
    max_score: float
    gsheets_url: str
    gsheets_credentials_path: str
    rows: list[list]               # pre-built rows from GoogleSheetsSubmitter._build_rows


# ---------------------------------------------------------------------------
# Queue
# ---------------------------------------------------------------------------

class PendingGSheetsQueue:
    """Thread-safe read/write wrapper around the JSON queue file."""

    # ------------------------------------------------------------------ #
    # Read helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _load() -> list[dict]:
        if not _QUEUE_FILE.exists():
            return []
        try:
            data = json.loads(_QUEUE_FILE.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Failed to read pending queue: {exc}")
            return []

    @staticmethod
    def _save(items: list[dict]) -> None:
        EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
        # Atomic write via temp file
        fd, tmp = tempfile.mkstemp(dir=EXPORTS_DIR, suffix=".json.tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(items, f, ensure_ascii=False, indent=2)
            Path(tmp).replace(_QUEUE_FILE)
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def count(self) -> int:
        """Return number of pending items."""
        return len(self._load())

    def get_all(self) -> list[PendingItem]:
        """Return all pending items as PendingItem objects."""
        items = []
        for d in self._load():
            try:
                items.append(PendingItem(**d))
            except TypeError:
                pass  # skip malformed entries
        return items

    def push(
        self,
        *,
        quiz_title: str,
        submitter_name: str,
        submitter_id: str,
        score: float,
        max_score: float,
        gsheets_url: str,
        gsheets_credentials_path: str,
        rows: list[list],
    ) -> str:
        """Add a new pending item. Returns the new item_id."""
        item = PendingItem(
            item_id=str(uuid.uuid4()),
            queued_at=datetime.now(timezone.utc).isoformat(),
            quiz_title=quiz_title,
            submitter_name=submitter_name,
            submitter_id=submitter_id,
            score=score,
            max_score=max_score,
            gsheets_url=gsheets_url,
            gsheets_credentials_path=gsheets_credentials_path,
            rows=rows,
        )
        current = self._load()
        current.append(asdict(item))
        self._save(current)
        logger.info(f"Queued GSheets submission {item.item_id} for '{quiz_title}'")
        return item.item_id

    def remove(self, item_id: str) -> bool:
        """Remove item by id. Returns True if found and removed."""
        current = self._load()
        filtered = [d for d in current if d.get("item_id") != item_id]
        if len(filtered) == len(current):
            return False
        self._save(filtered)
        return True

    def retry_one(self, item_id: str) -> None:
        """Attempt to submit the queued item to Google Sheets.

        On success, removes the item from the queue.
        Raises on failure (caller is responsible for error handling).
        """
        current = self._load()
        match = next((d for d in current if d.get("item_id") == item_id), None)
        if match is None:
            raise ValueError(f"Pending item not found: {item_id}")

        item = PendingItem(**match)
        self._submit_rows(item)
        self.remove(item_id)
        logger.info(f"Successfully retried GSheets submission {item_id}")

    # ------------------------------------------------------------------ #
    # Internal submission helper
    # ------------------------------------------------------------------ #

    @staticmethod
    def _submit_rows(item: PendingItem) -> None:
        """Append pre-built rows to the spreadsheet."""
        import gspread
        from google.oauth2.service_account import Credentials

        from modules.google_sheets.submitter import (
            SHEET_HEADER,
            TARGET_WORKSHEET,
            GoogleSheetsSubmitter,
        )

        if not os.path.isfile(item.gsheets_credentials_path):
            raise FileNotFoundError(
                f"Không tìm thấy file credentials:\n{item.gsheets_credentials_path}"
            )

        creds = Credentials.from_service_account_file(
            item.gsheets_credentials_path,
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        gc = gspread.authorize(creds)

        try:
            sh = gc.open_by_url(item.gsheets_url.strip())
        except gspread.exceptions.SpreadsheetNotFound:
            raise gspread.exceptions.SpreadsheetNotFound(
                f"Không tìm thấy Google Sheet.\nURL: {item.gsheets_url}"
            )

        try:
            ws = sh.worksheet(TARGET_WORKSHEET)
        except gspread.exceptions.WorksheetNotFound:
            ws = sh.sheet1

        # Auto-create header if sheet is empty
        try:
            a1 = ws.acell("A1").value
        except Exception:
            a1 = None
        if not a1:
            GoogleSheetsSubmitter._retry_on_transient(
                lambda: ws.append_row(SHEET_HEADER, value_input_option="USER_ENTERED")
            )

        if item.rows:
            GoogleSheetsSubmitter._retry_on_transient(
                lambda: ws.append_rows(item.rows, value_input_option="USER_ENTERED")
            )
