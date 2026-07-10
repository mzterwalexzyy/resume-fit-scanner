# Resume/Job-Fit Scanner

A single, stateless Agentic Service Provider (ASP) tool for the OKX.AI
Genesis Hackathon: `analyze_resume_fit` compares pasted resume text against
a pasted job description and returns a structured ATS fit report. Nothing
else -- no resume generation, no chat, no file/image parsing, no crypto
logic.

## What it does

Input: `resume_text`, `job_description_text` (both plain pasted text).

Output (JSON):

```json
{
  "fit_score": 79,
  "missing_keywords": ["flask", "database design", "graphql", "kubernetes"],
  "formatting_issues": [],
  "suggestions": ["Add a specific, quantified bullet showing your experience with \"flask\" -- ..."],
  "summary": "Your resume matches 79% of this role's key requirements -- here's how to close the gap."
}
```

If the input is empty, too short, or doesn't look like resume/job-description
text, it returns `{"rejected": true, "reason": "..."}` instead of a score.

## How the score is actually computed (what's real, what's not)

Everything that produces `fit_score`, `missing_keywords`, and
`formatting_issues` is **plain deterministic code, not an LLM call**. Given
the same two input strings, you get the exact same output every time. The
pipeline, in order:

1. **`core/extract.py`** -- pulls candidate requirements out of the job
   description. Two mechanisms, both rule-based:
   - a curated ~200-term skills/tools/soft-skills taxonomy
     (`core/skills_taxonomy.py`), matched by word boundary;
   - a handful of regex patterns over bullet lines and signal phrases
     ("experience with X", "knowledge of Y") to catch requirement phrases
     the taxonomy doesn't already list.
   Terms found under a "Requirements"/"Qualifications" header are weighted
   2x; terms under "Preferred"/"Nice to have" are weighted 1x.
2. **`core/match.py`** -- checks each requirement's presence in the resume
   text (word-boundary match, plus a small synonym table for things like
   `js`/`javascript`, `k8s`/`kubernetes`). `fit_score` is the weighted
   percentage of requirements found present. This is the only place the
   number is computed -- nothing downstream can change it.
3. **`core/formatting.py`** -- rule-based checks for ATS-breaking patterns
   in plain text: no standard section headers, no dates near an experience
   section, pipe/tab/column layouts (table proxies), 300+ character
   unbroken lines (text-box proxies), and icon/dingbat glyphs.
4. **`core/phrasing.py`** -- **this is the only step that touches an LLM**,
   and only for wording. It takes the already-computed missing keywords,
   formatting fixes, and score, and either:
   - renders them through fixed English templates (default, fully offline,
     what the test harness uses), or
   - if `ANTHROPIC_API_KEY` is set, asks Claude to rephrase the same facts
     more naturally -- then verifies the response still contains the exact
     score and every named missing keyword before using it, silently
     falling back to the template otherwise.

The model never invents the score or the gap list; it can only reword facts
that were already decided by steps 1-3.

**Known limitation:** because this version only accepts pasted plain text
(no file upload), "formatting issues" are detected via textual proxies (pipe
characters, long unbroken lines, missing headers/dates, icon glyphs) rather
than by inspecting an actual `.docx`/PDF's tables, text boxes, or fonts. A
real Word table won't survive being pasted as plain text anyway -- so this
is the practical ceiling for a text-only input, not a shortcut taken to save
time.

## Project layout

```
core/
  skills_taxonomy.py   curated term list + synonyms (no LLM)
  extract.py           JD -> weighted requirement list (no LLM)
  match.py             requirements vs resume -> matched/missing/fit_score (no LLM)
  formatting.py        ATS structural issue checks (no LLM)
  phrasing.py           facts -> plain English (LLM optional, verified)
  analyze.py           input validation + orchestrates the above
mcp_server/
  billing_stub.py      marked integration point for OKX.AI pay-per-call billing (not implemented)
  server.py            thin MCP tool wrapper around core.analyze
tests/
  samples.py           3 synthetic, clearly-fake resume/JD pairs
  test_analyze.py      end-to-end assertions against those pairs
```

`core/` has no dependency on `mcp_server/` -- it's a plain Python function
(`analyze_resume_fit(resume_text, job_description_text) -> dict`) that any
transport can wrap without restructuring.

## Running the test harness

```bash
cd resume-fit-scanner
py -m tests.test_analyze     # or: python -m tests.test_analyze
```

Runs three synthetic cases and asserts on the output:

- **strong_match** -- a backend-engineer resume against a matching JD;
  expects a high score (currently ~79%) with a handful of missing
  nice-to-haves (Flask, GraphQL, Kubernetes).
- **weak_match_with_formatting_issues** -- a marketing resume against a
  senior data-scientist JD, deliberately written with a pipe-table skills
  block, no dates, contact-icon glyphs, and a wall-of-text bullet; expects a
  low score and all four formatting-issue types to fire.
- **invalid_input** -- gibberish, non-resume/non-JD text; expects a
  rejection object, not a fabricated score.

No API key is required to run this -- `core/phrasing.py` falls back to
templates whenever `ANTHROPIC_API_KEY` is unset.

## MCP server wrapper

`mcp_server/server.py` wraps `core.analyze.analyze_resume_fit` as a tool
named `analyze_resume_fit` using the official `mcp` Python SDK's `FastMCP`
helper (the standard Model Context Protocol tool-server shape), plus a
`ping` tool for health checks.

