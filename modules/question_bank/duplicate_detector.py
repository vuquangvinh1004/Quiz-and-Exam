"""Duplicate detection for import rows: within-file and against the DB.

Rules (QUIZ_APP_IMPORT_FORMAT.md §8):
  In-file:
    - Duplicate question_code            → ERROR
    - Duplicate (question_text, type)    → WARNING

  Against DB (v1.0 import-only, no upsert):
    - question_code already in DB        → ERROR (row blocked)
    - (question_text, type) already in DB → WARNING (user decides)
"""
from __future__ import annotations

from modules.question_bank.importer import ImportIssue, ParsedQuestion


class DuplicateDetector:
    """Detect duplicate questions within a parsed file and against the DB."""

    # -----------------------------------------------------------------------
    # In-file duplicate detection
    # -----------------------------------------------------------------------

    def detect_in_file(self, rows: list[ParsedQuestion]) -> list[ImportIssue]:
        """Return issues for duplicates found within *rows*."""
        issues: list[ImportIssue] = []
        seen_codes: dict[str, int] = {}          # code → first row_number
        seen_texts: dict[tuple[str, str], int] = {}  # (text, type) → first row_number

        for row in rows:
            if row.question_code:
                key = row.question_code.strip()
                if key in seen_codes:
                    issues.append(ImportIssue(
                        row=row.row_number,
                        severity="ERROR",
                        column="question_code",
                        message=(
                            f"question_code '{key}' bị trùng với dòng "
                            f"{seen_codes[key]} trong file."
                        ),
                    ))
                else:
                    seen_codes[key] = row.row_number

            text_key = (row.question_text.strip(), row.question_type.value)
            if text_key in seen_texts:
                issues.append(ImportIssue(
                    row=row.row_number,
                    severity="WARNING",
                    column="question_text",
                    message=(
                        f"question_text và question_type trùng với dòng "
                        f"{seen_texts[text_key]} trong cùng file."
                    ),
                ))
            else:
                seen_texts[text_key] = row.row_number

        return issues

    # -----------------------------------------------------------------------
    # DB duplicate detection
    # -----------------------------------------------------------------------

    def detect_against_db(
        self, rows: list[ParsedQuestion], session
    ) -> list[ImportIssue]:
        """Return issues for rows that collide with existing DB questions.

        Performs two single queries (codes, texts) rather than N per-row
        queries.
        """
        from core.database.models import Question

        issues: list[ImportIssue] = []

        # Load existing questions in one pass
        existing = (
            session.query(
                Question.question_code,
                Question.content,
                Question.question_type,
            ).all()
        )

        db_codes: set[str] = set()
        db_texts: set[tuple[str, str]] = set()
        for q_code, q_text, q_type in existing:
            if q_code:
                db_codes.add(q_code.strip())
            db_texts.add((q_text.strip(), q_type))

        for row in rows:
            if row.question_code and row.question_code.strip() in db_codes:
                issues.append(ImportIssue(
                    row=row.row_number,
                    severity="ERROR",
                    column="question_code",
                    message=(
                        f"question_code '{row.question_code}' đã tồn tại trong "
                        "cơ sở dữ liệu. v1.0 không hỗ trợ cập nhật; dòng này "
                        "sẽ bị chặn."
                    ),
                ))
            elif (row.question_text.strip(), row.question_type.value) in db_texts:
                issues.append(ImportIssue(
                    row=row.row_number,
                    severity="WARNING",
                    column="question_text",
                    message=(
                        "question_text và question_type trùng với câu hỏi đã "
                        "có trong cơ sở dữ liệu."
                    ),
                ))

        return issues
