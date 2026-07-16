"""
Public-facing landing page + live demo for the Resume/Job-Fit Scanner ASP.

NOT part of the MCP tool itself -- this is a presentation layer so a human
(e.g. a hackathon judge) can try the real analyze_resume_fit()/file_extract
pipeline in a browser, with no MCP client or CLI required. The scoring logic
underneath is byte-for-byte the same code the deployed MCP server runs.

Run with:  py demo/site.py            (serves on 0.0.0.0:$PORT, default 8080)
"""
import base64
import html
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.analyze import analyze_resume_fit
from demo._multipart import parse_multipart
from demo._resume_input import resolve_resume_text
from tests.samples import PAIRS

PORT = int(os.environ.get("SITE_PORT", 8080))
ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

SAMPLES_JSON = json.dumps({
    "weak_match_with_formatting_issues": {
        "resume": PAIRS["weak_match_with_formatting_issues"][0].strip(),
        "jd": PAIRS["weak_match_with_formatting_issues"][1].strip(),
    },
    "strong_match": {
        "resume": PAIRS["strong_match"][0].strip(),
        "jd": PAIRS["strong_match"][1].strip(),
    },
})

# The hero's preview card shows this, computed for real from the repo's own
# strong_match sample via the exact same analyze_resume_fit() the live tool
# uses -- not a fabricated stat. Recomputed on every server start, so it
# always reflects whatever the current scoring logic actually produces.
_hero_resume, _hero_jd = PAIRS["strong_match"]
HERO_RESULT = analyze_resume_fit(_hero_resume, _hero_jd)
HERO_SCORE = HERO_RESULT["fit_score"]
HERO_MISSING = HERO_RESULT["missing_keywords"][:3]
HERO_MISSING_EXTRA = max(0, len(HERO_RESULT["missing_keywords"]) - len(HERO_MISSING))
HERO_SUMMARY = HERO_RESULT["summary"]
HERO_CHIPS = "".join(f'<span class="hero-chip">{html.escape(k)}</span>' for k in HERO_MISSING)
if HERO_MISSING_EXTRA:
    HERO_CHIPS += f'<span class="hero-chip more">+{HERO_MISSING_EXTRA} more</span>'

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Resume Fit Scanner -- OKX.AI Agentic Service Provider</title>
<link rel="icon" type="image/png" href="/assets/favicon.png">
<script>
(function () {
  var t = localStorage.getItem('theme');
  if (t !== 'light' && t !== 'dark') {
    t = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }
  document.documentElement.setAttribute('data-theme', t);
})();
</script>
<style>
@font-face {
  font-family: "Manrope";
  src: url("/assets/Manrope.woff2") format("woff2");
  font-weight: 400 800;
  font-display: swap;
}

:root {
  --bg: #f8fafc;
  --surface: #ffffff;
  --border: #e2e8f0;
  --text: #0f172a;
  --text-muted: #64748b;
  --accent: #4f46e5;
  --accent-2: #3b82f6;
  --accent-soft: #eef2ff;

  --badge-resume-bg: #ede9fe; --badge-resume-fg: #7c3aed;
  --badge-jd-bg: #dcfce7;     --badge-jd-fg: #16a34a;
  --badge-report-bg: #dbeafe; --badge-report-fg: #2563eb;

  --warn-bg: #fff7ed;   --warn-fg: #c2410c;   --warn-border: #fed7aa;
  --danger-bg: #fef2f2; --danger-fg: #dc2626; --danger-border: #fecaca;
  --success-bg: #f0fdf4; --success-fg: #15803d; --success-border: #bbf7d0;

  --score-good: #16a34a;
  --score-mid: #d97706;
  --score-low: #dc2626;

  --radius: 14px;
  --shadow: 0 1px 2px rgba(15, 23, 42, 0.04), 0 8px 24px -12px rgba(15, 23, 42, 0.08);
}

