#!/usr/bin/env python3
"""ingest_schedules.py — fetch every agency SPECIAL records retention schedule
named in `_meta/source-manifest.yml`, extract its text, and write the paired
snapshot + document for each.

Per source:
  1. fetch the PDF (cached under `_meta/.cache/pdfs/`, gitignored, so re-runs
     are offline and the Archives Division is hit once per URL);
  2. copy the raw PDF to `_meta/snapshots/<id>.pdf` — the toolkit's
     `hash_snapshot()` reads the raw source out of the snapshot dir and
     `corpus-verify-provenance` errors with "missing source snapshot" without
     it, so the committed snapshot is raw + extracted text, not text alone;
  3. extract text with pypdf and strip PAGE FURNITURE ONLY (running headers /
     footers that repeat across most pages, and bare page-number lines),
     recording exactly what was removed in `conversion_notes`;
  4. write `_meta/snapshots/<id>.txt`;
  5. write `schedules/<id>.md`, whose `## Full text` is that snapshot
     unmodified — the provenance verifier checks every line of it against the
     snapshot, in order, and fails under 70% coverage.

Deliberately NOT done here (see AGENTS.md, "Scope boundary"): resolving the
OAR chapter 166 general-schedule citations these documents make. Those rules
live verbatim in the sibling corpus and are referenced as citation STRINGS in
`relationships.related`, never copied in.

  --only ID [ID...]   ingest just these manifest ids
  --refetch           ignore the PDF cache
"""
from __future__ import annotations

import argparse
import datetime
import re
import shutil
import sys
import time
import urllib.request
from collections import Counter
from pathlib import Path

import yaml
from pypdf import PdfReader
from pypdf import __version__ as PYPDF_VERSION

from corpus_toolkit.repo import hash_snapshot, normalize_ws

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "_meta" / "source-manifest.yml"
CACHE_DIR = ROOT / "_meta" / ".cache" / "pdfs"
SNAP_DIR = ROOT / "_meta" / "snapshots"
DOC_DIR = ROOT / "schedules"

USER_AGENT = ("OregonAI-corpus-ingest/1.0 (Oregon records-retention corpus; "
              "one fetch per schedule PDF; contact: github.com/morficflux)")
FETCH_DELAY = 0.3

CORPUS = "oregon-records-retention"
JURISDICTION = "oregon"
ISSUING_BODY = "Oregon Secretary of State, Archives Division"
MAINTAINER = "@morficflux"

# --- page furniture -----------------------------------------------------------------
# A line is stripped as furniture only if BOTH tests hold:
#   (1) it repeats at the top (or bottom) of at least FURNITURE_MIN_SHARE of the
#       document's pages, and
#   (2) it is publisher chrome — the Archives Division's running banner, an
#       edition/effective/expires/schedule-number line, or a bare page number.
#
# Repetition alone is not enough, and finding that out cost two rewrites of this
# function. These schedules are built from a page template, so plenty of
# SUBSTANTIVE text repeats at a page edge: every page of schedule-library opens
# "Organizational Placement / Agency: / Division: / Program Description:", and most
# pages of schedule-blind, -tspc, -lottery end "Systems of Record" or "Databases"
# or "None". A pure frequency rule deleted all of it. Test (2) is what keeps
# repeated *content* in the snapshot.
#
# The cost of the narrow rule is that a running header that is not chrome — e.g.
# schedule-forestry prints "Oregon Department of Forestry" atop every page — stays
# in the text. That is the right way to be wrong: an undetected running header is
# verbatim-correct if untidy, while a deleted record series is a records corpus
# telling someone the wrong thing.
HEADER_WINDOW = 6
FOOTER_WINDOW = 3
FURNITURE_MIN_SHARE = 0.80
FURNITURE_MIN_PAGES = 4
MAX_STRIP = 6

CHROME_RE = re.compile(r"""^(?:
      oregon\s+state\s+archives(?:\s+division)?
    | (?:state\s+of\s+oregon\s+)?records?\s+retention\s+schedule
    | (?:edition|effective(?:\s+date)?|revised|expires?|
         schedule\s*(?:number|no\.?|\#))\s*[:.]\s*.{0,80}
)$""", re.I | re.X)

