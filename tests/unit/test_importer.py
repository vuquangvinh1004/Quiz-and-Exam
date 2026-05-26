"""Unit tests for the question import parser, validator and duplicate detector.

Covers QUIZ_APP_IMPORT_FORMAT.md requirements:
  - All four question types (MC, MA, BLANK, SA)
  - Required column validation
  - Per-type correct_answers rules
  - Boolean normalisation
  - Default value injection (score, difficulty, status)
  - BOM handling for CSV
  - Duplicate detection (in-file and against DB)
  - Edge cases: blank rows, extra columns, wrong types, multi-delimiter answers
"""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import pytest

from modules.question_bank.importer import (
    ParseResult,
    ParsedQuestion,
    QuestionFileParser,
    _parse_bool,
)
from modules.question_bank.duplicate_detector import DuplicateDetector
from core.utils.constants import QuestionType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_csv(rows: list[dict], bom: bool = False) -> bytes:
    """Build CSV bytes from a list of row dicts (all with the same keys)."""
    if not rows:
        header = (
            "question_code,question_text,question_type,category,difficulty,score,"
            "hint,explanation,option_a,option_b,option_c,option_d,option_e,option_f,"
            "correct_answers,status,tags,case_sensitive,trim_whitespace"
        )
        content = header + "\n"
    else:
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
        content = buf.getvalue()
    enc = "utf-8-sig" if bom else "utf-8"
    return content.encode(enc)


def _base_mc_row(**overrides) -> dict:
    row = {
        "question_code": "MC001",
        "question_text": "Thủ đô của Việt Nam là gì?",
        "question_type": "multiple_choice",
        "category": "Địa lý",
        "difficulty": "easy",
        "score": "1",
        "hint": "",
        "explanation": "",
        "option_a": "Hà Nội",
        "option_b": "Hồ Chí Minh",
        "option_c": "Đà Nẵng",
        "option_d": "",
        "option_e": "",
        "option_f": "",
        "correct_answers": "A",
        "status": "active",
        "tags": "",
        "case_sensitive": "false",
        "trim_whitespace": "true",
    }
    row.update(overrides)
    return row


def _base_ma_row(**overrides) -> dict:
    row = {
        "question_code": "MA001",
        "question_text": "Ngôn ngữ nào là thông dịch?",
        "question_type": "multiple_answer",
        "category": "",
        "difficulty": "medium",
        "score": "1.5",
        "hint": "",
        "explanation": "",
        "option_a": "Python",
        "option_b": "Java",
        "option_c": "C++",
        "option_d": "JavaScript",
        "option_e": "",
        "option_f": "",
        "correct_answers": "A||D",
        "status": "active",
        "tags": "",
        "case_sensitive": "false",
        "trim_whitespace": "true",
    }
    row.update(overrides)
    return row


def _base_blank_row(**overrides) -> dict:
    row = {
        "question_code": "BL001",
        "question_text": "Thủ đô của Việt Nam là [[blank]].",
        "question_type": "blank",
        "category": "",
        "difficulty": "easy",
        "score": "1",
        "hint": "",
        "explanation": "",
        "option_a": "",
        "option_b": "",
        "option_c": "",
        "option_d": "",
        "option_e": "",
        "option_f": "",
        "correct_answers": "Hà Nội||Ha Noi",
        "status": "active",
        "tags": "",
        "case_sensitive": "false",
        "trim_whitespace": "true",
    }
    row.update(overrides)
    return row


def _base_sa_row(**overrides) -> dict:
    row = {
        "question_code": "SA001",
        "question_text": "EOQ viết tắt của từ gì?",
        "question_type": "short_answer",
        "category": "",
        "difficulty": "easy",
        "score": "1",
        "hint": "",
        "explanation": "",
        "option_a": "",
        "option_b": "",
        "option_c": "",
        "option_d": "",
        "option_e": "",
        "option_f": "",
        "correct_answers": "Economic Order Quantity||EOQ",
        "status": "active",
        "tags": "",
        "case_sensitive": "false",
        "trim_whitespace": "true",
    }
    row.update(overrides)
    return row