@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0b1220;
    --surface: #121b2e;
    --border: #22304a;
    --text: #e7ebf3;
    --text-muted: #93a1bd;
    --accent: #818cf8;
    --accent-2: #60a5fa;
    --accent-soft: rgba(129, 140, 248, 0.14);

    --badge-resume-bg: rgba(167, 139, 250, 0.16); --badge-resume-fg: #c4b5fd;
    --badge-jd-bg: rgba(74, 222, 128, 0.14);      --badge-jd-fg: #86efac;
    --badge-report-bg: rgba(96, 165, 250, 0.16);  --badge-report-fg: #93c5fd;

    --warn-bg: rgba(217, 119, 6, 0.14);   --warn-fg: #fb923c;   --warn-border: rgba(217, 119, 6, 0.35);
    --danger-bg: rgba(220, 38, 38, 0.14); --danger-fg: #f87171; --danger-border: rgba(220, 38, 38, 0.35);
    --success-bg: rgba(22, 163, 74, 0.14); --success-fg: #4ade80; --success-border: rgba(22, 163, 74, 0.35);

    --score-good: #4ade80;
    --score-mid: #fbbf24;
    --score-low: #f87171;
    --shadow: 0 1px 2px rgba(0, 0, 0, 0.3), 0 8px 24px -12px rgba(0, 0, 0, 0.5);
  }
}
:root[data-theme="dark"] {
  --bg: #0b1220; --surface: #121b2e; --border: #22304a; --text: #e7ebf3; --text-muted: #93a1bd;
  --accent: #818cf8; --accent-2: #60a5fa; --accent-soft: rgba(129, 140, 248, 0.14);
  --badge-resume-bg: rgba(167, 139, 250, 0.16); --badge-resume-fg: #c4b5fd;
  --badge-jd-bg: rgba(74, 222, 128, 0.14); --badge-jd-fg: #86efac;
  --badge-report-bg: rgba(96, 165, 250, 0.16); --badge-report-fg: #93c5fd;
  --warn-bg: rgba(217, 119, 6, 0.14); --warn-fg: #fb923c; --warn-border: rgba(217, 119, 6, 0.35);
  --danger-bg: rgba(220, 38, 38, 0.14); --danger-fg: #f87171; --danger-border: rgba(220, 38, 38, 0.35);
  --success-bg: rgba(22, 163, 74, 0.14); --success-fg: #4ade80; --success-border: rgba(22, 163, 74, 0.35);
  --score-good: #4ade80; --score-mid: #fbbf24; --score-low: #f87171;
  --shadow: 0 1px 2px rgba(0,0,0,0.3), 0 8px 24px -12px rgba(0,0,0,0.5);
}
:root[data-theme="light"] {
  --bg: #f8fafc; --surface: #ffffff; --border: #e2e8f0; --text: #0f172a; --text-muted: #64748b;
  --accent: #4f46e5; --accent-2: #3b82f6; --accent-soft: #eef2ff;
  --badge-resume-bg: #ede9fe; --badge-resume-fg: #7c3aed;
  --badge-jd-bg: #dcfce7; --badge-jd-fg: #16a34a;
  --badge-report-bg: #dbeafe; --badge-report-fg: #2563eb;
  --warn-bg: #fff7ed; --warn-fg: #c2410c; --warn-border: #fed7aa;
  --danger-bg: #fef2f2; --danger-fg: #dc2626; --danger-border: #fecaca;
  --success-bg: #f0fdf4; --success-fg: #15803d; --success-border: #bbf7d0;
  --score-good: #16a34a; --score-mid: #d97706; --score-low: #dc2626;
  --shadow: 0 1px 2px rgba(15,23,42,0.04), 0 8px 24px -12px rgba(15,23,42,0.08);
}

* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; overflow-x: hidden; }
body {
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, "Segoe UI", system-ui, sans-serif;
  line-height: 1.5;
}
h1, h2, h3, .brand, .btn-scan, .btn-primary, .score-number, .card-head h2, .step h3 {
  font-family: "Manrope", -apple-system, "Segoe UI", system-ui, sans-serif;
}
h1, h2, h3 { text-wrap: balance; margin: 0; }
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }
button, input, textarea { font-family: inherit; }
:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }

.nav {
  position: sticky; top: 0; z-index: 10;
  background: color-mix(in srgb, var(--surface) 88%, transparent);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid var(--border);
}
.nav-inner {
  max-width: 1080px; margin: 0 auto; padding: 14px 24px;
  display: flex; align-items: center; justify-content: space-between; gap: 16px;
}
.brand { display: flex; align-items: center; gap: 10px; font-weight: 800; font-size: 17px; }
.brand-logo { flex-shrink: 0; border-radius: 7px; display: block; }
.nav-links { display: flex; align-items: center; gap: 22px; font-size: 14px; font-weight: 600; }
.nav-links a:not(.btn-primary) { color: var(--text-muted); }
.btn-primary {
  background: var(--text); color: var(--surface); padding: 9px 16px;
  border-radius: 999px; font-weight: 700; font-size: 13.5px;
}
.btn-primary:hover { opacity: 0.88; text-decoration: none; }
.theme-toggle {
  width: 36px; height: 36px; border-radius: 999px; border: 1px solid var(--border);
  background: var(--surface); color: var(--text); display: flex; align-items: center;
  justify-content: center; cursor: pointer; flex-shrink: 0;
}
.theme-toggle:hover { border-color: var(--accent); }
.theme-toggle .icon-moon { display: none; }
:root[data-theme="dark"] .theme-toggle .icon-sun { display: none; }
:root[data-theme="dark"] .theme-toggle .icon-moon { display: block; }
@media (max-width: 560px) {
  .nav-links a:not(.btn-primary) { display: none; }
  .brand { font-size: 15px; }
  .btn-primary { padding: 8px 13px; font-size: 12.5px; }
}

