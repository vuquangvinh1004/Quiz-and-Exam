"""Google Sheets submission module.

Appends quiz attempt results to a pre-existing Google Sheets spreadsheet
using a Service Account for authentication.

Sheet format
------------
Flat table — one row per question per submission.  All students' submissions
accumulate in the same worksheet so the teacher can filter/pivot by name or
Mã số.

The first row of the target worksheet is treated as the header.
If the sheet is empty the header row is written automatically on the first
submission.  Subsequent submissions always call ``append_rows`` (server-side),
which is safe for concurrent writes from multiple students.

Concurrency note
----------------
``append_rows`` (Sheets API *append* endpoint) is server-side: Google itself
determines "the first empty row after the last data row" at the moment it
processes the request.  Thirty students submitting simultaneously each issue
one ``append_rows`` call; Google serialises them correctly with no row
collisions.

Security note
-------------
``credentials_path`` must point to a Service Account JSON key downloaded from
Google Cloud Console.  Only share the key with administrators / teachers who
set up the application, never with end-users (students).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from modules.grading.result_builder import AttemptResultData

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

SHEET_HEADER: list[str] = [
    "Thời gian nộp",
    "Họ và tên",
    "Mã số",
    "Bài kiểm tra",
    "Tổng điểm",
    "Điểm tối đa",
    "Số câu đúng",
    "Số câu sai",
    "Số bỏ qua",
    "Thời gian làm bài (giây)",
    "STT câu",
    "Mã câu hỏi",
    "Nội dung câu hỏi",
    "Đáp án học sinh",
    "Đáp án đúng",
    "Kết quả",
    "Điểm câu",
    "Điểm tối đa câu",
]

# Name of the worksheet to write into.
# The teacher should create a sheet with this name (or rename the first sheet).
# If not found, the first sheet is used as fallback.
TARGET_WORKSHEET = "Kết quả"


# ---------------------------------------------------------------------------
# Submitter
# ---------------------------------------------------------------------------

class GoogleSheetsSubmitter:
    """Appends one attempt's results to a Google Sheets spreadsheet.

    All methods are instance methods for testability (mock-friendly), but
    the class holds no mutable state — it is safe to instantiate once and
    reuse across calls.
    """

    def submit(
        self,
        data: AttemptResultData,
        spreadsheet_url: str,
        credentials_path: str,
    ) -> None:
        """Append all question rows for *data* to the spreadsheet.

        Parameters
        ----------
        data:
            Fully populated ``AttemptResultData`` from the grading pipeline.
        spreadsheet_url:
            Full URL of the Google Sheets file, e.g.
            ``https://docs.google.com/spreadsheets/d/SHEET_ID/edit``.
        credentials_path:
            Absolute path to the Service Account JSON key file.

        Raises
        ------
        FileNotFoundError
            If *credentials_path* does not exist.
        ValueError
            If *spreadsheet_url* or *credentials_path* is empty.
        gspread.exceptions.SpreadsheetNotFound
            If the URL is invalid or the sheet is not shared with the SA.
        gspread.exceptions.APIError
            On unexpected Sheets API errors.
        """
        import gspread
        from google.oauth2.service_account import Credentials

        if not spreadsheet_url.strip():
            raise ValueError("URL Google Sheet không được để trống.")
        if not credentials_path.strip():
            raise ValueError("Đường dẫn file credentials chưa được cấu hình.")

        import os
        if not os.path.isfile(credentials_path):
            raise FileNotFoundError(
                f"Không tìm thấy file credentials:\n{credentials_path}\n\n"
                "Vui lòng kiểm tra cài đặt Google Sheets."
            )

        creds = Credentials.from_service_account_file(
            credentials_path, scopes=_SCOPES
        )
        gc = gspread.authorize(creds)

        try:
            sh = gc.open_by_url(spreadsheet_url.strip())
        except gspread.exceptions.SpreadsheetNotFound:
            raise gspread.exceptions.SpreadsheetNotFound(
                "Không tìm thấy Google Sheet.\n\n"
                "Kiểm tra:\n"
                "  1. URL có đúng không?\n"
                "  2. Sheet đã được chia sẻ với email của Service Account chưa?\n"
                "     (email trong file credentials.json, trường 'client_email')"
            ) from None

        # Resolve target worksheet
        ws = self._get_worksheet(sh)

        # Auto-create header if sheet is empty
        try:
            a1_value = ws.acell("A1").value
        except Exception:
            a1_value = None
        if not a1_value:
            self._retry_on_transient(
                lambda: ws.append_row(SHEET_HEADER, value_input_option="USER_ENTERED")
            )

        # Build and append data rows (one per question)
        rows = self._build_rows(data)
        if rows:
            self._retry_on_transient(
                lambda: ws.append_rows(rows, value_input_option="USER_ENTERED")
            )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _retry_on_transient(fn, max_retries: int = 3) -> None:
        """Call fn(), retrying on transient network/rate-limit errors.

        Retried HTTP status codes: 429 (rate limit), 500, 502, 503, 504.
        Network-layer errors (ConnectionError, TimeoutError, OSError) are
        also retried.  Other exceptions propagate immediately.

        Backoff: 1 s → 2 s → 4 s (exponential, base 2).
        """
        import time

        import gspread

        last_exc: BaseException = RuntimeError("no attempts made")
        for attempt in range(max_retries):
            try:
                fn()
                return
            except gspread.exceptions.APIError as exc:
                status = (
                    exc.response.status_code
                    if hasattr(exc, "response") and exc.response is not None
                    else 0
                )
                if status in (429, 500, 502, 503, 504):
                    last_exc = exc
                    time.sleep(2 ** attempt)
                    continue
                raise
            except (ConnectionError, TimeoutError, OSError) as exc:
                last_exc = exc
                time.sleep(2 ** attempt)
                continue
        raise last_exc

    @staticmethod
    def _get_worksheet(sh):  # type: ignore[no-untyped-def]
        """Return TARGET_WORKSHEET if it exists, else the first sheet."""
        import gspread
        try:
            return sh.worksheet(TARGET_WORKSHEET)
        except gspread.exceptions.WorksheetNotFound:
            return sh.sheet1

    @staticmethod
    def _build_rows(data: AttemptResultData) -> list[list]:
        """Convert AttemptResultData into a list of cell rows."""
        ts = data.submitted_at.strftime("%d/%m/%Y %H:%M:%S")
        rows: list[list] = []
        for q in data.questions:
            result_text = (
                "Đúng" if q.is_correct is True
                else "Sai" if q.is_correct is False
                else "Bỏ qua"
            )
            rows.append([
                ts,
                data.submitter_name,
                data.submitter_id,
                data.quiz_title,
                round(data.score, 4),
                round(data.max_score, 4),
                data.correct_count,
                data.incorrect_count,
                data.skipped_count,
                data.duration_seconds,
                q.order,
                q.question_code or "",
                q.question_text,
                q.answer_text,
                q.correct_answer_display,
                result_text,
                round(q.score_awarded, 4),
                round(q.max_score, 4),
            ])
        return rows
