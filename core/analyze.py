"""
Orchestrator for the analyze_resume_fit tool.

Pipeline (matches the spec exactly, in this order):
  1. extract.extract_requirements   -- pull requirements out of the JD (no LLM)
  2. match.compare                  -- check presence/absence in the resume,
                                        compute fit_score (no LLM)
  3. formatting.find_formatting_issues -- rule-based ATS structural checks (no LLM)
  4. phrasing.phrase_output          -- plain-English wording only (LLM optional)

If the inputs don't look like resume/job-description content, or are empty,
this returns a rejection object instead of a fabricated score.
"""
import re

from core.extract import extract_requirements
from core.match import compare
from core.formatting import find_formatting_issues
from core.phrasing import phrase_output, MAX_DISPLAYED_MISSING_KEYWORDS

MIN_WORDS = 20

RESUME_SIGNALS = re.compile(
    r"\b(experience|education|employment|university|college|degree|"
    r"responsible for|worked as|internship|certifi(?:cation|ed)|references)\b",
    re.IGNORECASE,
)
EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+\.[a-z]{2,}", re.IGNORECASE)
PHONE_PATTERN = re.compile(r"(\+?\d[\d\-. ]{8,}\d)")

JD_SIGNALS = re.compile(
    r"\b(responsibilities|requirements|qualifications|we are looking|"
    r"you will|the role|this position|candidate|years of experience|"
    r"about the (?:role|team|company)|apply now|job description)\b",
    re.IGNORECASE,
)


def _word_count(text: str) -> int:
    return len(text.split())


def _looks_like_resume(text: str, requirement_hits: int) -> bool:
    if RESUME_SIGNALS.search(text):
        return True
    if EMAIL_PATTERN.search(text) or PHONE_PATTERN.search(text):
        return True
    return requirement_hits >= 2


def _looks_like_job_description(text: str, requirements) -> bool:
    if JD_SIGNALS.search(text):
        return True
    return len(requirements) >= 2


def validate_input(resume_text: str, job_description_text: str):
    """Return an error message string if input is invalid, else None."""
    if not resume_text or not resume_text.strip():
        return "resume_text is empty. Please paste your resume content."
    if not job_description_text or not job_description_text.strip():
        return "job_description_text is empty. Please paste the target job description."

    if _word_count(resume_text) < MIN_WORDS:
        return ("resume_text is too short to analyze. Please paste your full "
                "resume content (at least a few sentences).")
    if _word_count(job_description_text) < MIN_WORDS:
        return ("job_description_text is too short to analyze. Please paste "
                "the full job description.")

    requirements = extract_requirements(job_description_text)
    if not _looks_like_job_description(job_description_text, requirements):
        return ("job_description_text doesn't look like a job description. "
                "Please paste the actual job posting text (responsibilities, "
                "requirements, qualifications, etc.).")

    resume_requirement_hits = sum(
        1 for r in requirements if compare([r], resume_text)[0]
    )
    if not _looks_like_resume(resume_text, resume_requirement_hits):
        return ("resume_text doesn't look like resume content. Please paste "
                "your actual resume text (experience, education, skills, etc.).")

    return None


def analyze_resume_fit(resume_text: str, job_description_text: str) -> dict:
    """Single stateless entry point. Returns a dict matching the ASP output
    schema, or {"rejected": True, "reason": str} if the input is invalid.
    Nothing here is persisted, logged, or stored beyond this call.
    """
    error = validate_input(resume_text, job_description_text)
    if error:
        return {"rejected": True, "reason": error}

    requirements = extract_requirements(job_description_text)
    matched, missing, fit_score = compare(requirements, resume_text)
    formatting_issues, formatting_fixes = find_formatting_issues(resume_text)
    suggestions, summary = phrase_output(missing, formatting_fixes, fit_score)

    return {
        "fit_score": fit_score,
        "missing_keywords": missing[:MAX_DISPLAYED_MISSING_KEYWORDS],
        "formatting_issues": formatting_issues,
        "suggestions": suggestions,
        "summary": summary,
    }
