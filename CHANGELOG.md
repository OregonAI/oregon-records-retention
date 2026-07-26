# Changelog — Oregon Records Retention — Agency Special Schedules

Keep a Changelog format; ISO dates. Change types: Added, Source-Updated,
Superseded, Repealed, Removed, Verified, Fixed, Security.
Repo-curation dates only — official effective dates live in frontmatter.

## [Unreleased]

### Added
- 2026-07-25 — Initial ingestion of all 76 agency special records retention
  schedules named in `_meta/source-manifest.yml` (`src/ingest_schedules.py`):
  `schedules/<id>.md` plus paired `_meta/snapshots/<id>.pdf` (raw source) and
  `_meta/snapshots/<id>.txt` (extracted text, the hashed provenance artifact).
  Page furniture stripped is declared per document in `conversion_notes`;
  440 OAR chapter 166 general-schedule citations are recorded across the corpus
  as citation strings in `relationships.related`, never copied in (AGENTS.md,
  "Scope boundary"). `last_verified`/`verified_by` are intentionally empty —
  human verification has not happened yet.
