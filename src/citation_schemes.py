"""citation_module (corpus.yml: plugins.citation_module) — this corpus's citation
formats, registered with the toolkit's resolve_citation dispatcher at import time.

Two families of scheme live here, and they behave very differently on purpose.

LOCAL — schedules held in this corpus. These resolve to real document ids.

CROSS-CORPUS — OAR chapter 166 and ORS 192. The documents genuinely are not in this
corpus: the general retention schedules live verbatim in
OregonAI/executive-regulatory-frameworks and are referenced rather than copied (see
AGENTS.md, "Scope boundary"). They are marked `corpus=` so the toolkit resolves them
against that corpus's published index and returns a real title and link.

Requires corpus-toolkit >= 1.1.0 and the `siblings:` block in corpus.yml. Before
v1.1.0 these schemes returned a textual pointer instead, because the alternative —
leaving them unregistered — gave an agent a bare "could not resolve", which is true
but useless and reads as "this citation is bad" when the citation is good and simply
lives next door.

The failure mode is the part worth understanding. If the sibling's index cannot be
loaded, the toolkit reports the citation unresolved AND says the sibling was
unavailable, stating explicitly that this is not evidence the document is absent.
"We could not look" and "it is not there" are different answers. For a corpus about
what agencies may destroy and when, letting the first silently become the second is
the worst thing this code could do.
"""
import re

from corpus_toolkit.mcp.framework import register_scheme

# The sibling corpus that holds the general schedules and the statutory spine. The id
# must match an entry in corpus.yml's `siblings:` block — that is where its published
# index and web base live.
POLICY_CORPUS_ID = "executive-regulatory-frameworks"


# --- cross-corpus: OAR chapter 166, the GENERAL retention schedules -----------------
# `corpus=` (toolkit >= 1.1.0) tells resolve_citation these candidate ids live in the
# sibling declared under `siblings:` in corpus.yml. It resolves them against that
# corpus's published index and returns a real title and URL, rather than the textual
# pointer this file emitted before v1.1.0.
#
# What the toolkit does when the sibling cannot be reached matters more than the happy
# path: it reports the citation as unresolved AND says the sibling was unavailable,
# explicitly noting that this is not evidence the document is absent. "We could not
# look" and "it is not there" are different answers, and a records corpus must never
# let the first quietly become the second.
#
# Matched narrowly to chapter 166. An OAR citation from any other chapter is a
# different kind of reference and is not claimed by this scheme.
def _oar_166_id(m):
    return [f"oar-{m.group('num')}"]


register_scheme("oar-166-general-schedule",
                r"(?:OAR\s*)?(?P<num>166-\d{3}-\d{4})\s*$",
                resolver=_oar_166_id,
                corpus=POLICY_CORPUS_ID)


# --- cross-corpus: ORS 192, the public-records statutes -----------------------------
def _ors_192_id(m):
    return [f"ors-{m.group('num').lower()}"]


register_scheme("ors-192-public-records",
                r"(?:ORS\s*)?(?P<num>192\.\d{3})\s*$",
                resolver=_ors_192_id,
                corpus=POLICY_CORPUS_ID)


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
