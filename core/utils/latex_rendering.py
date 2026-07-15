"""Lightweight helpers for rendering simple LaTeX-like math inline."""
from __future__ import annotations

from html import escape
import re

_MATH_DELIM_RE = re.compile(r"(?<!\\)\$(.+?)(?<!\\)\$")

_GREEK_MAP = {
    r"\alpha": "α",
    r"\beta": "β",
    r"\gamma": "γ",
    r"\delta": "δ",
    r"\epsilon": "ε",
    r"\theta": "θ",
    r"\lambda": "λ",
    r"\mu": "μ",
    r"\pi": "π",
    r"\sigma": "σ",
    r"\tau": "τ",
    r"\phi": "φ",
    r"\omega": "ω",
    r"\Alpha": "Α",
    r"\Beta": "Β",
    r"\Gamma": "Γ",
    r"\Delta": "Δ",
    r"\Theta": "Θ",
    r"\Lambda": "Λ",
    r"\Mu": "Μ",
    r"\Pi": "Π",
    r"\Sigma": "Σ",
    r"\Phi": "Φ",
    r"\Omega": "Ω",
}

_SYMBOL_MAP = {
    r"\le": "≤",
    r"\ge": "≥",
    r"\leq": "≤",
    r"\geq": "≥",
    r"\leqq": "≦",
    r"\geqq": "≧",
    r"\neq": "≠",
    r"\in": "∈",
    r"\ni": "∋",
    r"\notin": "∉",
    r"\subset": "⊂",
    r"\subseteq": "⊆",
    r"\supset": "⊃",
    r"\supseteq": "⊇",
    r"\parallel": "∥",
    r"\perp": "⊥",
    r"\equiv": "≡",
    r"\cong": "≅",
    r"\sim": "∼",
    r"\simeq": "≃",
    r"\propto": "∝",
    r"\to": "→",
    r"\mapsto": "↦",
    r"\leftarrow": "←",
    r"\rightarrow": "→",
    r"\leftrightarrow": "↔",
    r"\Leftarrow": "⇐",
    r"\Rightarrow": "⇒",
    r"\Leftrightarrow": "⇔",
    r"\longleftarrow": "←",
    r"\longrightarrow": "→",
    r"\longleftrightarrow": "↔",
    r"\times": "×",
    r"\cdot": "·",
    r"\pm": "±",
    r"\approx": "≈",
    r"\infty": "∞",
    r"\%": "%",
    r"\_": "_",
    r"\{": "{",
    r"\}": "}",
    r"\sum": "∑",
    r"\prod": "∏",
    r"\int": "∫",
    r"\iint": "∬",
    r"\iiint": "∭",
    r"\iiiint": "⨌",
    r"\oint": "∮",
    r"\bigcup": "⋃",
    r"\bigcap": "⋂",
    r"\bigvee": "⋁",
    r"\bigwedge": "⋀",
    r"\bigoplus": "⨁",
    r"\bigotimes": "⨂",
    r"\bigodot": "⨀",
    r"\biguplus": "⨄",
    r"\bigsqcup": "⨆",
}

_FUNCTION_MAP = {
    r"\arccos": "arccos",
    r"\arcsin": "arcsin",
    r"\arctan": "arctan",
    r"\arg": "arg",
    r"\cos": "cos",
    r"\cosh": "cosh",
    r"\cot": "cot",
    r"\coth": "coth",
    r"\csc": "csc",
    r"\deg": "deg",
    r"\det": "det",
    r"\dim": "dim",
    r"\exp": "exp",
    r"\gcd": "gcd",
    r"\hom": "hom",
    r"\inf": "inf",
    r"\ker": "ker",
    r"\lg": "lg",
    r"\lim": "lim",
    r"\liminf": "lim inf",
    r"\limsup": "lim sup",
    r"\ln": "ln",
    r"\log": "log",
    r"\max": "max",
    r"\min": "min",
    r"\Pr": "Pr",
    r"\sec": "sec",
    r"\sin": "sin",
    r"\sinh": "sinh",
    r"\sup": "sup",
    r"\tan": "tan",
    r"\tanh": "tanh",
}

