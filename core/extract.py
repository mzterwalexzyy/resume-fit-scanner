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
    r"|</?\w+>|\{\{.*\}\}",
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


def _bullet_phrase_candidates(body: str):
    """Pull short candidate phrases out of bullet/requirement-style lines.

    Looks at lines starting with a bullet marker or containing "experience
    with" / "proficiency in" / "knowledge of" style signal phrases, then
    splits on commas/and/or to get short noun-phrase-ish candidates.
    """
    candidates = []
    signal_re = re.compile(
        r"(?:experience (?:with|in)|proficien(?:cy|t) (?:with|in)|"
        r"knowledge of|familiarity with|skilled in|expertise in)\s+(.+)",
        re.IGNORECASE,
    )
    bullet_re = re.compile(r"^\s*[-*•]\s*(.+)")

    for line in body.splitlines():
        segment = None
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
        for phrase in _bullet_phrase_candidates(body):
            # Only keep regex-derived phrases that aren't already covered by
            # a taxonomy term, to avoid near-duplicate entries.
            if any(phrase == t or phrase in t or t in phrase for t in SKILLS_TAXONOMY):
                continue
            if phrase not in weights or weight > weights[phrase]:
                weights[phrase] = weight
            if phrase not in order:
                order.append(phrase)

    ranked = sorted(order, key=lambda t: (-weights[t], order.index(t)))
    ranked = ranked[:MAX_REQUIREMENTS]
    return [{"term": t, "weight": weights[t]} for t in ranked]