.hero { position: relative; overflow: hidden; }
.hero-blob {
  position: absolute; border-radius: 50%; filter: blur(60px); opacity: 0.35; z-index: -1;
  background: radial-gradient(circle, var(--accent) 0%, transparent 70%);
}
.hero-blob.b1 { width: 420px; height: 420px; top: -160px; right: -80px; }
.hero-blob.b2 { width: 320px; height: 320px; bottom: -140px; left: -100px; opacity: 0.22; }
.hero-inner {
  max-width: 1160px; margin: 0 auto; padding: 60px 24px 40px;
  display: grid; grid-template-columns: 1.05fr 0.95fr; gap: 48px; align-items: center;
}
@media (max-width: 900px) { .hero-inner { grid-template-columns: 1fr; padding-top: 40px; } }

.eyebrow {
  display: inline-flex; align-items: center; gap: 6px;
  font-size: 12.5px; font-weight: 700; color: var(--accent);
  background: var(--accent-soft); padding: 5px 12px; border-radius: 999px;
  margin-bottom: 18px; letter-spacing: 0.02em;
}
.eyebrow .dot { width: 6px; height: 6px; border-radius: 50%; background: var(--score-good); }
.hero-copy h1 { font-size: 40px; font-weight: 800; letter-spacing: -0.015em; margin-bottom: 16px; }
.hero-copy .lede { color: var(--text-muted); font-size: 16.5px; max-width: 480px; margin: 0 0 26px; }
.hero-ctas { display: flex; gap: 12px; flex-wrap: wrap; }
.btn-primary-lg {
  background: linear-gradient(135deg, var(--accent), var(--accent-2)); color: white;
  padding: 13px 22px; border-radius: 10px; font-weight: 700; font-size: 14.5px;
  box-shadow: 0 8px 20px -8px color-mix(in srgb, var(--accent) 60%, transparent);
}
.btn-primary-lg:hover { opacity: 0.92; text-decoration: none; }
.btn-ghost {
  padding: 13px 20px; border-radius: 10px; font-weight: 700; font-size: 14.5px;
  color: var(--text); border: 1px solid var(--border);
}
.btn-ghost:hover { border-color: var(--accent); text-decoration: none; }

.hero-visual { display: flex; justify-content: center; }
.hero-card {
  width: 100%; max-width: 380px; background: var(--surface); border: 1px solid var(--border);
  border-radius: 18px; box-shadow: var(--shadow); padding: 20px;
}
.hero-card-label {
  display: flex; align-items: center; justify-content: space-between;
  font-size: 12px; font-weight: 700; color: var(--text-muted); margin-bottom: 14px;
}
.hero-card-tag {
  font-size: 10.5px; font-weight: 700; color: var(--accent); background: var(--accent-soft);
  padding: 3px 8px; border-radius: 999px; text-transform: uppercase; letter-spacing: 0.03em;
}
.hero-ring {
  width: 84px; height: 84px; border-radius: 50%; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  background: conic-gradient(var(--score-good) calc(var(--hero-score) * 3.6deg), var(--border) 0);
}
.hero-ring-inner {
  width: 66px; height: 66px; border-radius: 50%; background: var(--surface);
  display: flex; align-items: center; justify-content: center;
  font-family: "Manrope", sans-serif; font-weight: 800; font-size: 20px;
  font-variant-numeric: tabular-nums; color: var(--score-good);
}
.hero-card-top { display: flex; align-items: center; gap: 16px; margin-bottom: 16px; }
.hero-card-summary { font-size: 13.5px; font-weight: 600; line-height: 1.4; }
.hero-card-sub { font-size: 11.5px; color: var(--text-muted); font-weight: 600; margin: 2px 0 14px; }
.hero-chip-row { display: flex; flex-wrap: wrap; gap: 6px; }
.hero-chip {
  font-size: 12px; font-weight: 600; padding: 4px 10px; border-radius: 999px;
  background: var(--warn-bg); color: var(--warn-fg); border: 1px solid var(--warn-border);
}
.hero-chip.more { background: var(--bg); color: var(--text-muted); border-color: var(--border); }