_COMMAND_STRIP_MAP = {
    r"\text": lambda value: value,
    r"\mathrm": lambda value: value,
    r"\mathit": lambda value: value,
    r"\mathbf": lambda value: value,
    r"\mathcal": lambda value: value,
    r"\mathbb": lambda value: value,
    r"\mathfrak": lambda value: value,
    r"\mathsf": lambda value: value,
    r"\mathbi": lambda value: value,
    r"\mbox": lambda value: value,
    r"\operatorname": lambda value: value,
}

_SUBSCRIPT_MAP = str.maketrans(
    {
        "0": "₀",
        "1": "₁",
        "2": "₂",
        "3": "₃",
        "4": "₄",
        "5": "₅",
        "6": "₆",
        "7": "₇",
        "8": "₈",
        "9": "₉",
        "+": "₊",
        "-": "₋",
        "=": "₌",
        "(": "₍",
        ")": "₎",
        "a": "ₐ",
        "e": "ₑ",
        "h": "ₕ",
        "i": "ᵢ",
        "j": "ⱼ",
        "k": "ₖ",
        "l": "ₗ",
        "m": "ₘ",
        "n": "ₙ",
        "o": "ₒ",
        "p": "ₚ",
        "r": "ᵣ",
        "s": "ₛ",
        "t": "ₜ",
        "u": "ᵤ",
        "v": "ᵥ",
        "x": "ₓ",
        "A": "ₐ",
        "E": "ₑ",
        "H": "ₕ",
        "I": "ᵢ",
        "J": "ⱼ",
        "K": "ₖ",
        "L": "ₗ",
        "M": "ₘ",
        "N": "ₙ",
        "O": "ₒ",
        "P": "ₚ",
        "R": "ᵣ",
        "S": "ₛ",
        "T": "ₜ",
        "U": "ᵤ",
        "V": "ᵥ",
        "X": "ₓ",
    }
)

_SUPERSCRIPT_MAP = str.maketrans(
    {
        "0": "⁰",
        "1": "¹",
        "2": "²",
        "3": "³",
        "4": "⁴",
        "5": "⁵",
        "6": "⁶",
        "7": "⁷",
        "8": "⁸",
        "9": "⁹",
        "+": "⁺",
        "-": "⁻",
        "=": "⁼",
        "(": "⁽",
        ")": "⁾",
        "n": "ⁿ",
        "i": "ᶦ",
        "x": "ˣ",
        "y": "ʸ",
    }
)


def iter_inline_latex_segments(text: str) -> list[tuple[str, bool]]:
    """Split text into plain and math segments based on ``$...$`` delimiters."""
    segments: list[tuple[str, bool]] = []
    last = 0
    for match in _MATH_DELIM_RE.finditer(text):
        if match.start() > last:
            segments.append((text[last:match.start()], False))
        segments.append((match.group(1), True))
        last = match.end()
    if last < len(text):
        segments.append((text[last:], False))
    return segments


def render_inline_latex_text(text: str) -> str:
    """Render inline LaTeX fragments to a Unicode-friendly plain string."""
    parts: list[str] = []
    for fragment, is_math in iter_inline_latex_segments(text):
        if is_math:
            parts.append(render_latex_fragment(fragment))
        else:
            parts.append(fragment)
    return "".join(parts)