@pytest.fixture
def parser() -> QuestionFileParser:
    return QuestionFileParser()


@pytest.fixture
def detector() -> DuplicateDetector:
    return DuplicateDetector()


def _write_csv(tmp_path: Path, rows: list[dict], bom: bool = False) -> Path:
    p = tmp_path / "test_import.csv"
    p.write_bytes(_make_csv(rows, bom=bom))
    return p


# ===========================================================================
# 1. Valid rows – all four question types
# ===========================================================================

class TestValidRows:

    def test_mc_parses_correctly(self, parser, tmp_path):
        p = _write_csv(tmp_path, [_base_mc_row()])
        result = parser.parse_file(p)
        assert not result.has_errors
        assert len(result.parsed_questions) == 1
        q = result.parsed_questions[0]
        assert q.question_type == QuestionType.MULTIPLE_CHOICE
        assert q.question_code == "MC001"
        assert q.correct_answers == ["A"]
        assert q.options["A"] == "Hà Nội"
        assert q.score == 1.0
        assert q.difficulty == "easy"
        assert q.status == "active"
        assert q.case_sensitive is False
        assert q.trim_whitespace is True

    def test_ma_parses_correctly(self, parser, tmp_path):
        p = _write_csv(tmp_path, [_base_ma_row()])
        result = parser.parse_file(p)
        assert not result.has_errors
        q = result.parsed_questions[0]
        assert q.question_type == QuestionType.MULTIPLE_ANSWER
        assert q.correct_answers == ["A", "D"]
        assert len(q.options) >= 4

    def test_blank_parses_correctly(self, parser, tmp_path):
        p = _write_csv(tmp_path, [_base_blank_row()])
        result = parser.parse_file(p)
        assert not result.has_errors
        q = result.parsed_questions[0]
        assert q.question_type == QuestionType.BLANK
        assert "Hà Nội" in q.correct_answers
        assert "Ha Noi" in q.correct_answers
        assert not q.options  # blank: no options expected

    def test_sa_parses_correctly(self, parser, tmp_path):
        p = _write_csv(tmp_path, [_base_sa_row()])
        result = parser.parse_file(p)
        assert not result.has_errors
        q = result.parsed_questions[0]
        assert q.question_type == QuestionType.SHORT_ANSWER
        assert "EOQ" in q.correct_answers

    def test_multiple_rows_all_valid(self, parser, tmp_path):
        rows = [_base_mc_row(), _base_ma_row(), _base_blank_row(), _base_sa_row()]
        p = _write_csv(tmp_path, rows)
        result = parser.parse_file(p)
        assert not result.has_errors
        assert len(result.parsed_questions) == 4


# ===========================================================================
# 2. Default injection
# ===========================================================================

class TestDefaultInjection:

    def test_empty_score_uses_default_and_info(self, parser, tmp_path):
        p = _write_csv(tmp_path, [_base_mc_row(score="")])
        result = parser.parse_file(p)
        assert not result.has_errors
        assert result.parsed_questions[0].score == 1.0
        infos = [i for i in result.issues if i.severity == "INFO"]
        assert any("score" in i.column.lower() for i in infos)

    def test_empty_difficulty_uses_default(self, parser, tmp_path):
        p = _write_csv(tmp_path, [_base_mc_row(difficulty="")])
        result = parser.parse_file(p)
        assert not result.has_errors
        assert result.parsed_questions[0].difficulty == "medium"

    def test_empty_status_uses_default(self, parser, tmp_path):
        p = _write_csv(tmp_path, [_base_mc_row(status="")])
        result = parser.parse_file(p)
        assert not result.has_errors
        assert result.parsed_questions[0].status == "active"


# ===========================================================================
# 3. Header validation errors
# ===========================================================================

