"""
Local, zero-dependency demo web page for recording a screen-capture demo.

NOT part of the ASP/MCP tool -- this is a dev convenience that calls the
exact same core.analyze.analyze_resume_fit() the deployed MCP server uses,
just wrapped in a plain HTML form instead of the MCP protocol, so it's easy
to paste text into a browser and watch the score/keywords/suggestions update
live on screen.

Run with:  py demo/webapp.py     (from the project root)
Then open: http://127.0.0.1:8765
"""
import html
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.analyze import analyze_resume_fit
from tests.samples import PAIRS

PORT = 8765

PAGE_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Resume/Job-Fit Scanner -- local demo</title>
<style>
  body {{ font-family: -apple-system, Segoe UI, Arial, sans-serif; max-width: 900px;
         margin: 40px auto; padding: 0 20px; color: #1a1a2e; background: #fafafa; }}
  h1 {{ font-size: 22px; }}
  .sub {{ color: #666; margin-bottom: 24px; }}
  .row {{ display: flex; gap: 20px; margin-bottom: 16px; }}
  .col {{ flex: 1; }}
  label {{ font-weight: 600; font-size: 13px; display: block; margin-bottom: 6px; }}
  textarea {{ width: 100%; height: 220px; box-sizing: border-box; padding: 10px;
              font-family: monospace; font-size: 13px; border: 1px solid #ccc;
              border-radius: 6px; resize: vertical; }}
  .buttons {{ margin: 16px 0; display: flex; gap: 10px; flex-wrap: wrap; }}
  button {{ background: #14b8a6; color: white; border: none; padding: 10px 18px;
            border-radius: 6px; font-size: 14px; cursor: pointer; }}
  button.secondary {{ background: #e5e7eb; color: #1a1a2e; }}
  button:hover {{ opacity: 0.9; }}
  .results {{ margin-top: 30px; }}
  .score {{ font-size: 56px; font-weight: 800; color: #14b8a6; }}
  .summary {{ font-size: 18px; margin: 6px 0 24px; }}
  .rejected {{ font-size: 18px; color: #b91c1c; margin: 20px 0; }}
  .section-title {{ font-weight: 700; margin: 18px 0 6px; }}
  .chip {{ display: inline-block; background: #fee2e2; color: #991b1b; padding: 4px 10px;
           border-radius: 999px; font-size: 13px; margin: 3px 4px 3px 0; }}
  ul {{ margin: 4px 0; padding-left: 20px; }}
  li {{ margin-bottom: 6px; }}
  .empty {{ color: #999; font-style: italic; }}
</style>
</head>
<body>
  <h1>Resume/Job-Fit Scanner -- local demo</h1>
  <div class="sub">Calls the exact same core.analyze.analyze_resume_fit() code running on the live deployed ASP.</div>
  <form method="POST" action="/">
    <div class="row">
      <div class="col">
        <label>Resume text</label>
        <textarea name="resume_text" placeholder="Paste resume text here...">{resume_text}</textarea>
      </div>
      <div class="col">
        <label>Job description text</label>
        <textarea name="job_description_text" placeholder="Paste job description text here...">{jd_text}</textarea>
      </div>
    </div>
    <div class="buttons">
      <button type="submit">Analyze</button>
      <button type="submit" name="load" value="weak_match_with_formatting_issues" class="secondary">Load weak-match example</button>
      <button type="submit" name="load" value="strong_match" class="secondary">Load strong-match example</button>
    </div>
  </form>
  {results_html}
</body>
</html>
"""


def render_results(result):
    if result is None:
        return ""
    if result.get("rejected"):
        return f'<div class="results"><div class="rejected">Rejected: {html.escape(result["reason"])}</div></div>'

    keywords_html = "".join(f'<span class="chip">{html.escape(k)}</span>' for k in result["missing_keywords"]) \
        or '<div class="empty">None -- great coverage.</div>'
    issues_html = "".join(f"<li>{html.escape(i)}</li>" for i in result["formatting_issues"]) \
        or '<div class="empty">None detected.</div>'
    suggestions_html = "".join(f"<li>{html.escape(s)}</li>" for s in result["suggestions"]) \
        or '<div class="empty">None.</div>'

    return f"""
    <div class="results">
      <div class="score">{result['fit_score']}%</div>
      <div class="summary">{html.escape(result['summary'])}</div>

      <div class="section-title">Missing keywords</div>
      {keywords_html}

      <div class="section-title">Formatting issues</div>
      {issues_html if result["formatting_issues"] else issues_html}

      <div class="section-title">Suggestions</div>
      <ul>{suggestions_html}</ul>
    </div>
    """


class Handler(BaseHTTPRequestHandler):
    def _send_page(self, resume_text="", jd_text="", result=None):
        body = PAGE_TEMPLATE.format(
            resume_text=html.escape(resume_text),
            jd_text=html.escape(jd_text),
            results_html=render_results(result),
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self._send_page()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        fields = parse_qs(body)

        load = fields.get("load", [None])[0]
        if load and load in PAIRS:
            resume_text, jd_text = PAIRS[load]
            self._send_page(resume_text.strip(), jd_text.strip())
            return

        resume_text = fields.get("resume_text", [""])[0]
        jd_text = fields.get("job_description_text", [""])[0]
        result = analyze_resume_fit(resume_text, jd_text)
        self._send_page(resume_text, jd_text, result)

    def log_message(self, format, *args):
        pass  # keep the terminal quiet during recording


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"Demo running at http://127.0.0.1:{PORT}  (Ctrl+C to stop)")
    server.serve_forever()
