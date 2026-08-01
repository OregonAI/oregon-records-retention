# Oregon Records Retention — RETIRED

> ## 🪦 This corpus has moved
>
> Its **76 Secretary of State Archives Division special records-retention schedules** now live
> in **[executive-regulatory-frameworks](https://github.com/OregonAI/executive-regulatory-frameworks)**,
> as `doc_type: schedule` under `agencies/<agency>/schedules/`, filed by the agency each
> schedule binds.
>
> | | |
> |---|---|
> | MCP endpoint | `https://oregonai.morficflux.com/executive-regulatory-frameworks/mcp` |
> | Site | https://oregonai.github.io/executive-regulatory-frameworks/ |
> | The old endpoint | still answers, and tells you the same thing |
>
> This repository is **archived**: read-only, kept so its history and every URL that ever
> pointed here keep resolving. Nothing here is updated any more.

## Why it was folded in

A separate repository for 76 documents bought a second deployment, a second Pages site, a
second MCP server and a cross-corpus citation hop. The schedules are agency-level instruments —
the class ERF already models as policy, procedure, standard and manual.

**The graph settled it.** All 440 of this corpus's edges were *external*: `related` targets
that were OAR 166 citation strings resolving out to ERF. Folded in, **430 of 440 (97.7%)**
became edges to real local documents. The cross-corpus hop was the only thing the separation
bought, and it was a cost, not a feature.

The 10 that still dangle point at `OAR 166-300-0017` and `-0003`, which ERF does not hold.
Whether that is a coverage gap or a repeal is deliberately **not** asserted.

## What is NOT here, and never was

County, city and special-district special schedules. The Archives Division **does not publish
them** — its own page scopes special schedules to *"a particular state agency"*, and the
per-body PDF convention holds no local bodies. Counties are covered for the *general* layer by
**OAR 166-150**, the County and Special District schedule, which lives in ERF. That was
verified rather than assumed; see `AGENTS.md` for the evidence.

## History

Everything below the fold is preserved as it was at retirement. `PLAN.md` Phase 9 in the
platform repo records the decision.

---

# Oregon Records Retention — Agency Special Schedules

> ## ⚠️ NON-AUTHORITATIVE — AI-friendly reference only
> Curated copies/summaries, not official text. Always verify at the
> authoritative source linked in each document. See [DISCLAIMER.md](DISCLAIMER.md).

Part of the OregonAI civic corpus platform
([reference architecture](https://github.com/OregonAI/corpus-toolkit)).
Archetype: **document**. MCP interface: contract v1.

| Entry point | For |
|---|---|
| [llms.txt](llms.txt) | Machine-readable index — AI agents start here |
| [AGENTS.md](AGENTS.md) | Agent rules and anti-fabrication requirements |
| [STATUS.md](STATUS.md) | Generated health: freshness, coverage, drift |
| `_meta/corpus.yml` | Corpus configuration |

## License
Content (curated government material): CC0-1.0. Tooling, structure,
metadata: MIT.