class TestHeaderValidation:

    def _csv_without_col(self, tmp_path, drop_col):
        row = _base_mc_row()
        del row[drop_col]
        p = tmp_path / "test.csv"
        p.write_bytes(_make_csv([row]))
        return p

    def test_missing_question_text_column_is_error(self, parser, tmp_path):
        p = self._csv_without_col(tmp_path, "question_text")
        result = parser.parse_file(p)
        assert result.has_errors
        msgs = [i.message for i in result.issues if i.severity == "ERROR"]
        assert any("question_text" in m for m in msgs)

    def test_missing_question_type_column_is_error(self, parser, tmp_path):
        p = self._csv_without_col(tmp_path, "question_type")
        result = parser.parse_file(p)
        assert result.has_errors

    def test_missing_correct_answers_column_is_error(self, parser, tmp_path):
        p = self._csv_without_col(tmp_path, "correct_answers")
        result = parser.parse_file(p)
        assert result.has_errors

    def test_duplicate_header_is_error(self, parser, tmp_path):
        content = (
            "question_text,question_type,question_text,correct_answers\n"
            "Some text,multiple_choice,dup,A\n"
        )
        p = tmp_path / "dup_header.csv"
        p.write_bytes(content.encode("utf-8"))
        result = parser.parse_file(p)
        assert result.has_errors
        assert any("trùng" in i.message for i in result.issues)


# ===========================================================================
# 4. Row-level validation errors
# ===========================================================================

class TestRowValidation:

    def test_empty_question_text_is_error(self, parser, tmp_path):
        p = _write_csv(tmp_path, [_base_mc_row(question_text="")])
        result = parser.parse_file(p)
        assert result.has_errors

    def test_unknown_question_type_is_error(self, parser, tmp_path):
        p = _write_csv(tmp_path, [_base_mc_row(question_type="essay")])
        result = parser.parse_file(p)
        assert result.has_errors

    def test_empty_correct_answers_is_error(self, parser, tmp_path):
        p = _write_csv(tmp_path, [_base_mc_row(correct_answers="")])
        result = parser.parse_file(p)
        assert result.has_errors

    def test_negative_score_is_error(self, parser, tmp_path):
        p = _write_csv(tmp_path, [_base_mc_row(score="-1")])
        result = parser.parse_file(p)
        assert result.has_errors

    def test_non_numeric_score_is_error(self, parser, tmp_path):
        p = _write_csv(tmp_path, [_base_mc_row(score="abc")])
        result = parser.parse_file(p)
        assert result.has_errors

    def test_invalid_difficulty_is_error(self, parser, tmp_path):
        p = _write_csv(tmp_path, [_base_mc_row(difficulty="extreme")])
        result = parser.parse_file(p)
        assert result.has_errors

    def test_invalid_status_is_error(self, parser, tmp_path):
        p = _write_csv(tmp_path, [_base_mc_row(status="pending")])
        result = parser.parse_file(p)
        assert result.has_errors

    def test_invalid_boolean_is_error(self, parser, tmp_path):
        p = _write_csv(tmp_path, [_base_mc_row(case_sensitive="maybe")])
        result = parser.parse_file(p)
        assert result.has_errors


# ===========================================================================
# 5. MC-specific validation
# ===========================================================================

class TestMCValidation:

    def test_mc_less_than_two_options_is_error(self, parser, tmp_path):
        row = _base_mc_row(option_b="", option_c="", option_d="")
        p = _write_csv(tmp_path, [row])
        result = parser.parse_file(p)
        assert result.has_errors

    def test_mc_two_correct_answers_is_error(self, parser, tmp_path):
        p = _write_csv(tmp_path, [_base_mc_row(correct_answers="A||B")])
        result = parser.parse_file(p)
        assert result.has_errors
        assert any(
            "exactly 1" in i.message or "1 correct" in i.message
            for i in result.issues if i.severity == "ERROR"
        )

    def test_mc_nonexistent_option_in_answer_is_error(self, parser, tmp_path):
        # Only options A, B, C defined; answer references E
        p = _write_csv(tmp_path, [_base_mc_row(correct_answers="E")])
        result = parser.parse_file(p)
        assert result.has_errors

    def test_mc_with_blank_placeholder_is_error(self, parser, tmp_path):
        p = _write_csv(
            tmp_path,
            [_base_mc_row(question_text="Fill [[blank]] here.")],
        )
        result = parser.parse_file(p)
        assert result.has_errors


