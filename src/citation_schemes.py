"""citation_module (corpus.yml: plugins.citation_module) — this corpus's citation
formats, registered with the toolkit's resolve_citation dispatcher at import time.

Two families of scheme live here, and they behave very differently on purpose.

LOCAL — schedules held in this corpus. These resolve to real document ids.

CROSS-CORPUS — OAR chapter 166 and ORS 192. These deliberately resolve to NOTHING
here, because the documents genuinely are not in this corpus: the general retention
schedules live verbatim in OregonAI/executive-regulatory-frameworks and are referenced
rather than copied (see AGENTS.md, "Scope boundary").

The toolkit has no remote resolution yet. The lazy option would be to leave those
citations unregistered and let an agent receive a bare "could not resolve". That is
true but useless, and worse, it reads as "this citation is bad" when the citation is
perfectly good and simply lives next door. So they ARE registered, with resolvers that
return no candidates plus a `note` explaining exactly where the document is and how to
reach it. `register_scheme` supports this directly: a resolver may return
`(candidates, note)`, and the note is surfaced whether or not resolution succeeded.

When toolkit remote resolution lands, these resolvers are the seam to change: keep the
patterns, swap the bodies for a real lookup.
"""
import re

from corpus_toolkit.mcp.framework import register_scheme

# The sibling corpus that holds the general schedules and the statutory spine.
POLICY_CORPUS = "OregonAI/executive-regulatory-frameworks"
POLICY_URL = "https://github.com/OregonAI/executive-regulatory-frameworks"


def _elsewhere(kind: str, cite: str, path_hint: str):
    """A resolution that correctly finds nothing locally, and says why."""
    return [], (
        f"{cite} is {kind}. It is NOT in this corpus by design — this corpus holds only "
        f"agency SPECIAL schedules; the general schedules and statutes live in "
        f"{POLICY_CORPUS} at `{path_hint}`. Look it up there: {POLICY_URL}. "
        "(Cross-corpus citation resolution is not implemented in the toolkit yet, so "
        "this pointer is textual rather than a resolved document.)")


# --- cross-corpus: OAR chapter 166, the GENERAL retention schedules -----------------
# Matched narrowly to chapter 166. An OAR citation from any other chapter is a
# different kind of reference and should not be claimed by this scheme.
def _resolve_oar_166(m):
    rule = m.group("num")
    div = rule.split("-")[1]
    return _elsewhere("a general records-retention rule (OAR chapter 166)",
                      f"OAR {rule}", f"rules/166/{div}/oar-{rule}.md")


register_scheme("oar-166-general-schedule",
                r"(?:OAR\s*)?(?P<num>166-\d{3}-\d{4})\s*$",
                resolver=_resolve_oar_166)


# --- cross-corpus: ORS 192, the public-records statutes -----------------------------
def _resolve_ors_192(m):
    sec = m.group("num")
    return _elsewhere("a public-records statute (ORS chapter 192)",
                      f"ORS {sec}", f"statutes/ors-{sec.lower()}.md")


register_scheme("ors-192-public-records",
                r"(?:ORS\s*)?(?P<num>192\.\d{3})\s*$",
                resolver=_resolve_ors_192)


# --- local: a whole agency special schedule -----------------------------------------
# Document ids are `schedule-<agency-slug>`, mirroring the upstream PDF filename
# (schedule-das.pdf -> schedule-das), so an id is checkable against its source URL by
# eye rather than through a mapping table.
#
# `register_scheme` compiles patterns with no flags, so case-insensitivity has to be
# inline: people write "DAS Special Schedule", not "das special schedule". Resolvers
# rather than id_template because the slug must be lowercased to match the id, and a
# format string cannot do that.
def _slug_to_id(m):
    return [f"schedule-{m.group('slug').lower()}"]


register_scheme("special-schedule",
                r"(?i)^(?P<slug>[a-z][a-z0-9-]{1,})\s+special\s+schedule\s*$",
                resolver=_slug_to_id)

register_scheme("special-schedule-slug",
                r"(?i)^schedule-(?P<slug>[a-z][a-z0-9-]{2,})\s*$",
                resolver=_slug_to_id)


# --- local: an individual retention ITEM inside a schedule --------------------------
# The seed spec asked for a `retention-item` scheme so an agent can cite "how long do I
# keep X" precisely rather than pointing at a 96-page PDF.
#
# Item numbering, from the real documents: a three-digit number and a record-series
# title, then an indented retention clause, with lettered sub-items where a series has
# several dispositions:
#
#     014 State E-Governance Board Records
#     (a) Retain final reports, and meeting agendas, attachments, and recaps 20 years, destroy
#     (b) Retain formation and organizational records 2 years after the life of the board, destroy
#
# Items are NOT separate documents in this corpus — one document per schedule, matching
# how the Archives Division publishes and revises them. So an item citation resolves to
# the SCHEDULE that contains it, with the item number carried in the note. That is the
# truthful answer: the resolver knows which document holds the item, and does not
# pretend to a granularity the corpus does not store.
def _resolve_item(m):
    slug = m.group("slug").lower()
    item = m.group("item")
    return [f"schedule-{slug}"], (
        f"Item {item} of the {slug} special schedule. Items are not stored as separate "
        f"documents — open `schedule-{slug}` and find the entry numbered {item}; its "
        "retention and disposition are stated in the clause directly beneath the record "
        "series title.")


register_scheme("retention-item",
                r"(?i)^(?:schedule-)?(?P<slug>[a-z][a-z0-9-]{1,}?)"
                r"(?:\s+special\s+schedule)?[\s,]+item\s+(?P<item>\d{3})\s*$",
                resolver=_resolve_item)
