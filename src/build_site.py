#!/usr/bin/env python3
"""Build the GitHub Pages site into ./site/ (gitignored; produced at deploy time).

    python3 src/build_site.py

MIGRATED onto `corpus_toolkit.site`. This file used to carry its own copy of the theme-aware
CSS, the tile markup, the theme toggle and the corpus-index.json emission — 220 lines, of
which about 160 were shell shared with two other corpora and about to be shared with five
more. The shell now lives in the toolkit; this file owns the numbers and what they mean.

The contracts it kept are now kept there and are documented in that module: corpus-index.json
at the site root (how a sibling resolves a citation INTO this corpus, and how the org page
reads live counts) and .nojekyll. This still REPLACES the reusable publish-index workflow —
the two must never both exist here, because they fight over the `pages` concurrency group.
"""
import pathlib
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from corpus_toolkit import config as config_mod                       # noqa: E402
from corpus_toolkit.site import Page, Section, Tile, build            # noqa: E402

REPO = pathlib.Path(__file__).resolve().parent.parent
SIBLING = "https://oregonai.github.io/executive-regulatory-frameworks/"


def stats() -> dict:
    agencies = set()
    schedules = sorted((REPO / "schedules").glob("*.md"))
    for p in schedules:
        try:
            fm = yaml.safe_load(p.read_text().split("---", 2)[1]) or {}
        except (ValueError, yaml.YAMLError):
            continue
        if fm.get("title"):
            agencies.add(fm["title"])
    return {"schedules": len(schedules), "agencies": len(agencies)}


def main() -> int:
    s = stats()
    out = build(Page(
        config=config_mod.load(REPO / "_meta/corpus.yml"),
        repo="oregon-records-retention",
        title="Oregon Records Retention — agency special schedules",
        description=("A non-authoritative, machine-readable mirror of Oregon agency special "
                     "records-retention schedules from the Secretary of State Archives "
                     "Division."),
        eyebrow="Oregon · Secretary of State Archives Division",
        headline="How long Oregon agencies must keep their records",
        lede_html=(
            f"<b>{s['schedules']:,} agency-specific <i>special</i> retention schedules</b>, "
            "mirrored verbatim with provenance, so an agent can answer \"how long do I keep "
            "this?\" with a citation instead of a guess."),
        disclaimer=("NON-AUTHORITATIVE reference — not the official retention schedule. "
                    "Always verify against the Secretary of State Archives Division."),
        tiles=[
            Tile("Retention schedules", f"{s['schedules']:,}",
                 "agency-specific SPECIAL schedules from the Archives Division"),
            Tile("Agencies covered", f"{s['agencies']:,}",
                 "one schedule per agency, mirrored verbatim with provenance"),
            Tile("General schedules", "referenced",
                 "OAR chapter 166 lives in the sibling corpus and is cited, never copied"),
        ],
        sections=[
            Section("Special schedules, not general ones", f"""
    <ul class="plain">
      <li>A <b>special</b> schedule covers records unique to one agency. This corpus holds
        those.</li>
      <li>The <b>general</b> schedules — OAR chapter 166, which apply across state agencies,
        counties, cities and special districts — live in
        <a href="{SIBLING}">Executive Regulatory Frameworks</a> and are <b>referenced here,
        never copied</b>. One copy of a rule, cited from wherever it is needed.</li>
      <li>That cross-corpus reference is live: this corpus's MCP server resolves an
        <code>OAR 166-*</code> citation into the sibling corpus and returns its title and
        URL, rather than reporting a document it does not hold as nonexistent.</li>
    </ul>"""),
            Section("For agents", """
    <ul class="plain">
      <li><b>MCP server</b> — tools: <code>search_corpus</code>, <code>get_document</code>,
        <code>resolve_citation</code>, <code>corpus_overview</code>,
        <code>graph_neighbors</code>, <code>authority_chain</code>.</li>
      <li><b>Every schedule carries provenance</b> — source URL, retrieval date and a
        content hash — so a claim can be traced to the document it came from.</li>
      <li><b>A retention period is a legal obligation.</b> These are mirrors, not the
        official record; verify against the cited source before acting on one.</li>
    </ul>"""),
        ],
        footer_note=("Unofficial and non-authoritative; not affiliated with the State of "
                     "Oregon or the Secretary of State."),
    ))
    print(f"built site/ — {s['schedules']} schedules, {s['agencies']} agencies")
    print(f"  corpus-index.json: {out['index']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