# A bare number is a page number only if it could plausibly BE one — a lone
# "2005" at the foot of a page is more likely a year in a record series than
# page 2005 of a 40-page schedule.
PAGENUM_RE = re.compile(r"^(?:page\s+)?(\d{1,4})(?:\s*(?:of|/)\s*\d{1,4})?$", re.I)


def is_page_number(norm_line: str, npages: int) -> bool:
    m = PAGENUM_RE.match(norm_line)
    if not m:
        return False
    if norm_line.lower().startswith("page") or "of" in norm_line or "/" in norm_line:
        return True
    return int(m.group(1)) <= npages + 5

OAR_166_RE = re.compile(r"\bOAR\s*(166-\d{3}-\d{4})\b")
SCHEDULE_NO_RE = re.compile(r"Schedule\s*Number\s*:?\s*(\d{4}-\d{4})", re.I)
SCHEDULE_NO_COVER_RE = re.compile(r"Records\s+Retention\s+Schedule\s+(\d{4}-\d{4})", re.I)
EFFECTIVE_RE = re.compile(r"Effective\s*Date\s*:?\s*([^\n]{1,60})", re.I)
AGENCY_RE = re.compile(r"^\s*Agency\s*:\s*(.+?)\s*$", re.M)
DIVISION_RE = re.compile(r"^\s*Division\s*:\s*(.+?)\s*$", re.M)

