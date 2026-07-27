#!/usr/bin/env python3
"""Build the static GitHub Pages site into ./site/ (gitignored; produced at deploy time).

A landing page for the corpus — the repo, the MCP server, and llms.txt already serve the
schedules themselves. This exists so the corpus has a front door: without it the site root
404s, and the org registry at https://oregonai.github.io/ cannot offer an "Explore the
corpus" link (it only renders one when the root actually answers).

  python3 src/build_site.py     # writes ./site/{index.html, llms.txt, corpus-index.json}

Wired into .github/workflows/pages.yml.

THIS REPLACES the reusable publish-index workflow, which publishes corpus-index.json and
nothing else — hence the 404. Its own header warns against calling it from a corpus that
deploys Pages itself, because two workflows deploying to one Pages site fight over the
`pages` concurrency group. So this script must keep emitting corpus-index.json at the SAME
URL: the org page reads it for live document counts, and it is how a sibling corpus resolves
citations INTO this one. Dropping it would break something outside this repo, silently.
"""
import json
import shutil
from datetime import date
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
SITE = REPO / "site"
REPO_URL = "https://github.com/OregonAI/oregon-records-retention"
MCP_URL = "https://oregonai.morficflux.com/oregon-records-retention/mcp"
SIBLING_URL = "https://oregonai.github.io/executive-regulatory-frameworks/"


def stats() -> dict:
    cfg = yaml.safe_load((REPO / "_meta/corpus.yml").read_text())
    schedules = sorted((REPO / "schedules").glob("*.md"))
    agencies = set()
    for p in schedules:
        try:
            fm = yaml.safe_load(p.read_text().split("---", 2)[1]) or {}
        except (ValueError, yaml.YAMLError):
            continue
        if fm.get("title"):
            agencies.add(fm["title"])
    return {"schedules": len(schedules), "agencies": len(agencies),
            "name": cfg["corpus"]["name"]}


def build_html() -> str:
    s = stats()
    tiles = [
        ("Retention schedules", f"{s['schedules']:,}",
         "agency-specific SPECIAL schedules from the Secretary of State Archives Division"),
        ("Agencies covered", f"{s['agencies']:,}",
         "one schedule per agency, mirrored verbatim with provenance"),
        ("General schedules", "referenced",
         "OAR chapter 166 lives in the sibling corpus and is cited, never copied"),
    ]
    tile_html = "\n".join(
        f'<div class="tile"><div class="num">{v}</div><div class="lbl">{n}</div>'
        f'<div class="sub">{sub}</div></div>' for n, v, sub in tiles)
    return (TEMPLATE
            .replace("<!--TILES-->", tile_html)
            .replace("__REPO__", REPO_URL)
            .replace("__MCP__", MCP_URL)
            .replace("__SIBLING__", SIBLING_URL)
            .replace("__N__", f"{s['schedules']:,}")
            .replace("__TODAY__", date.today().isoformat()))


def build_corpus_index(site: Path) -> str:
    """Publish the cross-corpus resolution index — see the module docstring for why this
    script owns it rather than the reusable publish-index workflow.

    Built at deploy time, never committed: a committed index is a generated file that can
    silently fall behind its own corpus, and that failure surfaces in SOMEONE ELSE's
    repository when their resolver returns stale titles and paths.
    """
    from corpus_toolkit import config as config_mod
    from corpus_toolkit.index import build_index

    index = build_index(config_mod.load(str(REPO / "_meta/corpus.yml")))
    out = site / "corpus-index.json"
    out.write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")),
                   encoding="utf-8")
    return f"{index['n_documents']:,} documents, {out.stat().st_size / 1024:.0f} KiB"