# ===========================================================================
# 6. MA-specific validation
# ===========================================================================

class TestMAValidation:

    def test_ma_one_correct_answer_is_error(self, parser, tmp_path):
        p = _write_csv(tmp_path, [_base_ma_row(correct_answers="A")])
        result = parser.parse_file(p)
        assert result.has_errors

    def test_ma_duplicate_answer_is_error(self, parser, tmp_path):
        p = _write_csv(tmp_path, [_base_ma_row(correct_answers="A||A")])
        result = parser.parse_file(p)
        assert result.has_errors

    def test_ma_nonexistent_option_is_error(self, parser, tmp_path):
        p = _write_csv(tmp_path, [_base_ma_row(correct_answers="A||G")])
        result = parser.parse_file(p)
        assert result.has_errors


# ===========================================================================
# 7. BLANK-specific validation
# ===========================================================================

class TestBlankValidation:

    def test_blank_missing_placeholder_is_error(self, parser, tmp_path):
        p = _write_csv(
            tmp_path,
            [_base_blank_row(question_text="No placeholder here.")],
        )
        result = parser.parse_file(p)
        assert result.has_errors

    def test_blank_multiple_placeholders_is_allowed(self, parser, tmp_path):
        """Multiple placeholders in one BLANK question are accepted."""
        p = _write_csv(
            tmp_path,
            [_base_blank_row(question_text="[[blank]] and [[blank]]")],
        )
        result = parser.parse_file(p)
        assert not result.has_errors

    def test_blank_legacy_placeholder_is_allowed_with_warning(self, parser, tmp_path):
        p = _write_csv(
            tmp_path,
            [_base_blank_row(question_text="Thủ đô là ________.")],
        )
        result = parser.parse_file(p)
        assert not result.has_errors
        assert any(
            i.severity == "WARNING" and "placeholder legacy" in i.message
            for i in result.issues
        )

    def test_blank_with_options_produces_warning(self, parser, tmp_path):
        row = _base_blank_row(option_a="some option")
        p = _write_csv(tmp_path, [row])
        result = parser.parse_file(p)
        assert not result.has_errors
        assert any(i.severity == "WARNING" for i in result.issues)

    def test_blank_correct_answers_multi_value(self, parser, tmp_path):
        row = _base_blank_row(correct_answers="Hà Nội||Ha Noi||HANOI")
        p = _write_csv(tmp_path, [row])
        result = parser.parse_file(p)
        assert not result.has_errors
        assert len(result.parsed_questions[0].correct_answers) == 3


# ===========================================================================
# 8. SA-specific validation
# ===========================================================================

class TestSAValidation:

    def test_sa_with_blank_placeholder_is_error(self, parser, tmp_path):
        p = _write_csv(
            tmp_path,
            [_base_sa_row(question_text="Fill the [[blank]].")],
        )
        result = parser.parse_file(p)
        assert result.has_errors

    def test_sa_with_options_produces_warning(self, parser, tmp_path):
        row = _base_sa_row(option_a="unexpected")
        p = _write_csv(tmp_path, [row])
        result = parser.parse_file(p)
        assert not result.has_errors
        assert any(i.severity == "WARNING" for i in result.issues)


# ===========================================================================
# 9. Boolean normalisation
# ===========================================================================

