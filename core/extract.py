"""
Deterministic extraction of "requirements" (skills/tools/qualifications) from
a job description's plain text. No LLM involved here on purpose: the same
input text must always produce the same requirement list, so the score in
core/match.py stays reproducible and auditable.
"""
import re

from core.skills_taxonomy import SKILLS_TAXONOMY, GENERIC_STOPWORDS

# Section headers whose content is weighted higher (must-have) vs lower
# (nice-to-have). Matched case-insensitively at the start of a line.
REQUIRED_SECTION_HEADERS = [
    "requirements", "required qualifications", "qualifications",
    "must have", "minimum qualifications", "what you'll need",
    "what you need", "responsibilities",
]
PREFERRED_SECTION_HEADERS = [
    "preferred", "nice to have", "nice-to-have", "bonus", "a plus",
    "preferred qualifications",
]

MAX_REQUIREMENTS = 25

# This tool is callable by arbitrary agents/bots on a marketplace, and its
# output (missing_keywords, suggestions) is often fed straight into a
# *calling* agent's own prompt. A crafted job_description_text could smuggle
# an instruction-like phrase through as a "missing keyword" and have it
# reflected verbatim in our JSON response, where a careless downstream agent
# might interpret it as a command rather than data. Regex-derived candidate
# phrases (unlike the fixed SKILLS_TAXONOMY list) come directly from
# attacker-controlled text, so they're the only extraction path that needs
# this filter.
_INJECTION_PATTERNS = re.compile(
    r"ignore (?:all )?(?:previous|prior|above) instructions?"
    r"|disregard (?:the )?(?:above|previous|prior)"
    r"|new instructions?"
    r"|system prompt|you are now|act as (?:a|an)"
    r"|forget (?:everything|all)"
    r"|reveal your|print your (?:instructions|prompt)"
    r"|assistant:|system:|user:"
    r"|</?\w+>|\{\{.*\}\}"
    # A legitimate resume/JD never needs to name this tool's own JSON
    # output fields -- a candidate phrase that does is trying to manipulate
    # a careless downstream parser (of *our* output), not describe a skill.
    r"|fit_score|missing_keywords|formatting_issues",
    re.IGNORECASE,
)
# Legitimate skill/tool phrases never need these characters; presence is a
# strong signal of an attempt to break out of a template or code context.
_SUSPICIOUS_CHARS = re.compile(r"[<>{}`\n\r]")


def _is_safe_candidate_phrase(phrase: str) -> bool:
    if _INJECTION_PATTERNS.search(phrase):
        return False
    if _SUSPICIOUS_CHARS.search(phrase):
        return False
    if len(phrase) > 60:
        return False
    return True


def _sections(text: str):
    """Split job description text into (header, weight, body) blocks.

    Falls back to a single "required" block covering the whole text when no
    recognizable section headers are found.
    """
    lines = text.splitlines()
    blocks = []
    current_weight = 2  # default: whole doc treated as required if no headers
    current_lines = []

    def header_weight(line: str):
        stripped = line.strip().strip(":").lower()
        if any(stripped == h or stripped.startswith(h) for h in REQUIRED_SECTION_HEADERS):
            return 2
        if any(stripped == h or stripped.startswith(h) for h in PREFERRED_SECTION_HEADERS):
            return 1
        return None

    found_any_header = False
    for line in lines:
        w = header_weight(line)
        if w is not None:
            found_any_header = True
            if current_lines:
                blocks.append((current_weight, "\n".join(current_lines)))
            current_weight = w
            current_lines = []
        else:
            current_lines.append(line)
    if current_lines:
        blocks.append((current_weight, "\n".join(current_lines)))

    if not found_any_header:
        return [(2, text)]
    return blocks


def _taxonomy_matches(body: str):
    lower = body.lower()
    found = []
    for term in SKILLS_TAXONOMY:
        pattern = r"\b" + re.escape(term) + r"\b"
        if re.search(pattern, lower):
            found.append(term)
    return found


def _join_wrapped_lines(body: str) -> str:
    """Collapse hard-wrapped prose back into one logical line per sentence
    block, so a signal phrase (e.g. "experience in X") isn't separated from
    a negation cue (e.g. "don't need") that landed on the previous line
    purely because of where the source text happened to wrap. Explicit
    bullet lines are left as their own separate lines -- those are
    intentionally itemized, not wrapped.
    """
    bullet_start_re = re.compile(r"^\s*[-*•]")
    out_lines = []
    buffer = []

    def flush():
        if buffer:
            out_lines.append(" ".join(buffer))
            buffer.clear()

    for line in body.splitlines():
        if not line.strip():
            flush()
            out_lines.append("")
        elif bullet_start_re.match(line):
            flush()
            out_lines.append(line)
        else:
            buffer.append(line.strip())
    flush()
    return "\n".join(out_lines)