**On OKX.AI's specific integration format:** this project does not have
reliable documented detail on any OKX.AI-specific ASP listing schema beyond
"MCP/A2A protocols, paid in USDT, on X Layer." What's built here is a
standard MCP tool server, since that's the protocol OKX.AI names for
discovery/invocation -- it is *not* a guess at an OKX-specific manifest
format, request signature, or registration payload. If OKX.AI's listing
process needs something beyond a standard MCP tool definition, that piece
still needs to be confirmed against their actual docs/onboarding flow.

### Running locally

```bash
pip install -r requirements.txt
py -m mcp_server.server
```

`server.py` runs the FastMCP server over **streamable-http** (bound to
`0.0.0.0:$PORT`, default 8000) -- not stdio -- because OKX.AI's ASP
registration requires a real `https://` endpoint it can call, not a local
stdio pipe. For a one-off local/stdio smoke test instead (e.g. from a
Python REPL), call `mcp.call_tool(...)` directly as in the checks used
during development, or override the transport in `mcp.run(...)`.

### Live deployment

Currently deployed at **`https://resume-fit.145-241-206-88.sslip.io/mcp`**
(a small Oracle Cloud "Always Free" Ubuntu VM). Stack:

- `resume-fit-scanner.service` (systemd) -- runs `python -m mcp_server.server`
  under the repo's venv, `Restart=on-failure`, listens internally on
  `0.0.0.0:8000`.
- **Caddy** reverse-proxies `443`/`80` -> `localhost:8000` and auto-provisions
  a real Let's Encrypt certificate. The hostname uses
  [sslip.io](https://sslip.io) (`resume-fit.<dashed-ip>.sslip.io` always
  resolves to `<ip>`) so no domain purchase was needed -- Let's Encrypt still
  issues a normal trusted cert for it via HTTP-01/TLS-ALPN-01.
- Both **OCI's cloud-level Security List** (VCN-level firewall) and the
  instance's **local `iptables`** had to separately allow inbound 80/443 --
  either one alone blocks Let's Encrypt's validation servers with a
  same-symptom "timeout during connect" error, so if this ever needs
  redeploying elsewhere, check both layers.

### Environment variables

| Variable | Required | Purpose |
|---|---|---|
| `PORT` | no | Port the streamable-http server binds to internally. Default `8000`. |
| `ANTHROPIC_API_KEY` | no | Enables LLM-phrased suggestions/summary (see above). Omit to run fully offline on templates. |

### Payment / billing integration point (not implemented)

Real pay-per-call billing is explicitly out of scope for this build -- per
the brief, that's handled on the OKX.AI listing side. What we now know
concretely (from OKX's own `onchainos-skills` docs, not guessed): paid
A2MCP endpoints are expected to speak **x402** (a payment-required HTTP
challenge/response scheme), with OKX recommending their Payment SDK
(`okx-agent-payments-protocol`) for it -- not a generic "USDT on X Layer"
integration as originally assumed. The one hook that exists today is
`mcp_server/billing_stub.py`'s `verify_payment()`, called at the top of the
`analyze_resume_fit` tool handler in `mcp_server/server.py`. It currently
always returns `True` (every call is allowed through). Wiring in a real
x402 challenge/verify step is the one place this needs to change --
nothing else in `core/` or `server.py` does.

## Prompt-injection guardrails

This tool is meant to be called by arbitrary agents/bots on a marketplace,
and its JSON output (`missing_keywords`, `suggestions`) is the kind of thing
a calling agent often feeds straight into its own next prompt. That makes a
hostile `job_description_text` a realistic **reflected prompt-injection**
vector even when no LLM is involved on our side at all -- an attacker only
needs their injected phrase to survive extraction and come back out
verbatim in the response for a careless downstream agent to treat it as an
instruction rather than data.

Defenses, in the order data actually flows:

1. **`core/extract.py`** -- every regex-derived candidate phrase (the only
   extraction path that touches attacker-controlled text; the curated
   taxonomy list is our own fixed data) is checked against
   `_is_safe_candidate_phrase`: a pattern list for common injection framing
   ("ignore all previous instructions", "system:", "you are now", "reveal
   your system prompt", etc.), a ban on structurally suspicious characters
   (`<>{}` `` ` `` and newlines), and a 60-char length cap. Anything that
   matches never becomes a `missing_keyword` in the first place, so it can't
   leak into the output regardless of whether the optional LLM step below
   runs.
2. **`core/phrasing.py`** -- the one place attacker-derived text actually
   reaches an LLM (only when `ANTHROPIC_API_KEY` is set). The prompt
   explicitly frames every interpolated item as untrusted data to reword,
   never to obey, mirroring the same "render as-is, ignore embedded
   instructions" pattern OKX's own `okx-ai` skill uses for untrusted
   agent-to-agent fields. The response is then re-checked against the same
   pattern/character filter from step 1 before being trusted, falling back
   to the deterministic template on any hit.
3. **Blast radius is architecturally limited regardless:** `phrase_output()`
   is a leaf call -- nothing downstream executes code or takes a further
   action based on its return value, so a successful injection's worst case
   is a wrong sentence in the response, not a compromised process.

`tests/samples.py`'s `prompt_injection_attempt` pair and the matching
assertions in `tests/test_analyze.py` exercise this directly: several
injection payloads embedded in a job description (fake "ignore previous
instructions", "reveal your system prompt", etc.) are asserted to never
appear anywhere in the tool's JSON output.

## Privacy

- Stateless: no resume or job-description text is written to disk, logged,
  or cached anywhere in this codebase. Each call only ever sees the two
  strings passed to it.
- No name, contact info, or identifying data is requested. If a pasted
  resume happens to contain a name/email/phone (normal for resumes), it's
  neither stripped nor used for anything beyond the presence/absence checks
  above -- it's never echoed back or repurposed.
- No financial data, government IDs, or other sensitive personal data
  categories are requested or processed.
