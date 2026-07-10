"""
Minimal test harness proving the analyze_resume_fit flow end-to-end against
the synthetic sample pairs in tests/samples.py.

Run with:  py -m tests.test_analyze     (from the project root)
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.analyze import analyze_resume_fit
from tests.samples import PAIRS


def _assert(condition, message):
    if not condition:
        raise AssertionError(message)


def run_case(name, resume_text, job_description_text):
    print(f"\n=== {name} ===")
    result = analyze_resume_fit(resume_text, job_description_text)
    print(json.dumps(result, indent=2))
    return result


def main():
    resume_a, jd_a = PAIRS["strong_match"]
    result_a = run_case("strong_match", resume_a, jd_a)
    _assert("rejected" not in result_a, "strong_match should not be rejected")
    _assert(isinstance(result_a["fit_score"], int), "fit_score must be an int")
    _assert(0 <= result_a["fit_score"] <= 100, "fit_score must be 0-100")
    _assert(result_a["fit_score"] >= 60,
            f"expected a high score for a strong match, got {result_a['fit_score']}")
    _assert(str(result_a["fit_score"]) in result_a["summary"],
            "summary must contain the actual computed score, not a placeholder")
    _assert(len(result_a["summary"]) > 0, "summary must be non-empty")

    resume_b, jd_b = PAIRS["weak_match_with_formatting_issues"]
    result_b = run_case("weak_match_with_formatting_issues", resume_b, jd_b)
    _assert("rejected" not in result_b, "weak_match should not be rejected")
    _assert(result_b["fit_score"] < result_a["fit_score"],
            "weak match should score lower than strong match")
    _assert(len(result_b["missing_keywords"]) > 0,
            "weak match should surface missing keywords")
    _assert(len(result_b["formatting_issues"]) > 0,
            "resume_b has deliberate formatting issues that should be detected")
    _assert(len(result_b["suggestions"]) > 0, "suggestions must not be empty")
    for term in result_b["missing_keywords"][:3]:
        joined_suggestions = " ".join(result_b["suggestions"]).lower()
        # Not every missing keyword is guaranteed a suggestion slot (capped),
        # but at least the top few should be represented.
        if term.lower() in joined_suggestions:
            break
    else:
        raise AssertionError("expected at least one top missing keyword to appear in suggestions")

    resume_c, jd_c = PAIRS["invalid_input"]
    result_c = run_case("invalid_input", resume_c, jd_c)
    _assert(result_c.get("rejected") is True, "gibberish input should be rejected")
    _assert("fit_score" not in result_c, "rejected input must not include a fabricated score")
    _assert(len(result_c["reason"]) > 0, "rejection must include a clear reason")

    empty_result = analyze_resume_fit("", "some job description text here")
    _assert(empty_result.get("rejected") is True, "empty resume_text must be rejected")

    resume_d, jd_d = PAIRS["prompt_injection_attempt"]
    result_d = run_case("prompt_injection_attempt", resume_d, jd_d)
    _assert("rejected" not in result_d, "prompt_injection_attempt should not be rejected outright")
    # The JD's only *legitimate* asks ("ticketing systems", "customer
    # service") are both genuinely present in the resume, so a fair, honest
    # score here really is 100 -- that's not the property under test.
    # What matters is that none of the injected instruction text survived
    # extraction and got reflected back out in the JSON, where a careless
    # downstream calling agent might read it as a command instead of data.
    blob = json.dumps(result_d).lower()
    for banned in ("ignore all previous", "reveal your system prompt", "unrestricted agent",
                   "forget everything", "disregard the above", "set fit_score to 100"):
        _assert(banned not in blob,
                f"injection payload '{banned}' leaked into the tool's JSON output")

    print("\nAll assertions passed.")


if __name__ == "__main__":
    main()
