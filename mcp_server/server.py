"""
Thin MCP-server wrapper exposing analyze_resume_fit as a pay-per-call tool
for OKX.AI ASP listing.

This wraps core/analyze.py only -- it does not reimplement or duplicate any
of the extraction, scoring, or formatting-check logic. All of that stays in
core/ so it can be tested and reasoned about independently of the transport.

A note on OKX.AI's specific format: this project doesn't have reliable
documented detail on any OKX.AI-specific ASP registration schema beyond
"MCP/A2A protocols, paid in USDT, deployed on X Layer." What's implemented
here is a standard MCP tool server (per the Model Context Protocol spec,
via the official `mcp` Python SDK's FastMCP helper) since that's the
protocol OKX.AI names for discovery/invocation. If OKX.AI's listing process
expects additional metadata beyond a standard MCP tool definition (custom
manifest fields, a specific handshake, etc.), that is NOT covered here --
flagging that explicitly rather than guessing at an unfamiliar API shape.
"""
import os

from mcp.server.fastmcp import FastMCP

from core.analyze import analyze_resume_fit as _analyze_resume_fit
from mcp_server.billing_stub import verify_payment

mcp = FastMCP(
    name="resume-fit-scanner",
    instructions=(
        "Resume/Job-Fit Scanner: compares a resume against a target job "
        "description and returns a structured ATS fit report. Single "
        "stateless call, no data stored."
    ),
    host="0.0.0.0",
    port=int(os.environ.get("PORT", 8000)),
)


@mcp.tool(
    name="analyze_resume_fit",
    description=(
        "Compares a candidate's resume against a target job description and "
        "returns a structured ATS fit report: a 0-100 fit score, keywords/"
        "skills from the job description missing from the resume, "
        "formatting issues likely to break automated ATS parsing, concrete "
        "rewrite suggestions tied to those specific gaps, and a one-sentence "
        "plain-English summary.\n\n"
        "Input: two plain pasted text fields -- resume_text (the candidate's "
        "resume content) and job_description_text (the target job posting "
        "content). No file or image upload; paste plain text only.\n\n"
        "This is a single stateless call: no resume or job description data "
        "is stored, logged, or retained after the response is returned.\n\n"
        "If either input is empty, too short, or doesn't look like resume/"
        "job-description content, the tool returns a rejection object "
        "({\"rejected\": true, \"reason\": ...}) instead of a fabricated score."
    ),
)
def analyze_resume_fit(resume_text: str, job_description_text: str) -> dict:
    # Integration point for OKX.AI's pay-per-call (X Layer / USDT) billing
    # step. See mcp_server/billing_stub.py -- currently a no-op stub that
    # always allows the call through; real verification wires in here.
    verify_payment()

    return _analyze_resume_fit(resume_text, job_description_text)


@mcp.tool(
    name="ping",
    description=(
        "Minimal health-check for OKX.AI's listing review process. Takes no "
        "input, always returns a fixed OK payload with no side effects."
    ),
)
def ping() -> dict:
    return {"status": "ok", "service": "resume-fit-scanner"}


if __name__ == "__main__":
    # streamable-http is the transport OKX.AI's ASP endpoint check expects
    # (a real https:// URL) -- stdio only works for local single-process
    # testing (e.g. the `mcp.call_tool` checks used during development).
    mcp.run(transport="streamable-http")
