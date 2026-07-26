#!/usr/bin/env python3
"""Build _meta/graph.json — the node/edge artifact the toolkit reads.

The toolkit only ever READS this file; every corpus is responsible for producing its
own. Without it `resolve_citation`, `graph_neighbors` and `authority_chain` return
nothing, and `corpus-validate-frontmatter --changed` loses its resolution universe.

This corpus's graph is deliberately thin, and the reason is the scope boundary in
AGENTS.md. A special schedule's references point almost entirely OUT of this corpus —
at OAR chapter 166 general-schedule rules that live in
OregonAI/executive-regulatory-frameworks. Those are stored as citation strings, not
local ids, because copying them here is the one thing a records corpus must not do.

So the edges are emitted with the citation string as the target. They are real
references and worth traversing, but `to` will not match any node in this graph. That
is accurate rather than broken: the reference genuinely leaves this corpus. Anything
consuming the graph should treat an unresolvable `to` as "look this up in the sibling
corpus" — which is exactly what src/citation_schemes.py tells a caller who resolves
one of these citations.

  python3 src/build_graph.py           # write _meta/graph.json
  python3 src/build_graph.py --check   # exit 1 if stale (CI)
"""
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "_meta/graph.json"
SCHEDULES = ROOT / "schedules"

_FM = re.compile(r"\A---\n(.*?)\n---\n", re.S)


def frontmatter(path: Path) -> dict:
    m = _FM.match(path.read_text(encoding="utf-8"))
    if not m:
        raise SystemExit(f"{path}: no YAML frontmatter")
    return yaml.safe_load(m.group(1))


def build() -> dict:
    nodes, edges = [], []
    for path in sorted(SCHEDULES.glob("*.md")):
        fm = frontmatter(path)
        nodes.append({"id": fm["id"], "title": fm["title"], "doc_type": fm["doc_type"],
                      "path": str(path.relative_to(ROOT))})
        for target in (fm.get("relationships") or {}).get("related") or []:
            edges.append({"from": fm["id"], "type": "related", "to": target})
    local = {n["id"] for n in nodes}
    return {
        "note": ("Nodes are this corpus's schedules. Edges are the general-schedule rules "
                 "each schedule cites; their `to` is an OAR CITATION STRING that resolves "
                 "in OregonAI/executive-regulatory-frameworks, not a node here — see "
                 "AGENTS.md 'Scope boundary'."),
        "n_nodes": len(nodes),
        "n_edges": len(edges),
        "n_edges_external": sum(1 for e in edges if e["to"] not in local),
        "nodes": nodes,
        "edges": edges,
    }


def main():
    graph = build()
    text = json.dumps(graph, ensure_ascii=False, indent=1) + "\n"
    if "--check" in sys.argv:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != text:
            print("_meta/graph.json is stale — run: python3 src/build_graph.py")
            sys.exit(1)
        print("_meta/graph.json is current.")
        return
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}: {graph['n_nodes']} nodes, {graph['n_edges']} edges "
          f"({graph['n_edges_external']} pointing to the sibling corpus)")


if __name__ == "__main__":
    main()