def _bullet_phrase_candidates(body: str):
    """Pull short candidate phrases out of bullet/requirement-style lines.

    Looks at lines starting with a bullet marker or containing "experience
    with" / "proficiency in" / "knowledge of" style signal phrases, then
    splits on commas/and/or to get short noun-phrase-ish candidates.
    """
    body = _join_wrapped_lines(body)
    candidates = []
    signal_re = re.compile(
        r"(?:experience (?:with|in)|proficien(?:cy|t) (?:with|in)|"
        r"knowledge of|familiarity with|skilled in|expertise in)\s+(.+)",
        re.IGNORECASE,
    )
    # A common real-world phrasing this simple regex can't otherwise tell
    # apart from an actual requirement: "you don't need prior experience
    # with X" describes the *absence* of a requirement, not the presence of
    # one. Detecting negation scope in general is out of reach for a regex,
    # but this specific pattern (negation cue immediately before the signal
    # phrase) is common enough to guard against directly.
    negated_signal_re = re.compile(
        r"(?:don'?t|do not|doesn'?t|does not|no|not|without)\s+(?:need|require)\w*\b"
        r"[^.!?]{0,60}?"  # bounded to the same sentence, not the whole paragraph
        r"(?:experience (?:with|in)|proficien(?:cy|t) (?:with|in)|"
        r"knowledge of|familiarity with)",
        re.IGNORECASE,
    )
    bullet_re = re.compile(r"^\s*[-*•]\s*(.+)")

    for line in body.splitlines():
        segment = None
        if negated_signal_re.search(line):
            continue
        m = signal_re.search(line)
        if m:
            segment = m.group(1)
        else:
            b = bullet_re.match(line)
            if b:
                segment = b.group(1)
        if not segment:
            continue

        segment = re.split(r"[.;]", segment)[0]
        # Deliberately not splitting on bare "/" here: compact abbreviations
        # like "A/B" or "CI/CD" would otherwise get sliced in half. Slash-
        # separated alternatives (e.g. "Python/Java") are rare enough that
        # losing them is a better trade than corrupting abbreviations.
        parts = re.split(r",| and | or ", segment)
        for part in parts:
            phrase = part.strip(" .:-\t").lower()
            words = phrase.split()
            if not (2 <= len(words) <= 4):
                continue
            if all(w in GENERIC_STOPWORDS for w in words):
                continue
            if len(phrase) < 2:
                continue
            if not _is_safe_candidate_phrase(phrase):
                continue
            candidates.append(phrase)
    return candidates


# Non-technical job postings frequently list responsibilities/qualifications
# as "Label: description." lines (e.g. "Reliability: You are someone who...")
# rather than "- bullet" or "experience with X" phrasing. The label itself
# is already a clean, concise requirement name -- no need to parse the
# description sentence at all for this pattern.
_LABEL_COLON_RE = re.compile(r"^\s*([A-Za-z][A-Za-z /&-]{1,40}):\s+\S")

# Generic prefixes that use the same "Label: text" shape but aren't actual
# requirement/responsibility names.
_LABEL_COLON_EXCLUDE = {
    "note", "notes", "important", "disclaimer", "tip", "example",
    "about", "summary", "overview", "warning", "please note", "n b",
}


def _label_colon_candidates(body: str):
    candidates = []
    for line in body.splitlines():
        m = _LABEL_COLON_RE.match(line)
        if not m:
            continue
        label = m.group(1).strip().lower()
        if label in _LABEL_COLON_EXCLUDE:
            continue
        words = label.split()
        if not (1 <= len(words) <= 4):
            continue
        if all(w in GENERIC_STOPWORDS for w in words):
            continue
        if not _is_safe_candidate_phrase(label):
            continue
        candidates.append(label)
    return candidates


def _overlaps_taxonomy(phrase: str) -> bool:
    """True if phrase is already effectively covered by a taxonomy term.

    Word-boundary aware on purpose: a naive substring check (`"r" in
    phrase`) would wrongly flag "categorizing" or "proficiency" as covered
    by the single-letter taxonomy entry "r" (the R language), since "r"
    trivially occurs as a substring inside many ordinary words.
    """
    for t in SKILLS_TAXONOMY:
        if phrase == t:
            return True
        if re.search(r"\b" + re.escape(t) + r"\b", phrase):
            return True
        if re.search(r"\b" + re.escape(phrase) + r"\b", t):
            return True
    return False


def extract_requirements(job_description_text: str):
    """Return a deduped, weighted list of requirement dicts:
    [{"term": str, "weight": int}], sorted by weight desc then first-seen
    order. Capped at MAX_REQUIREMENTS.
    """
    weights = {}
    order = []

    for weight, body in _sections(job_description_text):
        for term in _taxonomy_matches(body):
            if term not in weights or weight > weights[term]:
                weights[term] = weight
            if term not in order:
                order.append(term)
        regex_candidates = _bullet_phrase_candidates(body) + _label_colon_candidates(body)
        for phrase in regex_candidates:
            # Only keep regex-derived phrases that aren't already covered by
            # a taxonomy term, to avoid near-duplicate entries.
            if _overlaps_taxonomy(phrase):
                continue
            if phrase not in weights or weight > weights[phrase]:
                weights[phrase] = weight
            if phrase not in order:
                order.append(phrase)

    ranked = sorted(order, key=lambda t: (-weights[t], order.index(t)))
    ranked = ranked[:MAX_REQUIREMENTS]
    return [{"term": t, "weight": weights[t]} for t in ranked]
