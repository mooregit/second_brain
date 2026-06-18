#!/usr/bin/env python3
import json
import sys
from urllib.request import urlopen


def main() -> int:
    term = sys.argv[1].lower() if len(sys.argv) > 1 else ""
    url = sys.argv[2] if len(sys.argv) > 2 else "http://secondbrain/api/graph"

    if not term:
        print("Usage: scripts/inspect-graph.py SEARCH_TERM [GRAPH_URL]")
        return 2

    with urlopen(url, timeout=10) as response:
        graph = json.load(response)

    print("Matching nodes:")
    for node in graph.get("nodes", []):
        if term in node.get("label", "").lower() or term in node.get("id", "").lower():
            print(json.dumps(node, indent=2, sort_keys=True))

    print("\nMatching edges:")
    for edge in graph.get("edges", []):
        edge_text = " ".join(
            [
                edge.get("id", ""),
                edge.get("source", ""),
                edge.get("target", ""),
                edge.get("label", ""),
                edge.get("relationship_type", ""),
            ]
        ).lower()
        if term in edge_text:
            print(json.dumps(edge, indent=2, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
