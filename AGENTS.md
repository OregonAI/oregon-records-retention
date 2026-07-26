# AGENTS.md — Oregon Records Retention — Agency Special Schedules

Corpus of the OregonAI civic corpus platform. Archetype: document.
Read `_meta/corpus.yml` for configuration; the platform rules live in
OregonAI/corpus-toolkit `docs/`.

## Purpose
Non-authoritative, AI-friendly mirror of the agency-specific *special* records retention schedules published by the Oregon Secretary of State Archives Division.
Never a source of truth — every answer must cite and link the
authoritative source.

## Scope boundary — READ THIS BEFORE ADDING ANYTHING

Oregon's retention rules come in two layers, and **this corpus holds only one of
them**:

| layer | where it lives | example |
|---|---|---|
| **General** schedules — apply to every agency of a class | **NOT HERE.** OAR chapter 166, all 15 divisions, 210 rules, already verbatim in [OregonAI/executive-regulatory-frameworks](https://github.com/OregonAI/executive-regulatory-frameworks) | OAR 166-300-0040 (state agency personnel records) |
| **Special** schedules — one agency's own record series | **HERE** | Department of Administrative Services special schedule |

**Never copy an OAR 166 rule into this corpus.** Reference it. Two divergent
copies of a retention period is precisely the failure a records corpus must not
produce — someone destroys a record on the strength of the stale one. The
general schedules are already ingested, verbatim, at rule granularity; there is
nothing to gain and a real hazard in duplicating them.

A special schedule *supplements* the general schedule for its agency: where a
record series is not covered generally, the agency's special schedule governs.
So the two layers must be read together, and this corpus's job is to hold the
half that OAR does not publish as rules.

Cross-corpus references (to OAR 166 rules, to ORS 192) are written as
**citation strings**, e.g. `ORS 192.311`, not as local document ids. The
toolkit's frontmatter validator deliberately tolerates citation-shaped
relationship targets as forward references to sibling corpora — it warns rather
than failing. Remote *resolution* of those citations does not exist yet and is
tracked as toolkit work; until it lands, a citation string is an honest
"look this up over there", not a broken link.

## Hard rules (anti-fabrication)
1. Never write content that does not exist in the pinned source. Source
   unreachable or unparseable → insert
   `<!-- TODO: human verification required -->` and stop. Never
   reconstruct from model knowledge.
2. `## Full text` sections are verbatim only. Curator content is confined
   to `## At a glance`, `## Curator notes`, `## Cross-references`.
3. Third-party copyrighted material: summary + official link only.
4. Never invent or infer a citation. Unresolvable → say so.
5. Live-data answers (api/hybrid) must carry the executed query and
   timestamp.
6. All changes via PR. Do not set `last_verified`/`verified_by` — the
   human reviewer does at approval.
7. Update this knowledge body's CHANGELOG.md in the same PR as content
   changes.

## Workflow
Discovery → human-approved source manifest → ingestion → human-reviewed
PR. See toolkit `docs/replication-guide.md`.
