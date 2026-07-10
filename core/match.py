"""
Deterministic comparison of extracted job-description requirements against
resume text, and the fit_score computation. No LLM involved: given the same
requirement list and resume text, the score and matched/missing lists are
always identical.
"""
import re

from core.skills_taxonomy import SYNONYMS

# Build a reverse synonym map so either side of a pair resolves to the same
# match check (e.g. "js" and "javascript" both satisfy each other).
_SYNONYM_GROUPS = {}
for k, v in SYNONYMS.items():
    _SYNONYM_GROUPS.setdefault(v, {v}).add(k)


def _term_variants(term: str):
    term = term.lower()
    variants = {term}
    if term in _SYNONYM_GROUPS:
        variants |= _SYNONYM_GROUPS[term]
    if term in SYNONYMS:
        canonical = SYNONYMS[term]
        variants.add(canonical)
        variants |= _SYNONYM_GROUPS.get(canonical, set())
    return variants


def _present_in(text: str, term: str) -> bool:
    lower = text.lower()
    for variant in _term_variants(term):
        pattern = r"\b" + re.escape(variant) + r"\b"
        if re.search(pattern, lower):
            return True
    return False


def compare(requirements, resume_text: str):
    """Given requirements (from extract.extract_requirements) and resume
    text, return (matched, missing, fit_score).

    matched/missing are lists of requirement term strings. fit_score is an
    int 0-100: the weighted percentage of requirements found in the resume.
    """
    matched = []
    missing = []
    total_weight = 0
    matched_weight = 0

    for req in requirements:
        term = req["term"]
        weight = req["weight"]
        total_weight += weight
        if _present_in(resume_text, term):
            matched.append(term)
            matched_weight += weight
        else:
            missing.append(term)

    if total_weight == 0:
        fit_score = 0
    else:
        fit_score = round((matched_weight / total_weight) * 100)

    return matched, missing, fit_score