class TestBoolNormalisation:

    @pytest.mark.parametrize("raw,expected", [
        ("true", True), ("TRUE", True), ("1", True), ("yes", True), ("y", True),
        ("false", False), ("FALSE", False), ("0", False), ("no", False), ("n", False),
        ("", False),   # default for case_sensitive
    ])
    def test_bool_values(self, raw, expected):
        val, err = _parse_bool(raw, default=False)
        assert val is expected
        assert err is None

    def test_invalid_bool_returns_error_message(self):
        _, err = _parse_bool("maybe", default=False)
        assert err is not None
        assert "maybe" in err

    def test_trim_whitespace_default_true(self, parser, tmp_path):
        row = _base_mc_row(trim_whitespace="")
        p = _write_csv(tmp_path, [row])
        result = parser.parse_file(p)
        assert not result.has_errors
        assert result.parsed_questions[0].trim_whitespace is True


# ===========================================================================
# 10. CSV encoding – UTF-8 BOM
# ===========================================================================

class TestCSVEncoding:

    def test_utf8_bom_csv_parsed_correctly(self, parser, tmp_path):
        p = _write_csv(tmp_path, [_base_mc_row()], bom=True)
        result = parser.parse_file(p)
        assert not result.has_errors
        assert len(result.parsed_questions) == 1

    def test_utf8_no_bom_csv_parsed_correctly(self, parser, tmp_path):
        p = _write_csv(tmp_path, [_base_mc_row()], bom=False)
        result = parser.parse_file(p)
        assert not result.has_errors


# ===========================================================================
# 11. Unsupported file extension
# ===========================================================================

class TestUnsupportedFormat:

    def test_json_extension_produces_error(self, parser, tmp_path):
        p = tmp_path / "data.json"
        p.write_text("{}")
        result = parser.parse_file(p)
        assert result.has_errors
        assert any("json" in i.message.lower() for i in result.issues)


# ===========================================================================
# 12. Blank row skipping
# ===========================================================================

class TestBlankRowSkipping:

    def test_blank_rows_skipped(self, parser, tmp_path):
        rows = [_base_mc_row(), _base_mc_row(question_code="", question_text="",
                                              question_type="", correct_answers="")]
        p = _write_csv(tmp_path, rows)
        result = parser.parse_file(p)
        assert not result.has_errors
        # Only the valid row should be in parsed_questions
        assert len(result.parsed_questions) == 1


# ===========================================================================
# 13. Tags parsing
# ===========================================================================

class TestTagsParsing:

    def test_tags_split_by_comma(self, parser, tmp_path):
        p = _write_csv(tmp_path, [_base_mc_row(tags="địa lý,country,easy")])
        result = parser.parse_file(p)
        assert not result.has_errors
        assert result.parsed_questions[0].tags == ["địa lý", "country", "easy"]

    def test_empty_tags_gives_empty_list(self, parser, tmp_path):
        p = _write_csv(tmp_path, [_base_mc_row(tags="")])
        result = parser.parse_file(p)
        assert result.parsed_questions[0].tags == []


# ===========================================================================
# 14. In-file duplicate detection
# ===========================================================================

class TestInFileDuplicates:

    def _make_parsed(self, row_num, code, text, qtype) -> ParsedQuestion:
        return ParsedQuestion(
            row_number=row_num,
            question_code=code,
            question_text=text,
            question_type=qtype,
            category=None,
            difficulty="medium",
            score=1.0,
            hint=None,
            explanation=None,
            options={},
            correct_answers=["A"],
            status="active",
            tags=[],
            case_sensitive=False,
            trim_whitespace=True,
        )

    def test_duplicate_code_is_error(self, detector):
        rows = [
            self._make_parsed(1, "CODE1", "Q1", QuestionType.MULTIPLE_CHOICE),
            self._make_parsed(2, "CODE1", "Q2", QuestionType.MULTIPLE_CHOICE),
        ]
        issues = detector.detect_in_file(rows)
        assert any(i.severity == "ERROR" and "CODE1" in i.message for i in issues)

    def test_duplicate_text_and_type_is_warning(self, detector):
        rows = [
            self._make_parsed(1, "C1", "Same text", QuestionType.MULTIPLE_CHOICE),
            self._make_parsed(2, "C2", "Same text", QuestionType.MULTIPLE_CHOICE),
        ]
        issues = detector.detect_in_file(rows)
        assert any(
            i.severity == "WARNING" and "trùng" in i.message for i in issues
        )

    def test_same_text_different_type_no_warning(self, detector):
        rows = [
            self._make_parsed(1, "C1", "Same text", QuestionType.MULTIPLE_CHOICE),
            self._make_parsed(2, "C2", "Same text", QuestionType.SHORT_ANSWER),
        ]
        issues = detector.detect_in_file(rows)
        # Different types → no WARNING for text duplication with itself
        assert not any(
            i.severity == "WARNING" and "question_text" in i.column for i in issues
        )

    def test_no_duplicates_returns_empty(self, detector):
        rows = [
            self._make_parsed(1, "C1", "Q1", QuestionType.MULTIPLE_CHOICE),
            self._make_parsed(2, "C2", "Q2", QuestionType.BLANK),
        ]
        assert detector.detect_in_file(rows) == []