.app-grid {
  max-width: 1080px; margin: 0 auto; padding: 24px 24px 64px;
  display: grid; grid-template-columns: 1fr 1fr; gap: 20px; align-items: start;
}
@media (max-width: 860px) { .app-grid { grid-template-columns: 1fr; } }

.col-input { display: flex; flex-direction: column; gap: 16px; }
.card {
  background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius);
  box-shadow: var(--shadow); padding: 18px;
}
.card-head { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
.card-head h2 { font-size: 15px; font-weight: 700; flex: 1; }
.badge {
  width: 30px; height: 30px; border-radius: 9px; display: flex; align-items: center;
  justify-content: center; flex-shrink: 0;
}
.badge-resume { background: var(--badge-resume-bg); color: var(--badge-resume-fg); }
.badge-jd { background: var(--badge-jd-bg); color: var(--badge-jd-fg); }
.badge-report { background: var(--badge-report-bg); color: var(--badge-report-fg); }
.badge-warn { background: var(--warn-bg); color: var(--warn-fg); }
.badge-danger { background: var(--danger-bg); color: var(--danger-fg); }
.badge-success { background: var(--success-bg); color: var(--success-fg); }

.link-btn {
  background: none; border: none; color: var(--text-muted); font-size: 12.5px;
  font-weight: 600; cursor: pointer; padding: 4px 6px;
}
.link-btn:hover { color: var(--text); }

textarea {
  width: 100%; min-height: 150px; resize: vertical; border: 1px solid var(--border);
  border-radius: 10px; padding: 12px; font-size: 13.5px; background: var(--bg);
  color: var(--text);
}
textarea::placeholder { color: var(--text-muted); }
.char-count { font-size: 11.5px; color: var(--text-muted); margin-top: 6px; text-align: right; font-variant-numeric: tabular-nums; }

.or-row { display: flex; align-items: center; gap: 10px; margin: 12px 0; color: var(--text-muted); font-size: 12px; }
.or-row::before, .or-row::after { content: ""; flex: 1; height: 1px; background: var(--border); }

.file-drop {
  display: flex; align-items: center; justify-content: center; gap: 8px;
  border: 1.5px dashed var(--border); border-radius: 10px; padding: 14px;
  font-size: 13px; color: var(--text-muted); cursor: pointer; text-align: center;
  transition: border-color 0.15s, color 0.15s;
}
.file-drop:hover, .file-drop.drag-over { border-color: var(--accent); color: var(--accent); }
.file-drop.has-file { border-color: var(--score-good); color: var(--score-good); border-style: solid; }

.examples-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; font-size: 13px; color: var(--text-muted); }
.chip-btn {
  background: var(--accent-soft); color: var(--accent); border: none; border-radius: 999px;
  padding: 6px 12px; font-size: 12.5px; font-weight: 600; cursor: pointer;
}
.chip-btn:hover { opacity: 0.85; }

.btn-scan {
  background: var(--text); color: var(--surface); border: none; border-radius: 10px;
  padding: 14px; font-size: 15px; font-weight: 700; cursor: pointer;
  display: flex; align-items: center; justify-content: center; gap: 8px;
}
.btn-scan:hover:not(:disabled) { opacity: 0.9; }
.btn-scan:disabled { opacity: 0.6; cursor: default; }
.privacy-note { font-size: 12px; color: var(--text-muted); display: flex; align-items: center; gap: 6px; justify-content: center; margin: 0; }

.col-report { position: sticky; top: 84px; }
.report-empty {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  text-align: center; gap: 14px; padding: 64px 24px; color: var(--text-muted);
}
.report-empty svg { opacity: 0.5; }
.report { display: flex; flex-direction: column; gap: 14px; }
.report.hidden, .report-empty.hidden { display: none; }

.score-card { display: flex; align-items: center; gap: 22px; flex-wrap: wrap; }
.score-ring-wrap { position: relative; width: 116px; height: 116px; flex-shrink: 0; }
.score-ring-wrap svg { width: 100%; height: 100%; transform: rotate(-90deg); }
.score-ring-track { fill: none; stroke: var(--border); stroke-width: 10; }
.score-ring-value { fill: none; stroke-width: 10; stroke-linecap: round; transition: stroke-dashoffset 0.8s cubic-bezier(0.16,1,0.3,1), stroke 0.3s; }
.score-ring-center { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; }
.score-number { font-size: 30px; font-weight: 800; font-variant-numeric: tabular-nums; line-height: 1; }
.score-suffix { font-size: 11px; color: var(--text-muted); font-weight: 600; }
.score-summary { flex: 1; min-width: 180px; font-size: 15.5px; font-weight: 600; }

