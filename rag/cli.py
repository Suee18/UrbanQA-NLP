"""CLI — ask the Germany RAG system a question.

Usage:
    python -m rag.cli "How many people live in Munich?"
    python -m rag.cli "What river runs through Cologne?" --json

Requires: a built Qdrant index (python -m rag.build_index) and a .env.
"""

import argparse
import json

from rag.graph import build_app


def main():
    parser = argparse.ArgumentParser(description="Germany RAG — ask a question.")
    parser.add_argument("question", type=str, help="Your question about a German city")
    parser.add_argument("--json", action="store_true", help="Emit JSON only")
    args = parser.parse_args()

    app = build_app()
    result = app.ask(args.question)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    print()
    print(f"Q (original) : {result['question']}")
    print(f"Q (rewritten): {result['rewritten_query']}")
    print()
    print(f"A: {result['answer']}")
    print()
    srcs = ", ".join(
        f"{s['location']}" for s in result["sources"] if s.get("location")
    )
    if srcs:
        print(f"Sources: {srcs}")
    print(f"(retrieved {len(result['retrieved_docs'])} passages)")


if __name__ == "__main__":
    main()
