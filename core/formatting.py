"""
Rule-based detection of formatting/structural issues likely to break
automated ATS parsing. Input is plain pasted text (no file/image parsing in
scope), so these checks look for textual proxies of known ATS failure modes:
copy-pasted tables, missing section headers, missing dates, dumped text
boxes, and icon/glyph characters that many parsers choke on.

Each check returns an (issue, fix) pair so the same rule can populate both
the formatting_issues list and a matching entry in suggestions.
"""
import re

STANDARD_HEADERS = [
    "experience", "work experience", "professional experience", "employment",
    "education", "skills", "technical skills", "summary", "objective",
    "profile", "projects", "certifications", "publications", "awards",
]

# Common resume date patterns: "Jan 2021 - Present", "2019-2022", "03/2020"
DATE_PATTERN = re.compile(
    r"("
    r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{4}"
    r"|\b\d{1,2}/\d{4}\b"
    r"|\b(19|20)\d{2}\s*(?:-|–|to)\s*(?:(19|20)\d{2}|present|current)\b"
    r"|\b(19|20)\d{2}\b"
    r")",
    re.IGNORECASE,
)

# Misc Symbols (U+2600-26FF), Dingbats (U+2700-27BF), and Supplemental
# Symbols/Pictographs (U+1F300-1FAFF) -- common contact/bullet icon glyphs
# that plain-text ATS parsers frequently can't render.
ICON_CHARS = re.compile(
    "[☀-⛿✀-➿\U0001F300-\U0001FAFF]"
)


def _find_headers(text: str):
    found = []
    for line in text.splitlines():
        stripped = line.strip().strip(":").lower()
        if not stripped or len(stripped) > 40:
            continue
        if stripped in STANDARD_HEADERS:
            found.append(stripped)
    return found


def check_missing_section_headers(text: str):
    if not _find_headers(text):
        return (
            "No standard section headers detected (e.g. 'Experience', "
            "'Education', 'Skills'). ATS parsers rely on these labels to "
            "bucket your content, and non-standard or missing headers are "
            "often skipped entirely.",
            "Label each section with a standard header ('Experience', "
            "'Education', 'Skills') on its own line instead of a stylized or "
            "custom title.",
        )
    return None


def check_missing_dates(text: str):
    headers = _find_headers(text)
    has_experience_section = any("experience" in h or h == "employment" for h in headers)
    if has_experience_section and not DATE_PATTERN.search(text):
        return (
            "No recognizable dates (e.g. 'Jan 2021 - Present') found near "
            "your experience entries. ATS systems that timeline your work "
            "history will misread or drop entries without parsable dates.",
            "Add a start-end date (e.g. 'Jan 2021 - Present') to every role "
            "and education entry in a consistent Month YYYY format.",
        )
    return None


def check_table_like_layout(text: str):
    lines = text.splitlines()
    pipe_lines = sum(1 for l in lines if l.count("|") >= 2)
    tab_lines = sum(1 for l in lines if "\t" in l)
    multi_space_lines = sum(1 for l in lines if re.search(r"\S {3,}\S", l))
    if pipe_lines >= 2 or tab_lines >= 3 or multi_space_lines >= 3:
        return (
            "Content appears to use table/column-style layout (pipe "
            "characters, tabs, or aligned columns). Tables and text boxes "
            "are a leading cause of ATS parsers scrambling or dropping "
            "resume content.",
            "Replace table/column layout with plain single-column bullet "
            "lists so each line is read in the correct order.",
        )
    return None


def check_wall_of_text(text: str):
    lines = [l for l in text.splitlines() if l.strip()]
    if not lines:
        return None
    long_lines = [l for l in lines if len(l) > 300]
    if long_lines:
        return (
            "One or more lines run 300+ characters with no line breaks, "
            "suggesting content pasted from a text box or single-paragraph "
            "block. ATS parsers segment resumes by line/paragraph, so this "
            "content may be merged incorrectly or ignored.",
            "Break long paragraph blocks into short, separate bullet points "
            "(one accomplishment per line).",
        )
    return None


def check_icon_glyphs(text: str):
    if ICON_CHARS.search(text):
        return (
            "Icon or symbol glyphs detected (commonly used for contact info "
            "or bullet decoration). Many ATS parsers can't read these "
            "characters and will render them as blank boxes or skip the "
            "line entirely.",
            "Replace icon glyphs (phone/email/location symbols, decorative "
            "bullets) with plain text labels and standard hyphen bullets.",
        )
    return None


CHECKS = [
    check_missing_section_headers,
    check_missing_dates,
    check_table_like_layout,
    check_wall_of_text,
    check_icon_glyphs,
]


def find_formatting_issues(resume_text: str):
    """Return (issues, fixes) -- parallel lists of issue descriptions and
    their matching fix suggestions."""
    issues = []
    fixes = []
    for check in CHECKS:
        result = check(resume_text)
        if result:
            issue, fix = result
            issues.append(issue)
            fixes.append(fix)
    return issues, fixes
