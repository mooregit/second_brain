#!/usr/bin/env python3
from __future__ import annotations

import argparse

from secondbrain_client import SecondBrainClient, die, print_json


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask/search Second Brain and print source-linked context.")
    parser.add_argument("query", help="Question or search query.")
    parser.add_argument("--json", action="store_true", help="Print raw JSON response.")
    args = parser.parse_args()

    client = SecondBrainClient.from_env()
    response = client.post("/ask", {"question": args.query})
    if args.json:
        print_json(response)
        return
    print_markdown(response)


def print_markdown(response: dict) -> None:
    if not response:
        die("No response returned.")
    print("# Second Brain Search")
    print()
    print("## Answer")
    print()
    print(response.get("answer") or "")
    print()
    print("## Sources")
    print()
    for source in response.get("sources", []):
        title = source.get("title") or source.get("owner_type") or "Source"
        raw_item_id = source.get("raw_item_id") or ""
        score = source.get("score")
        score_text = f" score={score:.3f}" if isinstance(score, (int, float)) else ""
        print(f"- {title} (`raw_item_id={raw_item_id}`{score_text})")


if __name__ == "__main__":
    main()