MONTHS = {m.lower(): i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"], start=1)}


# --- fetching -----------------------------------------------------------------------
def fetch_pdf(source_id: str, url: str, refetch: bool) -> tuple[bytes, bool]:
    """Return (pdf_bytes, hit_network). Cached under _meta/.cache/pdfs/."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cached = CACHE_DIR / f"{source_id}.pdf"
    if cached.is_file() and not refetch:
        return cached.read_bytes(), False
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = resp.read()
    if not data.startswith(b"%PDF"):
        raise ValueError(f"{url} did not return a PDF (first bytes {data[:8]!r})")
    cached.write_bytes(data)
    return data, True


# --- extraction ---------------------------------------------------------------------
def page_lines(pdf_path: Path) -> list[list[str]]:
    reader = PdfReader(str(pdf_path))
    pages = []
    for page in reader.pages:
        text = page.extract_text() or ""
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = "".join(ch for ch in text if ch >= " " or ch == "\n" or ch == "\t")
        pages.append([ln.rstrip() for ln in text.split("\n")])
    return pages


def _edge_lines(lines: list[str], window: int, from_end: bool) -> list[str]:
    seq = list(reversed(lines)) if from_end else lines
    out = []
    for ln in seq:
        n = normalize_ws(ln)
        if not n:
            continue
        out.append(n)
        if len(out) >= window:
            break
    return out


def furniture_sets(pages: list[list[str]]) -> tuple[set[str], set[str]]:
    """Publisher-chrome lines that recur at the top / bottom of most pages."""
    if len(pages) < FURNITURE_MIN_PAGES:
        return set(), set()
    top, bot = Counter(), Counter()
    for lines in pages:
        top.update(set(_edge_lines(lines, HEADER_WINDOW, False)))
        bot.update(set(_edge_lines(lines, FOOTER_WINDOW, True)))
    floor = max(FURNITURE_MIN_PAGES, int(FURNITURE_MIN_SHARE * len(pages)))
    header = {ln for ln, c in top.items() if c >= floor and CHROME_RE.match(ln)}
    footer = {ln for ln, c in bot.items()
              if c >= floor and CHROME_RE.match(ln) and ln not in header}
    return header, footer


def strip_page(lines: list[str], header: set[str], footer: set[str],
               npages: int, removed: Counter) -> list[str]:
    """Drop the leading run of header/page-number lines and the trailing run of
    footer/page-number lines. Stops at the first substantive line either way."""
    start, i = 0, 0
    while i < len(lines) and i < MAX_STRIP:
        n = normalize_ws(lines[i])
        if not n:
            i += 1
            continue
        pn = is_page_number(n, npages)
        if n in header or pn:
            removed["page number" if pn else n] += 1
            i += 1
            start = i
            continue
        break

    end, j = len(lines), len(lines) - 1
    while j >= start and (len(lines) - 1 - j) < MAX_STRIP:
        n = normalize_ws(lines[j])
        if not n:
            j -= 1
            continue
        pn = is_page_number(n, npages)
        if n in footer or pn:
            removed["page number" if pn else n] += 1
            j -= 1
            end = j + 1
            continue
        break
    return lines[start:end]


def collapse_blanks(lines: list[str]) -> list[str]:
    out, blank = [], False
    for ln in lines:
        if ln.strip():
            out.append(ln)
            blank = False
        elif not blank:
            out.append("")
            blank = True
    while out and not out[0].strip():
        out.pop(0)
    while out and not out[-1].strip():
        out.pop()
    return out


def extract(pdf_path: Path) -> tuple[str, dict]:
    pages = page_lines(pdf_path)
    header, footer = furniture_sets(pages)
    removed: Counter = Counter()
    kept: list[str] = []
    for lines in pages:
        kept.extend(strip_page(lines, header, footer, len(pages), removed))
        kept.append("")
    text = "\n".join(collapse_blanks(kept)) + "\n"

    # A line beginning "## " would end the '## Full text' section early (the
    # verifier splits on it) and silently drop the rest of the document from the
    # coverage check. One leading space defeats the split and is invisible to the
    # verbatim comparison, which whitespace-normalizes every line.
    fenced = sum(1 for ln in text.split("\n") if ln.startswith("## "))
    if fenced:
        text = "\n".join(" " + ln if ln.startswith("## ") else ln
                         for ln in text.split("\n"))
    return text, {"pages": len(pages), "header": sorted(header),
                  "footer": sorted(footer), "removed": removed, "fenced": fenced}


# --- cover-page metadata ------------------------------------------------------------
def parse_effective_date(raw: str):
    """ISO date only when the source prints a full one. A schedule that prints
    'April 2022' has no day; guessing one would fabricate an effective date, so
    the standard field stays null and the printed string is kept verbatim in
    `effective_date_text`."""
    s = raw.strip().rstrip(".").strip()
    m = re.match(r"^([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})$", s)
    if m and m.group(1).lower() in MONTHS:
        return f"{int(m.group(3)):04d}-{MONTHS[m.group(1).lower()]:02d}-{int(m.group(2)):02d}", s
    m = re.match(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$", s)
    if m:
        return f"{int(m.group(3)):04d}-{int(m.group(1)):02d}-{int(m.group(2)):02d}", s
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", s)
    if m:
        return s, s
    return None, s


def cover_metadata(text: str) -> dict:
    head = text[:20000]
    num = SCHEDULE_NO_RE.search(head) or SCHEDULE_NO_COVER_RE.search(head)
    schedule_number = num.group(1) if num else None

    eff_iso = eff_text = None
    m = EFFECTIVE_RE.search(head)
    if m:
        eff_iso, eff_text = parse_effective_date(m.group(1))

    def _uniq(rx, source):
        vals = {v.strip() for v in rx.findall(source) if v.strip()}
        return vals.pop() if len(vals) == 1 else None

    return {
        "schedule_number": schedule_number,
        "effective_date": eff_iso,
        "effective_date_text": eff_text,
        "agency": _uniq(AGENCY_RE, text),
        "division": _uniq(DIVISION_RE, text),
    }


# --- document authoring -------------------------------------------------------------
def conversion_notes(info: dict) -> str:
    bits = [f"Text extracted from the source PDF with pypdf {PYPDF_VERSION} "
            f"(per-page extract_text), {info['pages']} pages."]
    hdr = info["header"]
    if hdr:
        bits.append("Stripped repeated running-header lines: "
                    + "; ".join(f'"{h}"' for h in hdr) + ".")
    if info["footer"]:
        bits.append("Stripped repeated running-footer lines: "
                    + "; ".join(f'"{f}"' for f in info["footer"]) + ".")
    pages_stripped = info["removed"].get("page number", 0)
    if pages_stripped:
        bits.append(f"Stripped {pages_stripped} bare page-number line(s).")
    if not hdr and not info["footer"] and not pages_stripped:
        bits.append("No repeated publisher-chrome header/footer or bare page-number "
                    "lines were found.")
    bits.append("Only lines that BOTH repeat at a page edge on 80%+ of pages AND read "
                "as publisher chrome (Archives Division banner, edition/effective/"
                "expires/schedule-number line, bare page number) were removed; every "
                "other repeated line, including per-page 'Organizational Placement' / "
                "'Agency' / 'Systems of Record' blocks, was left in place.")
    if info["fenced"]:
        bits.append(f"{info['fenced']} extracted line(s) beginning '## ' carry one "
                    "added leading space so they do not read as a Markdown heading; "
                    "text is otherwise unchanged.")
    bits.append("Trailing whitespace removed and blank-line runs collapsed to one. "
                "No substantive text was rewritten, reordered, or normalized.")
    return " ".join(bits)


def frontmatter(src: dict, meta: dict, sha: str, notes: str, oar: list[str],
                retrieved: str) -> str:
    fm = {
        "schema_version": 1,
        "corpus": CORPUS,
        "jurisdiction": JURISDICTION,
        "id": src["id"],
        "title": src["title"],
        "doc_type": "schedule",
        "citation": src["citation"],
        "authority_level": "schedule",
        "issuing_body": ISSUING_BODY,
        # From the schedule's own cover/banner "Agency:" line, and null when that
        # line is absent or inconsistent across pages. Deliberately NOT defaulted to
        # the manifest title: this field means "what the PDF says it covers", and
        # backfilling it from elsewhere would make an unsourced value look sourced.
        "agency": meta["agency"],
        "division": meta["division"],
        "schedule_number": meta["schedule_number"],
        "legal_authority": ["ORS 192.005", "ORS 357.895", "OAR 166-030-0027"],
        "source_url": src["url"],
        "source_format": "pdf",
        "retrieved": retrieved,
        "source_sha256": sha,
        "effective_date": meta["effective_date"],
        "effective_date_text": meta["effective_date_text"],
        "last_reviewed": None,
        "source_version": meta["schedule_number"],
        "status": "current",
        "content_mode": "verbatim",
        "conversion_notes": notes,
        # AGENTS.md rule 6: the human reviewer sets these at approval, not the
        # ingestion run. The schema requires the keys, so they ship empty rather
        # than asserting a verification that has not happened.
        "last_verified": "",
        "verified_by": "",
        "maintainer": MAINTAINER,
        "relationships": {
            "implements": [],
            "implemented_by": [],
            "references_external": [],
            "related": oar,
            "supersedes": [],
        },
        "tags": ["records-retention", "special-schedule", "state-agency"],
    }
    return yaml.dump(fm, sort_keys=False, allow_unicode=True, width=10 ** 6,
                     default_flow_style=False)


def at_a_glance(src: dict, meta: dict, oar: list[str], info: dict) -> str:
    who = meta["agency"] or src["title"]
    s = [f"Special records retention schedule for {who}, published by the "
         f"{ISSUING_BODY}"]
    if meta["schedule_number"]:
        s.append(f", schedule number {meta['schedule_number']}")
    if meta["effective_date_text"]:
        s.append(f", effective date as printed: {meta['effective_date_text']}")
    s.append(f". It runs to {info['pages']} pages and lists the agency's own record "
             "series with a retention and disposition clause for each.")
    s.append(" Record series that every state agency holds are NOT here: they are "
             "covered by the OAR chapter 166 general schedules, which this corpus "
             "references rather than copies")
    s.append(f" — {len(oar)} distinct general-schedule rule(s) are cited in the text "
             "below." if oar else ".")
    return "".join(s)


def document(src: dict, meta: dict, text: str, sha: str, oar: list[str],
             info: dict, retrieved: str) -> str:
    notes = conversion_notes(info)
    parts = [
        "---\n" + frontmatter(src, meta, sha, notes, oar, retrieved) + "---\n",
        "",
        "> **NON-AUTHORITATIVE — AI-friendly reference only.** This is a curated",
        "> copy, not the official text. Verify against the official source:",
        f"> <{src['url']}> (retrieved {retrieved}).",
        "",
        f"# {src['title']}",
        "",
        "## At a glance",
        "",
        at_a_glance(src, meta, oar, info),
        "",
        "## Full text",
        "",
        text.rstrip("\n"),
        "",
        "## Cross-references",
        "",
        "General records retention schedules cited in the text above. These are OAR",
        "chapter 166 rules and live verbatim in the sibling corpus",
        "[OregonAI/executive-regulatory-frameworks](https://github.com/OregonAI/executive-regulatory-frameworks);",
        "they are referenced here as citations, never copied (see AGENTS.md).",
        "",
    ]
    parts += [f"- {c}" for c in oar] or ["- None cited in this schedule."]
    parts += [
        "",
        "## Provenance & change history",
        "",
        f"- Source: <{src['url']}> · retrieved {retrieved} · sha256 `{sha}`",
        f"- Snapshot: `_meta/snapshots/{src['id']}.txt` (extracted text) and "
        f"`_meta/snapshots/{src['id']}.pdf` (raw source, {info['pages']} pages).",
        f"- Conversion: {notes}",
        "- See [CHANGELOG](../CHANGELOG.md).",
        "",
    ]
    return "\n".join(parts)


# --- driver -------------------------------------------------------------------------
def ingest(src: dict, refetch: bool, retrieved: str) -> dict:
    sid = src["id"]
    data, hit_network = fetch_pdf(sid, src["url"], refetch)
    SNAP_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(CACHE_DIR / f"{sid}.pdf", SNAP_DIR / f"{sid}.pdf")

    text, info = extract(SNAP_DIR / f"{sid}.pdf")
    (SNAP_DIR / f"{sid}.txt").write_text(text, encoding="utf-8")

    # hash_snapshot(): sha256 of the whitespace-normalized committed .txt when it
    # carries >= 200 chars, else of the raw PDF bytes. Called, not reimplemented —
    # corpus-verify-provenance recomputes it exactly this way.
    sha = hash_snapshot(sid, "pdf", SNAP_DIR)

    oar = sorted({f"OAR {m}" for m in OAR_166_RE.findall(text)})
    meta = cover_metadata(text)
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    (DOC_DIR / f"{sid}.md").write_text(
        document(src, meta, text, sha, oar, info, retrieved), encoding="utf-8")

    norm_len = len(normalize_ws(text))
    return {"id": sid, "pages": info["pages"], "chars": len(text),
            "norm_chars": norm_len, "oar": len(oar), "network": hit_network,
            "short": norm_len < 200, "meta": meta, "info": info}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only", nargs="+", metavar="ID")
    ap.add_argument("--refetch", action="store_true")
    args = ap.parse_args()

    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    sources = manifest.get("sources") or []
    if args.only:
        wanted = set(args.only)
        sources = [s for s in sources if s["id"] in wanted]
        missing = wanted - {s["id"] for s in sources}
        if missing:
            print(f"unknown id(s): {', '.join(sorted(missing))}", file=sys.stderr)
            return 2

    retrieved = datetime.date.today().isoformat()
    results, failures = [], []
    for i, src in enumerate(sources, 1):
        try:
            r = ingest(src, args.refetch, retrieved)
        except Exception as e:                                  # noqa: BLE001
            failures.append((src["id"], f"{type(e).__name__}: {e}"))
            print(f"[{i:>2}/{len(sources)}] FAILED {src['id']}: {e}", file=sys.stderr)
            continue
        results.append(r)
        flag = " SHORT-EXTRACTION" if r["short"] else ""
        print(f"[{i:>2}/{len(sources)}] {r['id']:<34} {r['pages']:>4}p "
              f"{r['chars']:>7}c  OAR166={r['oar']:>2}"
              f"  sched={r['meta']['schedule_number'] or '-'}{flag}")
        if r["network"]:
            time.sleep(FETCH_DELAY)

    print(f"\n{len(results)} document(s); "
          f"{sum(r['chars'] for r in results):,} snapshot chars; "
          f"{sum(r['oar'] for r in results):,} OAR 166 citations "
          f"({min((r['oar'] for r in results), default=0)}–"
          f"{max((r['oar'] for r in results), default=0)} per document).")
    for sid, err in failures:
        print(f"FAILED {sid}: {err}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