# ===========================================================================
# 15. DB duplicate detection
# ===========================================================================

class TestDBDuplicates:

    def _make_parsed(self, row_num, code, text, qtype):
        return ParsedQuestion(
            row_number=row_num,
            question_code=code,
            question_text=text,
            question_type=qtype,
            category=None,
            difficulty="medium",
            score=1.0,
            hint=None,
            explanation=None,
            options={},
            correct_answers=["A"],
            status="active",
            tags=[],
            case_sensitive=False,
            trim_whitespace=True,
        )

    def test_code_in_db_is_error(self, detector, db_session):
        from core.database.models import Question, QuestionBank
        bank = QuestionBank(name="TestBank")
        db_session.add(bank)
        db_session.flush()
        q = Question(
            bank_id=bank.id,
            question_code="EXISTING",
            question_type="MC",
            content="Existing question",
        )
        db_session.add(q)
        db_session.flush()

        rows = [self._make_parsed(1, "EXISTING", "New text", QuestionType.MULTIPLE_CHOICE)]
        issues = detector.detect_against_db(rows, db_session)
        assert any(i.severity == "ERROR" for i in issues)

    def test_text_in_db_is_warning(self, detector, db_session):
        from core.database.models import Question, QuestionBank
        bank = QuestionBank(name="TestBank2")
        db_session.add(bank)
        db_session.flush()
        q = Question(
            bank_id=bank.id,
            question_code="DIFF_CODE",
            question_type="MC",
            content="Duplicate content",
        )
        db_session.add(q)
        db_session.flush()

        rows = [self._make_parsed(1, "NEW_CODE", "Duplicate content", QuestionType.MULTIPLE_CHOICE)]
        issues = detector.detect_against_db(rows, db_session)
        assert any(i.severity == "WARNING" for i in issues)

    def test_no_db_rows_returns_empty(self, detector, db_session):
        rows = [self._make_parsed(1, "UNIQUE", "New question", QuestionType.BLANK)]
        issues = detector.detect_against_db(rows, db_session)
        assert issues == []


# ===========================================================================
# 16. ParseResult aggregation properties
# ===========================================================================

class TestParseResultProperties:

    def test_has_errors_true_when_error_present(self):
        from modules.question_bank.importer import ImportIssue
        result = ParseResult()
        result.issues.append(ImportIssue(row=1, severity="ERROR", message="err"))
        assert result.has_errors

    def test_has_errors_false_when_only_warnings(self):
        from modules.question_bank.importer import ImportIssue
        result = ParseResult()
        result.issues.append(ImportIssue(row=1, severity="WARNING", message="warn"))
        assert not result.has_errors

    def test_error_count(self):
        from modules.question_bank.importer import ImportIssue
        result = ParseResult()
        result.issues = [
            ImportIssue(row=1, severity="ERROR", message="e1"),
            ImportIssue(row=2, severity="WARNING", message="w1"),
            ImportIssue(row=3, severity="ERROR", message="e2"),
        ]
        assert result.error_count == 2
        assert result.warning_count == 1
