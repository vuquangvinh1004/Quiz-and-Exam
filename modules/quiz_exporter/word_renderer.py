"""Word document renderer for exam export.

Accepts a list of typed export snapshots (or legacy dict snapshots)
plus exam metadata, and generates
a clean .docx exam document ready for printing.

No database access occurs here. All data must be supplied by the caller.

Supported question types: MC, MA, BLANK, SA

Generated sections (each controlled by ExportConfig):
    1. Exam header (school, department, subject, title, etc.)
    2. Instructions
    3. Question body (grouped per section A/B/C/D or flat)
    4. Answer sheet
    5. Scoring rules
    6. Answer key and score table
"""
from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Pt, Cm, RGBColor, Inches

# ---------------------------------------------------------------------------
# Public data classes
# ---------------------------------------------------------------------------

@dataclass
class ExamMeta:
    """Metadata for the exam header."""
    school: str = ""
    department: str = ""
    instructor: str = ""
    subject: str = ""
    course_code: str = ""
    exam_title: str = "BÀI KIỂM TRA"
    exam_type: str = ""
    duration_minutes: int = 0
    note: str = ""


@dataclass
class ExportConfig:
    """Controls which optional sections to include in the export."""
    show_instructions: bool = True
    show_answer_sheet: bool = True
    show_answer_key: bool = True
    show_scoring_rules: bool = True
    # "global" = continuous numbering across all questions
    # "per_section" = restart numbering in each section
    numbering_mode: str = "global"
    # "grouped" = separate Part A/B/C/D by question type
    # "flat"    = all questions in one list
    group_by_type: bool = True
    # essay questions appended as last section
    # each dict: {"number": int, "score": float}
    essay_questions: list[dict] = field(default_factory=list)


@dataclass
class ExportQuestionSnapshot:
    """Typed snapshot payload used by WordRenderer export flow."""

    type: str
    content: str
    point_value: float = 1.0
    hint: str = ""
    explanation: str = ""
    options: list = field(default_factory=list)
    accepted_answers: Optional[list] = None

    @classmethod
    def from_dict(cls, data: dict) -> "ExportQuestionSnapshot":
        return cls(
            type=data.get("type", "MC"),
            content=data.get("content", ""),
            point_value=data.get("point_value", 1.0),
            hint=data.get("hint") or "",
            explanation=data.get("explanation") or "",
            options=data.get("options") or [],
            accepted_answers=data.get("accepted_answers"),
        )

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "content": self.content,
            "point_value": self.point_value,
            "hint": self.hint,
            "explanation": self.explanation,
            "options": self.options,
            "accepted_answers": self.accepted_answers,
        }


# Internal type → display label mapping
_TYPE_LABELS: dict[str, str] = {
    "MC": "Multiple Choice",
    "MA": "Multiple Answer",
    "BLANK": "Điền khuyết",
    "SA": "Trả lời ngắn",
}

_SECTION_LETTERS = "ABCDEFGH"

# Instructions text per question type
_INSTRUCTIONS: dict[str, str] = {
    "MC": (
        "Câu hỏi trắc nghiệm một đáp án (Multiple Choice): "
        "Chọn MỘT đáp án đúng nhất bằng cách khoanh tròn vào chữ cái tương ứng."
    ),
    "MA": (
        "Câu hỏi trắc nghiệm nhiều đáp án (Multiple Answer): "
        "Chọn TẤT CẢ các đáp án đúng bằng cách khoanh tròn hoặc đánh dấu vào chữ cái tương ứng."
    ),
    "BLANK": (
        "Câu điền khuyết (Blank): "
        "Điền từ hoặc cụm từ thích hợp vào chỗ trống trong câu."
    ),
    "SA": (
        "Câu trả lời ngắn (Short Answer): "
        "Trả lời ngắn gọn, rõ ràng vào phần dành sẵn bên dưới mỗi câu."
    ),
}

# ---------------------------------------------------------------------------
# Main renderer class
# ---------------------------------------------------------------------------