def render_latex_fragment(fragment: str) -> str:
    """Render a single math fragment into a readable Unicode string.

    This is intentionally lightweight and supports the common constructs used
    in the app's question content and rubric entries.
    """
    text = fragment.strip()
    if not text:
        return ""

    text = text.replace(r"\displaystyle", "")
    text = text.replace(r"\textstyle", "")
    text = text.replace(r"\scriptstyle", "")
    text = text.replace(r"\scriptscriptstyle", "")
    text = text.replace(r"\left", "")
    text = text.replace(r"\right", "")
    text = text.replace(r"\,", " ").replace(r"\;", " ").replace(r"\:", " ")
    text = _replace_matrix_environments(text)
    for command, replacer in _COMMAND_STRIP_MAP.items():
        text = _replace_braced_command(text, command, replacer)
    text = _replace_sqrt_commands(text)
    text = _replace_braced_command(
        text,
        r"\frac",
        lambda numerator, denominator: f"({numerator})/({denominator})",
        arity=2,
    )
    for command, replacer in (
        (r"\overrightarrow", _add_combining_vector),
        (r"\overleftarrow", _add_combining_leftarrow),
        (r"\overline", _add_combining_bar),
        (r"\underline", _add_combining_underline),
        (r"\widehat", _add_combining_hat),
        (r"\widetilde", _add_combining_tilde),
        (r"\vec", _add_combining_vector),
        (r"\bar", _add_combining_bar),
        (r"\hat", _add_combining_hat),
        (r"\tilde", _add_combining_tilde),
        (r"\dot", _add_combining_dot),
        (r"\ddot", _add_combining_ddot),
        (r"\acute", _add_combining_acute),
        (r"\grave", _add_combining_grave),
        (r"\breve", _add_combining_breve),
        (r"\check", _add_combining_check),
    ):
        text = _replace_braced_command(text, command, replacer)
    text = _replace_map(text, _GREEK_MAP)
    text = _replace_map(text, _SYMBOL_MAP)
    text = _replace_map(text, _FUNCTION_MAP)
    text = _replace_sqrt_commands(text)
    text = _replace_scripts(text)
    text = _normalize_delimiters(text)
    text = text.replace("{", "").replace("}", "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def render_inline_latex_html(text: str) -> str:
    """Render inline LaTeX fragments as HTML suitable for QTextBrowser."""
    parts: list[str] = []
    for fragment, is_math in iter_inline_latex_segments(text):
        if is_math:
            rendered = _render_latex_fragment_html(fragment)
            parts.append(f'<span class="math">{rendered}</span>')
        else:
            parts.append(escape(fragment))
    return "".join(parts).replace("\n", "<br>")


def _render_latex_fragment_html(fragment: str) -> str:
    tokens: list[tuple[str, str]] = []
    text = fragment.strip()
    if not text:
        return ""

    def replace_script(match: re.Match[str], kind: str) -> str:
        token = f"⟦{kind}{len(tokens)}⟧"
        tokens.append((token, escape(render_latex_fragment(match.group(1)))))
        return token

    text = re.sub(r"\^\{([^{}]+)\}", lambda m: replace_script(m, "SUP"), text)
    text = re.sub(r"_\{([^{}]+)\}", lambda m: replace_script(m, "SUB"), text)
    text = re.sub(
        r"\^([A-Za-z0-9+\-=\(\)niyx])",
        lambda m: replace_script(m, "SUP"),
        text,
    )
    text = re.sub(
        r"_([A-Za-z0-9+\-=\(\)A-Za-z])",
        lambda m: replace_script(m, "SUB"),
        text,
    )

    rendered = escape(render_latex_fragment(text))
    for token, html_value in tokens:
        rendered = rendered.replace(
            escape(token),
            f"<{'sup' if token.startswith('⟦SUP') else 'sub'}>{html_value}</{'sup' if token.startswith('⟦SUP') else 'sub'}>",
        )
    return rendered


def _replace_braced_command(
    text: str,
    command: str,
    replacer,
    *,
    arity: int = 1,
) -> str:
    """Replace a command whose arguments are enclosed in balanced braces."""
    start = 0
    while True:
        idx = text.find(command, start)
        if idx < 0:
            return text

        cursor = idx + len(command)
        args: list[str] = []
        success = True
        for _ in range(arity):
            cursor = _skip_whitespace(text, cursor)
            if cursor >= len(text) or text[cursor] != "{":
                success = False
                break
            value, cursor = _read_braced_group(text, cursor)
            args.append(render_latex_fragment(value))
        if not success:
            start = cursor
            continue

        replacement = replacer(*args)
        text = text[:idx] + replacement + text[cursor:]
        start = idx + len(replacement)
    return text


def _replace_sqrt_commands(text: str) -> str:
    pattern = re.compile(r"\\sqrt(?:\[(?P<index>[^\]]+)\])?\{")
    start = 0
    while True:
        match = pattern.search(text, start)
        if match is None:
            return text
        cursor = match.end() - 1
        value, end = _read_braced_group(text, cursor)
        index = match.group("index")
        rendered = render_latex_fragment(value)
        if index:
            rendered = f"{render_latex_fragment(index)}√({rendered})"
        else:
            rendered = f"√({rendered})"
        text = text[:match.start()] + rendered + text[end:]
        start = match.start() + len(rendered)


def _replace_matrix_environments(text: str) -> str:
    envs = {
        "cases": _render_cases_environment,
        "array": _render_array_environment,
        "matrix": _render_matrix_environment,
        "pmatrix": lambda body, cols=None: f"({ _render_matrix_body(body) })",
        "bmatrix": lambda body, cols=None: f"[{ _render_matrix_body(body) }]",
        "Bmatrix": lambda body, cols=None: f"⦃{_render_matrix_body(body)}⦄",
        "vmatrix": lambda body, cols=None: f"|{_render_matrix_body(body)}|",
        "Vmatrix": lambda body, cols=None: f"∥{_render_matrix_body(body)}∥",
    }
    start = 0
    while True:
        begin = text.find(r"\begin{", start)
        if begin < 0:
            return text
        env_name, after_begin = _read_braced_group(text, begin + len(r"\begin"))
        renderer = envs.get(env_name.strip())
        if renderer is None:
            start = after_begin
            continue

        cursor = after_begin
        cols_spec = None
        if env_name.strip() == "array":
            cursor = _skip_whitespace(text, cursor)
            if cursor < len(text) and text[cursor] == "{":
                cols_spec, cursor = _read_braced_group(text, cursor)

        end_token = rf"\end{{{env_name.strip()}}}"
        end = text.find(end_token, cursor)
        if end < 0:
            return text
        body = text[cursor:end]
        rendered = renderer(body, cols_spec) if env_name.strip() == "array" else renderer(body)
        text = text[:begin] + rendered + text[end + len(end_token):]
        start = begin + len(rendered)


def _render_cases_environment(body: str, _cols: str | None = None) -> str:
    rows = _split_matrix_rows(body)
    rendered_rows: list[str] = []
    for row in rows:
        cells = _split_matrix_cells(row)
        if len(cells) >= 2:
            rendered_rows.append(f"{render_latex_fragment(cells[0])} if {render_latex_fragment(cells[1])}")
        else:
            rendered_rows.append(render_latex_fragment(row))
    return "{ " + " ; ".join(r for r in rendered_rows if r) + " }"


def _render_array_environment(body: str, cols: str | None = None) -> str:
    _ = cols
    return _render_matrix_body(body, row_wrapper=lambda row: row)


def _render_matrix_environment(body: str, _cols: str | None = None) -> str:
    return _render_matrix_body(body)


def _render_matrix_body(body: str, row_wrapper=None) -> str:
    rows = _split_matrix_rows(body)
    rendered_rows = []
    for row in rows:
        cells = [_render_matrix_cell(cell) for cell in _split_matrix_cells(row)]
        rendered = " | ".join(cell for cell in cells if cell)
        if rendered:
            rendered_rows.append(rendered)
    if row_wrapper is not None:
        rendered_rows = [row_wrapper(row) for row in rendered_rows]
    if not rendered_rows:
        return ""
    if len(rendered_rows) == 1:
        return rendered_rows[0]
    return " ; ".join(rendered_rows)


def _render_matrix_cell(cell: str) -> str:
    text = cell.strip()
    if not text:
        return ""
    return render_latex_fragment(text)


def _split_matrix_rows(body: str) -> list[str]:
    return [row.strip() for row in re.split(r"(?<!\\)\\\\", body) if row.strip()]


def _split_matrix_cells(row: str) -> list[str]:
    return [cell.strip() for cell in re.split(r"(?<!\\)&", row)]


def _skip_whitespace(text: str, index: int) -> int:
    while index < len(text) and text[index].isspace():
        index += 1
    return index


def _read_braced_group(text: str, open_index: int) -> tuple[str, int]:
    """Return the contents of the balanced brace group at *open_index*."""
    if open_index >= len(text) or text[open_index] != "{":
        raise ValueError("Expected brace group")

    depth = 0
    cursor = open_index + 1
    start = cursor
    while cursor < len(text):
        char = text[cursor]
        if char == "\\":
            cursor += 2
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            if depth == 0:
                return text[start:cursor], cursor + 1
            depth -= 1
        cursor += 1
    raise ValueError("Unclosed brace group")


def _add_combining_bar(value: str) -> str:
    base = value.strip()
    if not base:
        return base
    return base + "\u0304"


def _add_combining_underline(value: str) -> str:
    base = value.strip()
    if not base:
        return base
    return base + "\u0332"


def _add_combining_hat(value: str) -> str:
    base = value.strip()
    if not base:
        return base
    return base + "\u0302"


def _add_combining_tilde(value: str) -> str:
    base = value.strip()
    if not base:
        return base
    return base + "\u0303"


def _add_combining_vector(value: str) -> str:
    base = value.strip()
    if not base:
        return base
    return base + "\u20d7"


def _add_combining_leftarrow(value: str) -> str:
    base = value.strip()
    if not base:
        return base
    return base + "\u20d6"


def _add_combining_dot(value: str) -> str:
    base = value.strip()
    if not base:
        return base
    return base + "\u0307"


def _add_combining_ddot(value: str) -> str:
    base = value.strip()
    if not base:
        return base
    return base + "\u0308"


def _add_combining_acute(value: str) -> str:
    base = value.strip()
    if not base:
        return base
    return base + "\u0301"


def _add_combining_grave(value: str) -> str:
    base = value.strip()
    if not base:
        return base
    return base + "\u0300"


def _add_combining_breve(value: str) -> str:
    base = value.strip()
    if not base:
        return base
    return base + "\u0306"


def _add_combining_check(value: str) -> str:
    base = value.strip()
    if not base:
        return base
    return base + "\u030c"


def _replace_scripts(text: str) -> str:
    def sub_sup(match: re.Match[str]) -> str:
        return _script_to_unicode(match.group(1), superscript=True)

    def sub_sub(match: re.Match[str]) -> str:
        return _script_to_unicode(match.group(1), superscript=False)

    text = re.sub(r"\^\{([^{}]+)\}", sub_sup, text)
    text = re.sub(r"_\{([^{}]+)\}", sub_sub, text)
    text = re.sub(r"\^([A-Za-z0-9+\-=\(\)niyx])", lambda m: _script_to_unicode(m.group(1), superscript=True), text)
    text = re.sub(r"_([A-Za-z0-9+\-=\(\)A-Za-z])", lambda m: _script_to_unicode(m.group(1), superscript=False), text)
    return text


def _script_to_unicode(value: str, *, superscript: bool) -> str:
    table = _SUPERSCRIPT_MAP if superscript else _SUBSCRIPT_MAP
    return value.translate(table)


def _normalize_delimiters(text: str) -> str:
    replacements = {
        r"\langle": "⟨",
        r"\rangle": "⟩",
        r"\lfloor": "⌊",
        r"\rfloor": "⌋",
        r"\lceil": "⌈",
        r"\rceil": "⌉",
        r"\lvert": "|",
        r"\rvert": "|",
        r"\vert": "|",
        r"\|": "∥",
        r"\Vert": "∥",
        r"\backslash": "\\",
        r"\uparrow": "↑",
        r"\downarrow": "↓",
        r"\updownarrow": "↕",
        r"\Uparrow": "⇑",
        r"\Downarrow": "⇓",
        r"\Updownarrow": "⇕",
    }
    for latex, symbol in replacements.items():
        text = text.replace(latex, symbol)
    return text


def _replace_map(text: str, mapping: dict[str, str]) -> str:
    for latex, symbol in sorted(mapping.items(), key=lambda item: len(item[0]), reverse=True):
        text = text.replace(latex, symbol)
    return text


__all__ = [
    "iter_inline_latex_segments",
    "render_inline_latex_html",
    "render_inline_latex_text",
    "render_latex_fragment",
]
