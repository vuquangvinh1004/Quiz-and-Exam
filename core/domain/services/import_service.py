"""Orchestration service for the import pipeline.

Workflow:
    1. preview(file_path, session) → ParseResult
       - Parses the file
       - Detects in-file duplicates
       - Detects DB duplicates (result enriched with issues, no write)

    2. commit(parse_result, bank_id, session) → ImportSummary
       - MUST only be called when not parse_result.has_errors
       - Writes questions + options in a single DB transaction (managed by
         the caller's session / get_session context manager)
       - Skips rows that the DB-duplicate detector flagged as ERROR

ARCHITECTURE NOTE:
    Business logic lives here, not in the UI dialog. The dialog only calls
    preview() and commit(), processes ImportSummary for display.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy.orm import Session

from core.database.models import Question, QuestionOption
from core.utils.constants import QuestionType
from core.utils.exceptions import ImportValidationError
from core.utils.logger import get_logger
from modules.question_bank.duplicate_detector import DuplicateDetector
from modules.question_bank.importer import (
    ParseResult,
    ParsedQuestion,
    QuestionFileParser,
)


# ---------------------------------------------------------------------------
# Return types
# ---------------------------------------------------------------------------

@dataclass
class ImportSummary:
    """Summary returned after a successful commit()."""
    inserted: int = 0
    skipped_rows: list[int] = field(default_factory=list)  # row numbers skipped


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class ImportService:
    """Preview and commit question import operations."""

    def __init__(
        self,
        *,
        parser: QuestionFileParser | None = None,
        dedup: DuplicateDetector | None = None,
        commit_batch_size: int = 200,
    ) -> None:
        self._parser = parser or QuestionFileParser()
        self._dedup = dedup or DuplicateDetector()
        self._commit_batch_size = commit_batch_size
        self._logger = get_logger(__name__)

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def preview(self, file_path: Path, session: Session) -> ParseResult:
        """Parse *file_path* and enrich result with duplicate findings.

        Does NOT write anything to the database.
        """
        self._logger.info(f"event=import_preview_started file={file_path.name}")
        result = self._parser.parse_file(file_path)

        # Run duplicate checks even when the file already has parse errors,
        # so the user sees the full picture in the preview dialog.
        in_file_issues = self._dedup.detect_in_file(result.parsed_questions)
        result.issues.extend(in_file_issues)

        db_issues = self._dedup.detect_against_db(result.parsed_questions, session)
        result.issues.extend(db_issues)

        # Keep issues sorted by row number for easier reading
        result.issues.sort(key=lambda i: (i.row, i.severity))
        self._logger.info(
            "event=import_preview_completed file=%s total_rows=%s parsed=%s errors=%s warnings=%s infos=%s"
            % (
                file_path.name,
                result.total_rows,
                len(result.parsed_questions),
                result.error_count,
                result.warning_count,
                result.info_count,
            )
        )
        return result

    def commit(
        self, parse_result: ParseResult, bank_id: int, session: Session
    ) -> ImportSummary:
        """Write valid parsed questions to the database.

        Raises ImportValidationError if *parse_result* still contains ERROR-level issues
        that are not the DB-duplicate kind (those are skipped silently because
        they existed before commit was called; the UI enforces the guard).

        The caller is responsible for the session transaction
        (commit / rollback). Typically called inside a `get_session()` block.
        """
        if parse_result.has_errors:
            errors = [
                {
                    "row": issue.row,
                    "severity": issue.severity,
                    "message": issue.message,
                }
                for issue in parse_result.issues
                if issue.severity == "ERROR"
            ]
            self._logger.warning(
                "event=import_commit_blocked errors=%s total_rows=%s"
                % (len(errors), parse_result.total_rows)
            )
            raise ImportValidationError(errors)

        # Rows flagged as DB-duplicates (ERROR) must be skipped
        skip_rows: set[int] = {
            issue.row
            for issue in parse_result.issues
            if issue.severity == "ERROR"
            and "cơ sở dữ liệu" in issue.message
        }

        inserted = 0
        for pq in parse_result.parsed_questions:
            if pq.row_number in skip_rows:
                continue

            question = _build_question(pq, bank_id)
            correct_answer_keys = {a.upper() for a in pq.correct_answers}

            # MC / MA / TF: persist answer options
            if pq.question_type in (
                QuestionType.MULTIPLE_CHOICE,
                QuestionType.MULTIPLE_ANSWER,
                QuestionType.TRUE_FALSE,
            ):
                for sort_idx, (label, text) in enumerate(pq.options.items()):
                    opt = QuestionOption(
                        option_key=label.upper(),
                        option_text=text,
                        is_correct=label.upper() in correct_answer_keys,
                        sort_order=sort_idx,
                    )
                    question.options.append(opt)

            session.add(question)

            inserted += 1
            if inserted % self._commit_batch_size == 0:
                session.flush()
                self._logger.info(
                    "event=import_commit_batch_flushed inserted=%s batch_size=%s"
                    % (inserted, self._commit_batch_size)
                )

        session.flush()
        self._logger.info(
            "event=import_commit_completed inserted=%s skipped=%s batch_size=%s"
            % (inserted, len(skip_rows), self._commit_batch_size)
        )

        return ImportSummary(
            inserted=inserted,
            skipped_rows=sorted(skip_rows),
        )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _build_question(pq: ParsedQuestion, bank_id: int) -> Question:
    """Map a ParsedQuestion to a Question ORM instance (without options)."""
    q = Question(
        bank_id=bank_id,
        question_code=pq.question_code,
        question_type=pq.question_type.value,
        content=pq.question_text,
        hint=pq.hint,
        explanation=pq.explanation,
        difficulty=pq.difficulty,
        category=pq.category,
        tags=", ".join(pq.tags) if pq.tags else None,
        point_value=pq.score,
        case_sensitive=pq.case_sensitive,
        trim_whitespace=pq.trim_whitespace,
        is_active=(pq.status == "active"),
    )
    # BLANK / SA / ES store accepted answers as a JSON list
    if pq.question_type in (
        QuestionType.BLANK,
        QuestionType.SHORT_ANSWER,
        QuestionType.ESSAY,
    ):
        q.accepted_answers = json.dumps(pq.correct_answers, ensure_ascii=False)
    return q