.result-list { margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: 8px; }
.result-list li {
  font-size: 13.5px; padding: 9px 11px; border-radius: 8px; border: 1px solid transparent;
}
.list-warn li { background: var(--warn-bg); color: var(--warn-fg); border-color: var(--warn-border); }
.list-danger li { background: var(--danger-bg); color: var(--danger-fg); border-color: var(--danger-border); }
.list-success li { background: var(--success-bg); color: var(--success-fg); border-color: var(--success-border); }
.empty-note { font-size: 13px; color: var(--text-muted); font-style: italic; }

.rejected-card { border-color: var(--danger-border); }
.rejected-card .card-head h2 { color: var(--danger-fg); }

.how { max-width: 1080px; margin: 0 auto; padding: 8px 24px 64px; }
.how h2 { font-size: 22px; text-align: center; margin-bottom: 8px; }
.how .sub { text-align: center; color: var(--text-muted); font-size: 14px; margin: 0 0 28px; }
.steps { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
@media (max-width: 760px) { .steps { grid-template-columns: 1fr 1fr; } }
.step { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 16px; }
.step-eyebrow { font-size: 11px; font-weight: 700; color: var(--accent); letter-spacing: 0.04em; text-transform: uppercase; margin-bottom: 8px; display: block; }
.step h3 { font-size: 14.5px; margin-bottom: 6px; }
.step p { font-size: 13px; color: var(--text-muted); margin: 0; }

.footer {
  border-top: 1px solid var(--border); padding: 24px; text-align: center;
  font-size: 12.5px; color: var(--text-muted);
}
.footer a { color: var(--text-muted); font-weight: 600; }

@media (prefers-reduced-motion: reduce) {
  .score-ring-value { transition: none; }
}
</style>
</head>
<body>

<nav class="nav">
  <div class="nav-inner">
    <div class="brand">
      <img src="/assets/logo.png" width="28" height="28" alt="" class="brand-logo">
      Resume Fit Scanner
    </div>
    <div class="nav-links">
      <a href="#how-it-works">How it's scored</a>
      <a href="https://github.com/mzterwalexzyy/resume-fit-scanner" target="_blank" rel="noopener">GitHub</a>
      <button class="theme-toggle" id="theme-toggle" type="button" aria-label="Toggle color theme">
        <svg class="icon-sun" width="16" height="16" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="4.2" stroke="currentColor" stroke-width="1.6"/><path d="M12 2.5v2.4M12 19.1v2.4M4.2 4.2l1.7 1.7M18.1 18.1l1.7 1.7M2.5 12h2.4M19.1 12h2.4M4.2 19.8l1.7-1.7M18.1 5.9l1.7-1.7" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>
        <svg class="icon-moon" width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M20 14.5A8.5 8.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/></svg>
      </button>
      <a href="#app" class="btn-primary">Scan your resume</a>
    </div>
  </div>
</nav>

<header class="hero">
  <div class="hero-blob b1"></div>
  <div class="hero-blob b2"></div>
  <div class="hero-inner">
    <div class="hero-copy">
      <span class="eyebrow"><span class="dot"></span>Live OKX.AI Agentic Service Provider &middot; Agent #4956 &middot; X Layer</span>
      <h1>Does your resume actually match the job?</h1>
      <p class="lede">Paste your resume and a job description below. Every keyword, formatting flag, and score is computed by rule-based matching, not guessed by a model &mdash; nothing is stored after you get your result.</p>
      <div class="hero-ctas">
        <a href="#app" class="btn-primary-lg">Scan your resume</a>
        <a href="#how-it-works" class="btn-ghost">See how scoring works</a>
      </div>
    </div>
    <div class="hero-visual">
      <div class="hero-card">
        <div class="hero-card-label">
          <span>Example run</span>
          <span class="hero-card-tag">Real output, our own test sample</span>
        </div>
        <div class="hero-card-top">
          <div class="hero-ring" style="--hero-score: __HERO_SCORE__">
            <div class="hero-ring-inner">__HERO_SCORE__%</div>
          </div>
          <div>
            <div class="hero-card-summary">__HERO_SUMMARY__</div>
          </div>
        </div>
        <div class="hero-card-sub">Missing keywords</div>
        <div class="hero-chip-row">
          __HERO_CHIPS__
        </div>
      </div>
    </div>
  </div>
</header>

<main id="app" class="app-grid">
  <section class="col-input">
    <div class="card">
      <div class="card-head">
        <span class="badge badge-resume">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M7 3.5h7l3 3v13a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1v-15a1 1 0 0 1 1-1z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/><path d="M9 12l2 2 4.5-4.5" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </span>
        <h2>1. Your resume</h2>
        <button class="link-btn" type="button" data-clear="resume">Clear</button>
      </div>
      <textarea id="resume_text" placeholder="Paste your resume content here..."></textarea>
      <div class="char-count" id="resume_count">0 characters</div>
      <div class="or-row"><span>or</span></div>
      <label class="file-drop" id="file-drop">
        <input type="file" id="resume_file" accept=".pdf,.docx,.txt" hidden>
        <span id="file-label">Upload PDF / DOCX / TXT &middot; max 5MB</span>
      </label>
    </div>

    <div class="card">
      <div class="card-head">
        <span class="badge badge-jd">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><rect x="5" y="4" width="14" height="17" rx="1.5" stroke="currentColor" stroke-width="1.6"/><path d="M9 3.5h6v2H9z" fill="currentColor"/><path d="M8 10h8M8 13.5h8M8 17h5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
        </span>
        <h2>2. Job description</h2>
        <button class="link-btn" type="button" data-clear="jd">Clear</button>
      </div>
      <textarea id="jd_text" placeholder="Paste the job description here..."></textarea>
      <div class="char-count" id="jd_count">0 characters</div>
    </div>

    <div class="examples-row">
      <span>Try an example:</span>
      <button type="button" class="chip-btn" data-sample="weak_match_with_formatting_issues">Weak match</button>
      <button type="button" class="chip-btn" data-sample="strong_match">Strong match</button>
    </div>

    <button id="scan-btn" class="btn-scan" type="button">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M12 3l1.8 4.6L18.5 9l-4.7 1.4L12 15l-1.8-4.6L5.5 9l4.7-1.4L12 3z" fill="currentColor"/></svg>
      <span id="scan-btn-label">Scan fit</span>
    </button>
    <p class="privacy-note">
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none"><rect x="5" y="11" width="14" height="9" rx="1.5" stroke="currentColor" stroke-width="1.6"/><path d="M8 11V7a4 4 0 0 1 8 0v4" stroke="currentColor" stroke-width="1.6"/></svg>
      Nothing is stored. Your text is used only to generate this response.
    </p>
  </section>

  <section class="col-report">
    <div id="report-empty" class="card report-empty">
      <svg width="44" height="44" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="1.4"/><path d="M12 7v5l3.5 2" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>
      <p>Your fit report will appear here once you scan a resume.</p>
    </div>
    <div id="report" class="report hidden"></div>
  </section>
</main>

<section id="how-it-works" class="how">
  <h2>How the score is actually computed</h2>
  <p class="sub">Every step below is deterministic. The same two inputs always produce the same output.</p>
  <div class="steps">
    <div class="step"><span class="step-eyebrow">Extract</span><h3>Read the job description</h3><p>Pull required skills and qualifications via a curated taxonomy plus pattern matching &mdash; no model involved.</p></div>
    <div class="step"><span class="step-eyebrow">Match</span><h3>Check your resume</h3><p>Each requirement is checked for presence in your resume text, with a small synonym table (JS/JavaScript, etc.).</p></div>
    <div class="step"><span class="step-eyebrow">Score</span><h3>Compute the percentage</h3><p>fit_score = matched requirement weight &divide; total weight. Fully reproducible and auditable.</p></div>
    <div class="step"><span class="step-eyebrow">Phrase</span><h3>Word it plainly</h3><p>A language model may reword the suggestions for readability &mdash; it never touches the score or the gap list itself.</p></div>
  </div>
</section>

<footer class="footer">
  Built for the OKX.AI Genesis Hackathon &middot;
  <a href="https://github.com/mzterwalexzyy/resume-fit-scanner" target="_blank" rel="noopener">Source on GitHub</a> &middot;
  Registered ASP #4956 on X Layer
</footer>

<script>
document.getElementById('theme-toggle').addEventListener('click', () => {
  const current = document.documentElement.getAttribute('data-theme');
  const next = current === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem('theme', next);
});

const SAMPLES = __SAMPLES_JSON__;

const resumeText = document.getElementById('resume_text');
const jdText = document.getElementById('jd_text');
const resumeCount = document.getElementById('resume_count');
const jdCount = document.getElementById('jd_count');
const fileInput = document.getElementById('resume_file');
const fileDrop = document.getElementById('file-drop');
const fileLabel = document.getElementById('file-label');
const scanBtn = document.getElementById('scan-btn');
const scanBtnLabel = document.getElementById('scan-btn-label');
const reportEmpty = document.getElementById('report-empty');
const report = document.getElementById('report');

function updateCount(el, out) { out.textContent = el.value.length + ' characters'; }
resumeText.addEventListener('input', () => updateCount(resumeText, resumeCount));
jdText.addEventListener('input', () => updateCount(jdText, jdCount));

document.querySelectorAll('[data-clear]').forEach(btn => {
  btn.addEventListener('click', () => {
    if (btn.dataset.clear === 'resume') {
      resumeText.value = ''; updateCount(resumeText, resumeCount);
      fileInput.value = ''; fileLabel.textContent = 'Upload PDF / DOCX / TXT · max 5MB'; fileDrop.classList.remove('has-file');
    } else {
      jdText.value = ''; updateCount(jdText, jdCount);
    }
  });
});

fileInput.addEventListener('change', () => {
  if (fileInput.files.length) {
    fileLabel.textContent = fileInput.files[0].name;
    fileDrop.classList.add('has-file');
    resumeText.value = '';
    updateCount(resumeText, resumeCount);
  }
});
['dragover', 'dragleave', 'drop'].forEach(evt => {
  fileDrop.addEventListener(evt, e => {
    e.preventDefault();
    fileDrop.classList.toggle('drag-over', evt === 'dragover');
    if (evt === 'drop' && e.dataTransfer.files.length) {
      fileInput.files = e.dataTransfer.files;
      fileInput.dispatchEvent(new Event('change'));
    }
  });
});

document.querySelectorAll('[data-sample]').forEach(btn => {
  btn.addEventListener('click', () => {
    const s = SAMPLES[btn.dataset.sample];
    resumeText.value = s.resume;
    jdText.value = s.jd;
    fileInput.value = '';
    fileLabel.textContent = 'Upload PDF / DOCX / TXT · max 5MB';
    fileDrop.classList.remove('has-file');
    updateCount(resumeText, resumeCount);
    updateCount(jdText, jdCount);
    window.scrollTo({ top: document.getElementById('app').offsetTop - 90, behavior: 'smooth' });
  });
});

function scoreColor(score) {
  if (score >= 70) return 'var(--score-good)';
  if (score >= 40) return 'var(--score-mid)';
  return 'var(--score-low)';
}

function escapeHtml(s) {
  return s.replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

function renderList(items, cls, emptyText) {
  if (!items.length) return `<p class="empty-note">${emptyText}</p>`;
  return `<ul class="result-list ${cls}">${items.map(i => `<li>${escapeHtml(i)}</li>`).join('')}</ul>`;
}

function renderReport(data) {
  reportEmpty.classList.add('hidden');
  report.classList.remove('hidden');

  if (data.rejected) {
    report.innerHTML = `
      <div class="card rejected-card">
        <div class="card-head">
          <span class="badge badge-danger">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M12 4l9 16H3z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/><path d="M12 10v4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/><circle cx="12" cy="17" r="0.8" fill="currentColor"/></svg>
          </span>
          <h2>Couldn't analyze this</h2>
        </div>
        <p style="margin:0; font-size:13.5px; color:var(--text-muted);">${escapeHtml(data.reason)}</p>
      </div>`;
    return;
  }

  const circumference = 2 * Math.PI * 50;
  const offset = circumference * (1 - data.fit_score / 100);
  const color = scoreColor(data.fit_score);

  report.innerHTML = `
    <div class="card score-card">
      <div class="score-ring-wrap">
        <svg viewBox="0 0 120 120">
          <circle class="score-ring-track" cx="60" cy="60" r="50"></circle>
          <circle class="score-ring-value" cx="60" cy="60" r="50"
            stroke="${color}"
            stroke-dasharray="${circumference}"
            stroke-dashoffset="${circumference}"></circle>
        </svg>
        <div class="score-ring-center">
          <div class="score-number" style="color:${color}">0</div>
          <div class="score-suffix">/ 100</div>
        </div>
      </div>
      <div class="score-summary">${escapeHtml(data.summary)}</div>
    </div>

    <div class="card">
      <div class="card-head">
        <span class="badge badge-warn">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M4 7h4M4 12h4M4 17h4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/><rect x="10" y="5" width="10" height="4" rx="1" stroke="currentColor" stroke-width="1.4"/><rect x="10" y="10" width="10" height="4" rx="1" stroke="currentColor" stroke-width="1.4"/><rect x="10" y="15" width="7" height="4" rx="1" stroke="currentColor" stroke-width="1.4"/></svg>
        </span>
        <h2>Missing keywords (${data.missing_keywords.length})</h2>
      </div>
      ${renderList(data.missing_keywords, 'list-warn', 'None -- great coverage.')}
    </div>

    <div class="card">
      <div class="card-head">
        <span class="badge badge-danger">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M12 4l9 16H3z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/><path d="M12 10v4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/><circle cx="12" cy="17" r="0.8" fill="currentColor"/></svg>
        </span>
        <h2>Formatting &amp; ATS issues (${data.formatting_issues.length})</h2>
      </div>
      ${renderList(data.formatting_issues, 'list-danger', 'None detected.')}
    </div>

    <div class="card">
      <div class="card-head">
        <span class="badge badge-success">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M9 18h6M10 21h4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/><path d="M12 3a6 6 0 0 0-3.5 10.9c.5.4.5 1 .5 1.1h6c0-.1 0-.7.5-1.1A6 6 0 0 0 12 3z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>
        </span>
        <h2>Suggestions (${data.suggestions.length})</h2>
      </div>
      ${renderList(data.suggestions, 'list-success', 'None.')}
    </div>
  `;

  requestAnimationFrame(() => {
    const ring = report.querySelector('.score-ring-value');
    const numEl = report.querySelector('.score-number');
    ring.style.strokeDashoffset = offset;
    const start = performance.now();
    const dur = 700;
    function tick(now) {
      const t = Math.min(1, (now - start) / dur);
      numEl.textContent = Math.round(t * data.fit_score);
      if (t < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  });

  report.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

scanBtn.addEventListener('click', async () => {
  const formData = new FormData();
  formData.append('resume_text', resumeText.value);
  formData.append('job_description_text', jdText.value);
  if (fileInput.files.length) formData.append('resume_file', fileInput.files[0]);

  scanBtn.disabled = true;
  scanBtnLabel.textContent = 'Scanning...';
  try {
    const res = await fetch('/api/analyze', { method: 'POST', body: formData });
    const data = await res.json();
    renderReport(data);
  } catch (e) {
    renderReport({ rejected: true, reason: 'Network error -- please try again.' });
  } finally {
    scanBtn.disabled = false;
    scanBtnLabel.textContent = 'Scan fit';
  }
});
</script>
</body>
</html>
"""

PAGE = PAGE.replace("__SAMPLES_JSON__", SAMPLES_JSON)
PAGE = PAGE.replace("__HERO_SCORE__", str(HERO_SCORE))
PAGE = PAGE.replace("__HERO_SUMMARY__", html.escape(HERO_SUMMARY))
PAGE = PAGE.replace("__HERO_CHIPS__", HERO_CHIPS)
PAGE_BYTES = PAGE.encode("utf-8")

def _load_asset(filename):
    with open(os.path.join(ASSETS_DIR, filename), "rb") as f:
        return f.read()


ASSET_FILES = {
    "/assets/Manrope.woff2": ("font/woff2", _load_asset("Manrope.woff2")),
    "/assets/logo.png": ("image/png", _load_asset("logo.png")),
    "/assets/favicon.png": ("image/png", _load_asset("favicon.png")),
}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path.startswith("/?"):
            self._respond(200, "text/html; charset=utf-8", PAGE_BYTES)
        elif self.path in ASSET_FILES:
            content_type, data = ASSET_FILES[self.path]
            self._respond(200, content_type, data, cache=True)
        else:
            self._respond(404, "text/plain", b"Not found")

    def do_POST(self):
        if self.path != "/api/analyze":
            self._respond(404, "application/json", b'{"error": "not found"}')
            return

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        fields, files = parse_multipart(body, self.headers.get("Content-Type", ""))

        resume_text = fields.get("resume_text", "")
        jd_text = fields.get("job_description_text", "")
        resolved_text, rejection = resolve_resume_text(resume_text, files.get("resume_file"))

        if rejection is not None:
            result = rejection
        else:
            result = analyze_resume_fit(resolved_text, jd_text)

        self._respond(200, "application/json", json.dumps(result).encode("utf-8"))

    def _respond(self, code, content_type, body, cache=False):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        if cache:
            self.send_header("Cache-Control", "public, max-age=604800, immutable")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Site running on 0.0.0.0:{PORT}")
    server.serve_forever()