def main():
    SITE.mkdir(exist_ok=True)
    (SITE / "index.html").write_text(build_html(), encoding="utf-8")
    if (REPO / "llms.txt").exists():
        shutil.copyfile(REPO / "llms.txt", SITE / "llms.txt")
    (SITE / ".nojekyll").write_text("", encoding="utf-8")
    print(f"built site/ ({stats()['schedules']} schedules) -> {SITE.relative_to(REPO)}")
    print(f"  corpus-index.json: {build_corpus_index(SITE)}")


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Oregon Records Retention — agency special schedules</title>
<meta name="description" content="A non-authoritative, machine-readable mirror of Oregon agency special records-retention schedules from the Secretary of State Archives Division.">
<style>
  :root{--bg:#f6f7f9;--panel:#fcfcfb;--ink:#0b0b0b;--muted:#52514e;--line:#e4e8ee;
    --accent:#1f6feb;--accent-ink:#0b4bc0;--gold:#8a6d1f;
    --shadow:0 1px 2px rgba(20,25,40,.06),0 8px 30px rgba(20,25,40,.07)}
  @media (prefers-color-scheme:dark){:root{--bg:#0e1116;--panel:#1a1a19;--ink:#fff;--muted:#c3c2b7;--line:#232a33;
    --accent:#5a9bff;--accent-ink:#8fbaff;--gold:#d9b45a;
    --shadow:0 1px 2px rgba(0,0,0,.4),0 10px 34px rgba(0,0,0,.45)}}
  :root[data-theme="light"]{--bg:#f6f7f9;--panel:#fcfcfb;--ink:#0b0b0b;--muted:#52514e;--line:#e4e8ee;--accent:#1f6feb;--accent-ink:#0b4bc0;--gold:#8a6d1f}
  :root[data-theme="dark"]{--bg:#0e1116;--panel:#1a1a19;--ink:#fff;--muted:#c3c2b7;--line:#232a33;--accent:#5a9bff;--accent-ink:#8fbaff;--gold:#d9b45a}
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--ink);
    font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;-webkit-font-smoothing:antialiased}
  a{color:var(--accent-ink);text-decoration:none} a:hover{text-decoration:underline}
  .wrap{max-width:960px;margin:0 auto;padding:0 22px}
  .disc{background:var(--gold);color:#1a1400;font-size:13px;text-align:center;padding:7px 14px;font-weight:600}
  header{padding:60px 0 26px;border-bottom:1px solid var(--line)}
  .eyebrow{text-transform:uppercase;letter-spacing:.14em;font-size:12px;color:var(--muted);font-weight:700;margin-bottom:14px}
  h1{font-size:clamp(28px,5vw,44px);line-height:1.08;margin:0 0 16px;letter-spacing:-.02em;font-weight:800;text-wrap:balance}
  .lede{font-size:19px;color:var(--muted);max-width:64ch;margin:0}
  .cta{display:flex;flex-wrap:wrap;gap:12px;margin-top:26px}
  .btn{display:inline-flex;align-items:center;gap:8px;padding:11px 18px;border-radius:10px;font-weight:650;font-size:15px;
    border:1px solid var(--line);background:var(--panel);color:var(--ink);box-shadow:var(--shadow)}
  .btn.primary{background:var(--accent);color:#fff;border-color:transparent}
  .btn:hover{text-decoration:none;transform:translateY(-1px)}
  section{padding:44px 0}
  .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px}
  .tile{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:20px;box-shadow:var(--shadow)}
  .tile .num{font-size:32px;font-weight:800;letter-spacing:-.02em;font-variant-numeric:tabular-nums}
  .tile .lbl{font-weight:650;margin-top:2px}
  .tile .sub{color:var(--muted);font-size:13.5px;margin-top:5px;line-height:1.45}
  h2{font-size:14px;text-transform:uppercase;letter-spacing:.1em;color:var(--muted);margin:0 0 18px;font-weight:700}
  code{background:var(--bg);border:1px solid var(--line);border-radius:6px;padding:1px 6px;font-size:13px;font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
  ul.plain{margin:0;padding-left:20px;color:var(--muted);font-size:14.5px}
  ul.plain li{margin:8px 0}
  footer{border-top:1px solid var(--line);padding:30px 0 60px;color:var(--muted);font-size:13.5px}
  footer p{margin:6px 0}
  #theme{position:fixed;top:14px;right:14px;width:36px;height:36px;border-radius:10px;border:1px solid var(--line);
    background:var(--panel);color:var(--ink);cursor:pointer;box-shadow:var(--shadow);font-size:16px;z-index:5}
</style>
</head>
<body>
<button id="theme" title="Toggle light/dark" aria-label="Toggle theme">◑</button>
<div class="disc">NON-AUTHORITATIVE reference — not the official retention schedule. Always verify against the Secretary of State Archives Division.</div>
<div class="wrap">
  <header>
    <div class="eyebrow">Oregon · Secretary of State Archives Division</div>
    <h1>How long Oregon agencies must keep their records</h1>
    <p class="lede">__N__ agency-specific <b>special</b> records-retention schedules, mirrored
      verbatim with provenance so an agent can answer "how long do I keep this?" with a
      citation instead of a guess.</p>
    <div class="cta">
      <a class="btn primary" href="__REPO__">Browse the schedules →</a>
      <a class="btn" href="llms.txt">llms.txt</a>
      <a class="btn" href="https://oregonai.github.io/">The platform</a>
    </div>
  </header>

  <section><div class="grid"><!--TILES--></div></section>

  <section>
    <h2>Special schedules, not general ones</h2>
    <ul class="plain">
      <li>A <b>special</b> schedule covers records unique to one agency. This corpus holds
        those.</li>
      <li>The <b>general</b> schedules — OAR chapter 166, which apply across state agencies,
        counties, cities, and special districts — live in
        <a href="__SIBLING__">Executive Regulatory Frameworks</a> and are
        <b>referenced here, never copied</b>. One copy of a rule, cited from wherever it is
        needed.</li>
      <li>That cross-corpus reference is live: this corpus's MCP server resolves an
        <code>OAR 166-*</code> citation into the sibling corpus and returns its title and
        URL, rather than reporting a document it does not hold as nonexistent.</li>
    </ul>
  </section>

  <section>
    <h2>For agents</h2>
    <ul class="plain">
      <li><b>MCP server</b> — <code>__MCP__</code>. Tools: <code>search_corpus</code>,
        <code>get_document</code>, <code>resolve_citation</code>,
        <code>corpus_overview</code>, <code>graph_neighbors</code>,
        <code>authority_chain</code>.</li>
      <li><b>Every schedule carries provenance</b> — source URL, retrieval date, and a
        content hash — so a claim can be traced to the document it came from.</li>
      <li><b>A retention period is a legal obligation.</b> These are mirrors, not the
        official record; verify against the cited source before acting on one.</li>
    </ul>
  </section>

  <footer>
    <p>Built __TODAY__ from the mirrored corpus. Unofficial and non-authoritative; not
      affiliated with the State of Oregon or the Secretary of State.</p>
    <p>Part of the <a href="https://oregonai.github.io/">OregonAI Civic Corpus Platform</a>.</p>
  </footer>
</div>
<script>
(function(){
  var b=document.getElementById('theme'),r=document.documentElement;
  try{var s=localStorage.getItem('theme'); if(s) r.setAttribute('data-theme',s);}catch(e){}
  b.addEventListener('click',function(){
    var cur=r.getAttribute('data-theme')||
      (matchMedia('(prefers-color-scheme:dark)').matches?'dark':'light');
    var next=cur==='dark'?'light':'dark';
    r.setAttribute('data-theme',next);
    try{localStorage.setItem('theme',next);}catch(e){}
  });
})();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
