"""
Plain-English phrasing of the suggestions and summary headline.

The underlying facts (which keywords are missing, what the score is, which
formatting issues were found) are all computed deterministically upstream in
extract.py / match.py / formatting.py. This module's only job is wording.

By default it uses fixed templates (no network calls, fully offline and
reproducible -- this is what runs in the test harness and whenever no LLM
key is configured). If ANTHROPIC_API_KEY is set, it optionally asks Claude to
rephrase the same facts more naturally, then verifies the model didn't change
the score or drop a named gap before using its output; otherwise it silently
falls back to the template.
"""
import os
import re

MAX_SUGGESTIONS = 8
MAX_DISPLAYED_MISSING_KEYWORDS = 15


def _template_suggestions(missing_keywords, formatting_fixes):
    suggestions = []
    # Prioritize the highest-weighted missing keywords (already sorted by
    # extract.py's ranking) so suggestions target the biggest gaps first.
    for term in missing_keywords[:MAX_SUGGESTIONS]:
        suggestions.append(
            f"Add a specific, quantified bullet showing your experience with "
            f"\"{term}\" -- it's named in the job description but doesn't "
            f"appear anywhere in your resume."
        )
    remaining_slots = MAX_SUGGESTIONS - len(suggestions)
    if remaining_slots > 0:
        suggestions.extend(formatting_fixes[:remaining_slots])
    return suggestions


def _template_summary(fit_score: int):
    return (
        f"Your resume matches {fit_score}% of this role's key requirements "
        f"-- here's how to close the gap."
    )


def _llm_client():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        import anthropic
    except ImportError:
        return None
    return anthropic.Anthropic(api_key=api_key)


def _score_preserved(text: str, fit_score: int) -> bool:
    return str(fit_score) in text


def _try_llm_rephrase(missing_keywords, formatting_fixes, fit_score, client):
    """Ask Claude to rephrase the deterministic suggestions/summary more
    naturally. Returns (suggestions, summary) or None on any failure, so
    callers can fall back to templates without special-casing errors.
    """
    template_suggestions = _template_suggestions(missing_keywords, formatting_fixes)
    template_summary = _template_summary(fit_score)

    prompt = (
        "Rephrase the following resume-feedback items in plain, encouraging "
        "English. Keep every named skill/keyword and every number exactly as "
        "given -- do not invent new gaps, drop named gaps, or change the "
        "score. Return exactly one rephrased line per input line, in the "
        "same order, no numbering, no extra commentary.\n\n"
        "SUMMARY (rephrase, must keep the number "
        f"{fit_score} verbatim):\n{template_summary}\n\n"
        "SUGGESTIONS (rephrase each, one per line):\n"
        + "\n".join(template_suggestions)
    )

    try:
        response = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
    except Exception:
        return None

    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if len(lines) < 1 + len(template_suggestions):
        return None

    summary_line = lines[0]
    suggestion_lines = lines[1:1 + len(template_suggestions)]

    if not _score_preserved(summary_line, fit_score):
        return None
    # Guard against the model silently dropping a named gap: every missing
    # keyword must still appear somewhere in the rephrased suggestion text.
    combined = " ".join(suggestion_lines).lower()
    for term in missing_keywords[:MAX_SUGGESTIONS]:
        if term.lower() not in combined:
            return None

    return suggestion_lines, summary_line


def phrase_output(missing_keywords, formatting_fixes, fit_score: int):
    """Return (suggestions, summary), preferring an LLM rephrase when
    available and verifiably faithful, otherwise the deterministic template.
    """
    client = _llm_client()
    if client is not None:
        result = _try_llm_rephrase(missing_keywords, formatting_fixes, fit_score, client)
        if result is not None:
            return result

    return (
        _template_suggestions(missing_keywords, formatting_fixes),
        _template_summary(fit_score),
    )