class WordRenderer:
    """Renders a list of question snapshots into a .docx exam document.

    Usage::

        renderer = WordRenderer()
        doc = renderer.render(questions, meta, config)
        doc.save("exam.docx")

    Parameters
    ----------
    questions:
        List of snapshot dicts as produced by
        ``QuestionSelector.build_snapshots()``.  Each dict must have at
        minimum the keys: ``type``, ``content``, ``point_value``.
        MC/MA also need ``options`` (list of ``{key, text, is_correct}``).
        BLANK/SA also need ``accepted_answers`` (list[str]).
    meta:
        ``ExamMeta`` instance with header information.
    config:
        ``ExportConfig`` instance controlling optional sections.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def render(
        self,
        questions: list[ExportQuestionSnapshot | dict],
        meta: ExamMeta,
        config: ExportConfig,
    ) -> Document:
        """Build and return a ``docx.Document`` object.

        The caller is responsible for saving the document to disk.
        """
        normalized_questions = self._normalize_questions(questions)

        doc = Document()
        self._set_default_font(doc, "Times New Roman")
        self._set_page_margins(doc)

        self._render_header(doc, meta)

        if config.show_instructions:
            self._render_instructions(doc, normalized_questions)

        grouped = self._group_questions(normalized_questions, config)
        self._render_questions(doc, grouped, config)

        if config.essay_questions:
            essay_letter_idx = len(grouped) if config.group_by_type else 0
            essay_letter = (
                _SECTION_LETTERS[essay_letter_idx]
                if essay_letter_idx < len(_SECTION_LETTERS)
                else ""
            )
            self._render_essay_section(doc, config.essay_questions, essay_letter)

        if config.show_answer_sheet or config.show_scoring_rules or config.show_answer_key:
            # Close the question section — SECTIONPAGES in the header will reflect
            # only question pages, not the supplementary pages that follow.
            self._add_next_page_section_break(doc)
            # Supplementary section must not show any page-number header.
            self._clear_supplementary_header(doc)
            first_supp = True

            if config.show_answer_sheet:
                if not first_supp:
                    doc.add_page_break()
                first_supp = False
                self._render_answer_sheet(doc, grouped, config)

            if config.show_scoring_rules:
                if not first_supp:
                    doc.add_page_break()
                first_supp = False
                self._render_scoring_rules(doc, normalized_questions, config)

            if config.show_answer_key:
                if not first_supp:
                    doc.add_page_break()
                self._render_answer_key(doc, grouped, config)

        return doc

    @staticmethod
    def _normalize_questions(
        questions: list[ExportQuestionSnapshot | dict],
    ) -> list[dict]:
        """Convert typed snapshots to legacy dict shape for renderer internals."""
        normalized: list[dict] = []
        for q in questions:
            if isinstance(q, ExportQuestionSnapshot):
                normalized.append(q.to_dict())
            else:
                normalized.append(q)
        return normalized

    # ------------------------------------------------------------------
    # Page setup
    # ------------------------------------------------------------------

    def _set_page_margins(self, doc: Document) -> None:
        section = doc.sections[0]
        section.top_margin = Cm(1.5)
        section.bottom_margin = Cm(1.5)
        section.left_margin = Cm(2.0)
        section.right_margin = Cm(1.5)
    def _set_default_font(self, doc: Document, font_name: str) -> None:
        """Apply *font_name* as the document-wide default for all runs.

        Sets both the 'Normal' paragraph style (which most styles inherit from)
        and the low-level ``w:docDefaults`` XML element so that runs without an
        explicit font also pick up the correct typeface.
        """
        # 1. Normal style – all paragraph styles inherit from this
        doc.styles["Normal"].font.name = font_name
        doc.styles["Normal"].font.size = Pt(12)

        # 2. Document-level rPrDefault – catches runs that bypass style inheritance
        styles_el = doc.styles.element
        docDefaults = styles_el.find(qn("w:docDefaults"))
        if docDefaults is None:
            return
        rPrDefault = docDefaults.find(qn("w:rPrDefault"))
        if rPrDefault is None:
            return
        rPr = rPrDefault.find(qn("w:rPr"))
        if rPr is None:
            rPr = OxmlElement("w:rPr")
            rPrDefault.append(rPr)
        # Remove any existing rFonts element before inserting
        for existing in rPr.findall(qn("w:rFonts")):
            rPr.remove(existing)
        rFonts = OxmlElement("w:rFonts")
        rFonts.set(qn("w:ascii"), font_name)
        rFonts.set(qn("w:hAnsi"), font_name)
        rFonts.set(qn("w:cs"), font_name)
        rPr.insert(0, rFonts)
        for existing in rPr.findall(qn("w:sz")):
            rPr.remove(existing)
        for existing in rPr.findall(qn("w:szCs")):
            rPr.remove(existing)
        sz = OxmlElement("w:sz")
        sz.set(qn("w:val"), "24")
        sz_cs = OxmlElement("w:szCs")
        sz_cs.set(qn("w:val"), "24")
        rPr.append(sz)
        rPr.append(sz_cs)
    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------

    def _render_header(self, doc: Document, meta: ExamMeta) -> None:
        """Header matching the Vietnamese standard exam template.

        Layout::

            [Word page header: Trang X / Y, top right]

            [Borderless 2-col info table]
            TRƯỜNG...          | BÀI KIỂM TRA GIỮA KỲ
            Khoa/Đơn vị...     | Môn học (Mã HP)
            Cán bộ giảng dạy.. | Hình thức: ... – Thời lượng: __ phút

            [Bordered 2-col student table]
            | Thông tin của sinh viên   | Chữ ký của sinh viên |
            | Họ & tên: ____________    |                      |
            | MSSV: __ Lớp: __ STT: __ |                      |

            Lưu ý: <meta.note>
        """
        # ── Page number in Word built-in header (top right) ──────────────
        self._set_page_number_header(doc)

        # ── Info block (borderless 2-column table) ───────────────────────
        INFO_LEFT_CM = 9.5
        INFO_RIGHT_CM = 9.5
        info_tbl = doc.add_table(rows=1, cols=2)
        self._clear_table_borders(info_tbl)
        L = info_tbl.cell(0, 0)
        R = info_tbl.cell(0, 1)
        self._set_cell_width(L, INFO_LEFT_CM)
        self._set_cell_width(R, INFO_RIGHT_CM)

        # Left cell: school → department → instructor
        lp = L.paragraphs[0]
        lp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if meta.school:
            r = lp.add_run(meta.school.upper())
            r.bold = True
            r.font.size = Pt(13)
        if meta.department:
            p = L.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(meta.department)
            r.bold = True
            r.font.size = Pt(13)
        if meta.instructor:
            p = L.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(f"Cán bộ giảng dạy: {meta.instructor}")
            r.italic = True
            r.font.size = Pt(12)

        # Right cell: title → subject/code → format/duration
        rp = R.paragraphs[0]
        rp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if meta.exam_title:
            r = rp.add_run(meta.exam_title.upper())
            r.bold = True
            r.font.size = Pt(13)
        if meta.subject or meta.course_code:
            parts = [meta.subject] if meta.subject else []
            if meta.course_code:
                parts.append(f"({meta.course_code})")
            p = R.add_paragraph(" ".join(parts))
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.runs[0].bold = True
            p.runs[0].font.size = Pt(12)
        fmt_line = self._build_format_duration_line(meta)
        if fmt_line:
            p = R.add_paragraph(fmt_line)
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.runs[0].font.size = Pt(12)

        doc.add_paragraph("")  # gap

        # ── Student info table (bordered) ────────────────────────────────
        STU_LEFT_CM = 12.5
        STU_RIGHT_CM = 9.5
        stu_tbl = doc.add_table(rows=3, cols=2)
        stu_tbl.style = "Table Grid"
        for row in stu_tbl.rows:
            self._set_cell_width(row.cells[0], STU_LEFT_CM)
            self._set_cell_width(row.cells[1], STU_RIGHT_CM)

        # Row 0: column headers
        p = stu_tbl.cell(0, 0).paragraphs[0]
        r = p.add_run("Thông tin của sinh viên")
        r.bold = True
        r.font.size = Pt(12)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER

        p = stu_tbl.cell(0, 1).paragraphs[0]
        r = p.add_run("Chữ ký của sinh viên")
        r.bold = True
        r.font.size = Pt(12)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # Row 1: full name
        p = stu_tbl.cell(1, 0).paragraphs[0]
        p.add_run("Họ & tên:  " + "_" * 44)
        p.runs[0].font.size = Pt(12)
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(6)

        # Row 2: student-ID / class / order
        p = stu_tbl.cell(2, 0).paragraphs[0]
        p.add_run("MSSV:  " + "_" * 16 + "   Lớp:  " + "_" * 10 + "   STT:  " + "_" * 3)
        p.runs[0].font.size = Pt(12)
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(6)

        # Merge right column rows 1+2 → signature area
        stu_tbl.cell(1, 1).merge(stu_tbl.cell(2, 1))

        # Hide the internal horizontal border between "Họ & tên" and "MSSV…" rows
        # (only in the left column — right column is already merged)
        self._hide_cell_border(stu_tbl.cell(1, 0), "bottom")
        self._hide_cell_border(stu_tbl.cell(2, 0), "top")

        # ── Note paragraph ───────────────────────────────────────────────
        doc.add_paragraph("")
        if meta.note:
            p = doc.add_paragraph()
            r1 = p.add_run("Lưu ý: ")
            r1.bold = True
            r1.font.size = Pt(12)
            r2 = p.add_run(meta.note)
            r2.font.size = Pt(12)
        doc.add_paragraph("")  # spacer before section body

    # ------------------------------------------------------------------
    # Header helpers
    # ------------------------------------------------------------------

    def _set_page_number_header(self, doc: Document) -> None:
        """Insert 'Trang X / Y' page-number field in the Word document header (top right)."""
        header = doc.sections[0].header
        p = header.paragraphs[0] if header.paragraphs else header.add_paragraph()
        p.clear()
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT

        run = p.add_run("Trang ")
        run.font.size = Pt(12)
        self._add_field_code(p, "PAGE")
        run2 = p.add_run(" / ")
        run2.font.size = Pt(12)
        self._add_field_code(p, "SECTIONPAGES")

    def _clear_supplementary_header(self, doc: Document) -> None:
        """Give the supplementary section a blank, independent header (no page numbers).

        After ``_add_next_page_section_break`` deep-copies ``sectPr``, both the
        question section (inline sectPr) and the supplementary section (body
        sectPr) share the **same** header relationship ID.  We must give the
        supplementary section its own new empty header part so Word does not
        inherit the question-section page-number header on those pages.

        ``Section.header_is_linked_to_previous`` does NOT exist in
        python-docx 1.2.0 — using that attribute would be a silent no-op.
        Instead we:
        1. Create a fresh empty header part via ``doc.part.add_header_part()``.
        2. Replace the ``<w:headerReference r:id>`` in the body sectPr with the
           new rId, leaving the inline sectPr's original rId untouched.
        """
        R_ID = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
        # Create a new empty header part and register it in doc.part relationships
        _empty_hdr_part, new_rId = doc.part.add_header_part()

        # The supplementary section is always the body's final sectPr (sections[-1])
        supp_sectPr = doc.sections[-1]._sectPr

        # Replace every existing headerReference in the supplementary sectPr
        for href in supp_sectPr.findall(qn("w:headerReference")):
            supp_sectPr.remove(href)

        href_el = OxmlElement("w:headerReference")
        href_el.set(qn("w:type"), "default")
        href_el.set(R_ID, new_rId)
        supp_sectPr.append(href_el)

    def _add_field_code(self, paragraph, field_name: str) -> None:
        """Append a Word field code run (PAGE, NUMPAGES, etc.) to *paragraph*."""
        run = paragraph.add_run()
        run.font.size = Pt(12)
        fld_begin = OxmlElement("w:fldChar")
        fld_begin.set(qn("w:fldCharType"), "begin")
        run._r.append(fld_begin)
        instr = OxmlElement("w:instrText")
        instr.set(qn("xml:space"), "preserve")
        instr.text = f" {field_name} "
        run._r.append(instr)
        fld_end = OxmlElement("w:fldChar")
        fld_end.set(qn("w:fldCharType"), "end")
        run._r.append(fld_end)

    def _hide_cell_border(self, cell, *sides: str) -> None:
        """Set specific border *sides* of *cell* to 'nil' (invisible).

        Accepted side names: ``top``, ``bottom``, ``left``, ``right``,
        ``insideH``, ``insideV``.
        """
        tc = cell._tc
        tcPr = tc.find(qn("w:tcPr"))
        if tcPr is None:
            tcPr = OxmlElement("w:tcPr")
            tc.insert(0, tcPr)
        tcBorders = tcPr.find(qn("w:tcBorders"))
        if tcBorders is None:
            tcBorders = OxmlElement("w:tcBorders")
            tcPr.append(tcBorders)
        for side in sides:
            for old in tcBorders.findall(qn(f"w:{side}")):
                tcBorders.remove(old)
            el = OxmlElement(f"w:{side}")
            el.set(qn("w:val"), "nil")
            tcBorders.append(el)

    def _clear_table_borders(self, table) -> None:
        """Remove all visible borders from a table (make it invisible)."""
        tbl = table._tbl
        tblPr = tbl.find(qn("w:tblPr"))
        if tblPr is None:
            tblPr = OxmlElement("w:tblPr")
            tbl.insert(0, tblPr)
        existing = tblPr.find(qn("w:tblBorders"))
        if existing is not None:
            tblPr.remove(existing)
        tblBorders = OxmlElement("w:tblBorders")
        for name in ("top", "left", "bottom", "right", "insideH", "insideV"):
            el = OxmlElement(f"w:{name}")
            el.set(qn("w:val"), "none")
            el.set(qn("w:sz"), "0")
            el.set(qn("w:space"), "0")
            el.set(qn("w:color"), "auto")
            tblBorders.append(el)
        tblPr.append(tblBorders)

    def _set_cell_width(self, cell, width_cm: float) -> None:
        """Set the width of a table cell (in centimetres) via raw XML."""
        tc = cell._tc
        tcPr = tc.find(qn("w:tcPr"))
        if tcPr is None:
            tcPr = OxmlElement("w:tcPr")
            tc.insert(0, tcPr)
        existing = tcPr.find(qn("w:tcW"))
        if existing is not None:
            tcPr.remove(existing)
        tcW = OxmlElement("w:tcW")
        # 1 cm = 360 000 EMU; 1 twip = 635 EMU → twips = Cm(x) / 635
        twips = int(Cm(width_cm) / 635)
        tcW.set(qn("w:w"), str(twips))
        tcW.set(qn("w:type"), "dxa")
        tcPr.append(tcW)

    def _build_format_duration_line(self, meta: ExamMeta) -> str:
        """Return the 'Hình thức: X – Thời lượng: Y phút' header line."""
        parts = []
        if meta.exam_type:
            parts.append(f"Hình thức: {meta.exam_type}")
        dur = str(meta.duration_minutes) if meta.duration_minutes else "__"
        parts.append(f"Thời lượng: {dur} phút")
        return " \u2013 ".join(parts)  # en-dash separator

    def _add_next_page_section_break(self, doc: Document) -> None:
        """Insert a 'next page' Word section break after the question body.

        Using SECTIONPAGES in the document header means the counter resets
        to the page count of this first section only (question pages),
        excluding the answer sheet, scoring rules, and answer key pages.
        """
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        pPr = p._p.get_or_add_pPr()
        # Deep-copy the main sectPr to preserve page size and margins
        main_sectPr = doc.sections[0]._sectPr
        sectPr = copy.deepcopy(main_sectPr)
        # Ensure the type element is set to nextPage
        type_el = sectPr.find(qn("w:type"))
        if type_el is None:
            type_el = OxmlElement("w:type")
            sectPr.insert(0, type_el)
        type_el.set(qn("w:val"), "nextPage")
        pPr.append(sectPr)

    # ------------------------------------------------------------------
    # Instructions
    # ------------------------------------------------------------------

    def _render_instructions(self, doc: Document, questions: list[dict]) -> None:
        types_present = self._types_present(questions)
        if not types_present:
            return

        p = doc.add_paragraph("HƯỚNG DẪN LÀM BÀI")
        p.runs[0].bold = True
        p.runs[0].font.size = Pt(12)
        p.runs[0].underline = True

        for qtype in ["MC", "MA", "BLANK", "SA"]:
            if qtype in types_present and qtype in _INSTRUCTIONS:
                p = doc.add_paragraph(style="List Bullet")
                p.add_run(_INSTRUCTIONS[qtype])
                p.runs[0].font.size = Pt(12)

        doc.add_paragraph("")

    # ------------------------------------------------------------------
    # Question body
    # ------------------------------------------------------------------

    def _group_questions(
        self,
        questions: list[dict],
        config: ExportConfig,
    ) -> list[tuple[str, str, list[dict]]]:
        """Return list of (section_letter, section_title, questions).

        If group_by_type is False, returns a single section with all questions.
        """
        if not config.group_by_type:
            return [("", "", list(questions))]

        # Group by type in canonical order
        order = ["MC", "MA", "BLANK", "SA"]
        buckets: dict[str, list[dict]] = {t: [] for t in order}
        for q in questions:
            qtype = q.get("type", "MC")
            if qtype in buckets:
                buckets[qtype].append(q)

        result = []
        letter_idx = 0
        for qtype in order:
            if buckets[qtype]:
                letter = _SECTION_LETTERS[letter_idx]
                title = f"Phần {letter}. {_TYPE_LABELS.get(qtype, qtype)}"
                result.append((letter, title, buckets[qtype]))
                letter_idx += 1
        return result

    def _render_questions(
        self,
        doc: Document,
        grouped: list[tuple[str, str, list[dict]]],
        config: ExportConfig,
    ) -> None:
        global_counter = 0

        for _letter, title, qs in grouped:
            if title:
                p = doc.add_paragraph(title)
                run = p.runs[0]
                run.bold = True
                run.font.size = Pt(12)
                run.underline = True

            section_counter = 0
            for q in qs:
                global_counter += 1
                section_counter += 1
                num = (
                    global_counter
                    if config.numbering_mode == "global"
                    else section_counter
                )
                self._render_single_question(doc, q, num)

            doc.add_paragraph("")

    def _render_single_question(
        self,
        doc: Document,
        q: dict,
        number: int,
    ) -> None:
        qtype = q.get("type", "MC")
        content = q.get("content", "")
        points = q.get("point_value", 1.0)

        # Question stem
        p = doc.add_paragraph()
        run = p.add_run(f"Câu {number}.")
        run.bold = True
        run.font.size = Pt(12)
        p.add_run(f" {content}")
        p.runs[-1].font.size = Pt(12)
        p.add_run(f"  [{points:g} điểm]")
        p.runs[-1].font.size = Pt(12)
        p.runs[-1].font.color.rgb = RGBColor(0x80, 0x80, 0x80)

        if qtype in ("MC", "MA"):
            self._render_mc_ma_options(doc, q)
        elif qtype == "BLANK":
            self._render_blank_answer_space(doc)
        elif qtype == "SA":
            self._render_sa_answer_space(doc)

    def _render_mc_ma_options(self, doc: Document, q: dict) -> None:
        options = q.get("options", [])
        for opt in options:
            p = doc.add_paragraph()
            run = p.add_run(f"{opt.get('key', '')}. ")
            run.bold = True
            run.font.size = Pt(12)
            p.add_run(opt.get("text", ""))
            p.runs[-1].font.size = Pt(12)
            p.paragraph_format.left_indent = Cm(1.0)

    def _render_blank_answer_space(self, doc: Document) -> None:
        p = doc.add_paragraph("Trả lời: " + "_" * 40)
        p.runs[0].font.size = Pt(12)
        p.paragraph_format.left_indent = Cm(1.0)

    def _render_sa_answer_space(self, doc: Document) -> None:
        p = doc.add_paragraph("Trả lời:")
        p.runs[0].font.size = Pt(12)
        for _ in range(3):
            p2 = doc.add_paragraph("_" * 80)
            p2.runs[0].font.size = Pt(12)
            p2.paragraph_format.left_indent = Cm(1.0)

    def _render_essay_section(
        self,
        doc: Document,
        essay_questions: list[dict],
        section_letter: str,
    ) -> None:
        """Render Tự luận section as the last part of the question body."""
        title = f"Phần {section_letter}. Tự luận" if section_letter else "Tự luận"
        p = doc.add_paragraph(title)
        run = p.runs[0]
        run.bold = True
        run.font.size = Pt(12)
        run.underline = True

        for eq in essay_questions:
            num = eq.get("number", 1)
            score = eq.get("score", 1.0)
            p = doc.add_paragraph()
            run = p.add_run(f"Câu {num}.")
            run.bold = True
            run.font.size = Pt(12)
            p.add_run(f"  [{score:g} điểm]")
            p.runs[-1].font.size = Pt(12)
            p.runs[-1].font.color.rgb = RGBColor(0x80, 0x80, 0x80)
            # Blank answer lines
            for _ in range(6):
                p2 = doc.add_paragraph("_" * 80)
                p2.runs[0].font.size = Pt(12)
                p2.paragraph_format.left_indent = Cm(1.0)
            doc.add_paragraph("")

    # ------------------------------------------------------------------
    # Answer sheet
    # ------------------------------------------------------------------

    def _render_answer_sheet(
        self,
        doc: Document,
        grouped: list[tuple[str, str, list[dict]]],
        config: ExportConfig,
    ) -> None:

        p = doc.add_paragraph("PHIẾU TRẢ LỜI")
        p.runs[0].bold = True
        p.runs[0].font.size = Pt(13)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER

        global_counter = 0
        for _letter, title, qs in grouped:
            if title:
                p = doc.add_paragraph(title)
                p.runs[0].bold = True
                p.runs[0].font.size = Pt(12)

            for q in qs:
                global_counter += 1
                section_num = (
                    global_counter
                    if config.numbering_mode == "global"
                    else qs.index(q) + 1
                )
                qtype = q.get("type", "MC")

                if qtype == "MC":
                    options = q.get("options", [])
                    keys = [o.get("key", "") for o in options]
                    choices = "  ".join(f"○ {k}" for k in keys)
                    p = doc.add_paragraph(
                        f"Câu {section_num}:  {choices}"
                    )
                    p.runs[0].font.size = Pt(12)

                elif qtype == "MA":
                    options = q.get("options", [])
                    keys = [o.get("key", "") for o in options]
                    choices = "  ".join(f"□ {k}" for k in keys)
                    p = doc.add_paragraph(
                        f"Câu {section_num}:  {choices}"
                    )
                    p.runs[0].font.size = Pt(12)

                elif qtype in ("BLANK", "SA"):
                    p = doc.add_paragraph(
                        f"Câu {section_num}:  " + "_" * 50
                    )
                    p.runs[0].font.size = Pt(12)

        # Essay questions — blank answer lines per question
        if config.essay_questions:
            p = doc.add_paragraph("Phần Tự luận")
            p.runs[0].bold = True
            p.runs[0].font.size = Pt(12)
            for eq in config.essay_questions:
                num = eq.get("number", 1)
                score = eq.get("score", 1.0)
                p = doc.add_paragraph()
                run = p.add_run(f"Câu {num}.")
                run.bold = True
                run.font.size = Pt(11)
                p.add_run(f"  [{score:g} điểm]")
                p.runs[-1].font.size = Pt(11)
                p.runs[-1].font.color.rgb = RGBColor(0x80, 0x80, 0x80)
                for _ in range(6):
                    p2 = doc.add_paragraph("_" * 80)
                    p2.runs[0].font.size = Pt(12)
                    p2.paragraph_format.left_indent = Cm(1.0)
                doc.add_paragraph("")

        doc.add_paragraph("")

    # ------------------------------------------------------------------
    # Scoring rules
    # ------------------------------------------------------------------

    def _render_scoring_rules(
        self, doc: Document, questions: list[dict], config: "ExportConfig | None" = None
    ) -> None:
        types_present = self._types_present(questions)
        if not types_present:
            return


        p = doc.add_paragraph("QUY ĐỊNH CHẤM ĐIỂM")
        p.runs[0].bold = True
        p.runs[0].font.size = Pt(13)

        rules: dict[str, str] = {
            "MC": "Mỗi câu Nhiều lựa chọn: chọn đúng 1 đáp án duy nhất mới được điểm; chọn sai hoặc bỏ trống: 0 điểm.",
            "MA": "Mỗi câu Nhiều đáp án: phải chọn đúng và đủ tất cả đáp án đúng mới được toàn bộ điểm; chọn thiếu hoặc thừa: 0 điểm.",
            "BLANK": "Mỗi câu Điền khuyết: điền đúng (không phân biệt hoa/thường, bỏ qua khoảng trắng đầu/cuối) mới được điểm.",
            "SA": "Mỗi câu Trả lời ngắn: so khớp với đáp án mẫu (không phân biệt hoa/thường) mới được điểm.",
        }

        total = sum(q.get("point_value", 1.0) for q in questions)
        if config and config.essay_questions:
            total += sum(eq.get("score", 1.0) for eq in config.essay_questions)

        for qtype in ["MC", "MA", "BLANK", "SA"]:
            if qtype in types_present:
                p = doc.add_paragraph(style="List Bullet")
                p.add_run(rules[qtype])
                p.runs[0].font.size = Pt(12)

        if config and config.essay_questions:
            p = doc.add_paragraph(style="List Bullet")
            p.add_run("Câu hỏi tự luận: Chấm theo thang điểm hướng dẫn chi tiết trong đáp án.")
            p.runs[0].font.size = Pt(12)

        p = doc.add_paragraph(f"Tổng điểm toàn bài: {total:g} điểm.")
        p.runs[0].bold = True
        p.runs[0].font.size = Pt(12)
        doc.add_paragraph("")

    # ------------------------------------------------------------------
    # Answer key
    # ------------------------------------------------------------------

    def _render_answer_key(
        self,
        doc: Document,
        grouped: list[tuple[str, str, list[dict]]],
        config: ExportConfig,
    ) -> None:
        p = doc.add_paragraph("ĐÁP ÁN VÀ THANG ĐIỂM")
        p.runs[0].bold = True
        p.runs[0].font.size = Pt(13)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER

        global_counter = 0
        total = 0.0

        for _letter, title, qs in grouped:
            if title:
                p = doc.add_paragraph(title)
                p.runs[0].bold = True
                p.runs[0].font.size = Pt(12)

            for q in qs:
                global_counter += 1
                num = (
                    global_counter
                    if config.numbering_mode == "global"
                    else qs.index(q) + 1
                )
                qtype = q.get("type", "MC")
                points = q.get("point_value", 1.0)
                total += points

                if qtype in ("MC", "MA"):
                    correct_keys = [
                        o.get("key", "")
                        for o in q.get("options", [])
                        if o.get("is_correct", False)
                    ]
                    answer_str = ", ".join(correct_keys) if correct_keys else "(chưa có)"
                else:
                    answers = q.get("accepted_answers", [])
                    answer_str = " / ".join(answers) if answers else "(chưa có)"

                p = doc.add_paragraph(
                    f"Câu {num}. {answer_str}  —  {points:g} điểm"
                )
                p.runs[0].font.size = Pt(12)

        doc.add_paragraph("")

        # Essay questions in answer key
        if config.essay_questions:
            p = doc.add_paragraph("Phần Tự luận")
            p.runs[0].bold = True
            p.runs[0].font.size = Pt(12)
            for eq in config.essay_questions:
                num = eq.get("number", 1)
                score = eq.get("score", 1.0)
                total += score
                p = doc.add_paragraph(
                    f"Câu {num} (tự luận): Chấm theo thang điểm  —  {score:g} điểm"
                )
                p.runs[0].font.size = Pt(12)

        doc.add_paragraph("")
        p = doc.add_paragraph(f"TỔNG ĐIỂM: {total:g} điểm")
        p.runs[0].bold = True
        p.runs[0].font.size = Pt(12)
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _types_present(self, questions: list[dict]) -> set[str]:
        return {q.get("type", "MC") for q in questions}


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------

def build_output_path(title: str, exports_dir: Path) -> Path:
    """Generate a timestamped output path inside *exports_dir*.

    Example: ``exports/MyExam_2026-04-21_143022.docx``
    """
    exports_dir.mkdir(parents=True, exist_ok=True)
    safe_title = re.sub(r'[\\/:*?"<>|]', "_", title).strip() or "exam"
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    return exports_dir / f"{safe_title}_{timestamp}.docx"
