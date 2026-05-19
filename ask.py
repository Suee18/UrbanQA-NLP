"""UrbanQA single-call CLI — ask a question, get an answer.

This is the canonical entry point. The `UrbanQA` class exposes one method,
`answer(question) -> dict`, and that dict is fully JSON-serializable. Every
downstream surface (this CLI, the Streamlit demo, the future Unreal/UDP
server) is a thin wrapper over that single method.

Usage:
    python ask.py "When was Cairo founded?"
    python ask.py "When was Cairo founded?" --mode dense
    python ask.py "When was Cairo founded?" --json
"""

import argparse
import json
import sys
import os

# Make src.* importable when running as a script
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.retrieval.query_processor import (
    process_query, load_spacy, _build_alias_lookup, load_config,
)
from src.retrieval.retriever import Retriever
from src.qa.extractor import AnswerExtractor
from src.qa.list_aggregator import aggregate_list_results


class UrbanQA:
    """Holds models in memory across many queries.

    The QA core. JSON-only outputs so the same call serves CLI, Streamlit,
    and a socket server without any payload reshaping.
    """

    def __init__(self, config=None, mode="hybrid", load_extractor=True):
        self.config = config or load_config()
        self.cities = self.config["cities"]
        self.mode = mode

        print("Loading spaCy...")
        self.nlp = load_spacy()
        self.alias_lookup = _build_alias_lookup(self.cities)

        self.retriever = Retriever(self.config)
        self.extractor = AnswerExtractor() if load_extractor else None

    def answer(self, question, mode=None, top_k=5, retrieve_k=20,
               rerank=True, read_k=3, list_top_k=8):
        """End-to-end QA over one question. Returns JSON-serializable dict.

        Two flows: extractive (default) returns one span; list mode returns
        the retrieved passages + an aggregated entity list. List mode triggers
        when query["is_list_query"] is True (detected by the query processor
        from phrasing like "top 10 places", "what are popular sights", etc.).
        Extractive QA can't synthesize a list across passages — list mode is
        an honest "here's what I found" instead of a forced wrong span.
        """
        mode = mode or self.mode

        # 1. Query processing
        query = process_query(question, self.cities, self.nlp, self.alias_lookup)

        # 2. Retrieval — list mode wants more passages so the entity aggregation
        #    has more material to work with.
        effective_top_k = list_top_k if query["is_list_query"] else top_k
        passages = self.retriever.retrieve(
            question,
            city=query["detected_city"],
            mode=mode,
            top_k=effective_top_k,
            retrieve_k=retrieve_k,
            rerank=rerank,
        )

        # 3a. List mode — skip extraction, build a ranked evidenced item list.
        if query["is_list_query"]:
            items = aggregate_list_results(
                passages, self.nlp, query,
                alias_lookup=self.alias_lookup, top_n=10,
            )
            return {
                "question":           question,
                "mode":               mode,
                "list_mode":          True,
                "query":              query,
                "answer":             "",          # no single span; consumers should render items + passages
                "confidence":         0.0,
                "type_match":         True,
                "source_passage":     passages[0] if passages else {},
                "retrieved_passages": passages,
                "list_items":         items,        # ranked items: name, label, score, mentions, aliases, snippet, passage_id, source, passage_rank
                "aggregated_entities": items,        # legacy alias for older consumers
                "all_candidates":     [],
            }

        # 3b. Standard extractive flow
        result = self.extractor.extract(
            question,
            passages,
            expected_types=query["expected_entity_types"],
            read_k=read_k,
        )

        return {
            "question":           question,
            "mode":               mode,
            "list_mode":          False,
            "query":              query,
            "answer":             result["answer"],
            "confidence":         result["confidence"],
            "type_match":         result["type_match"],
            "source_passage":     result["source_passage"],
            "retrieved_passages": passages,
            "list_items":         [],
            "aggregated_entities": [],
            "all_candidates":     result["all_candidates"],
        }


def _format_human(payload):
    """Pretty CLI print — readable, preserves structure for debugging."""
    q = payload["query"]
    lines = [
        f"Q: {payload['question']}",
        f"   city: {q['detected_city']}  (conf {q['city_confidence']:.2f})  "
        f"type: {q['question_type']}  mode: {payload['mode']}",
    ]

    # List-mode rendering: ranked items with evidence snippets and source
    # citations. Honest "here's what I found" instead of forcing a wrong span.
    if payload.get("list_mode"):
        lines.append("")
        lines.append("List question — returning ranked items with supporting evidence:")
        items = payload.get("list_items") or payload.get("aggregated_entities") or []
        if items:
            lines.append("")
            for i, it in enumerate(items, start=1):
                aliases = f"  (aka {', '.join(it['aliases'])})" if it.get("aliases") else ""
                lines.append(f"  {i:2d}. {it['name']}  [{it['label']}]"
                             f"  score={it['score']:.2f}  ×{it['mentions']}{aliases}")
                snippet = it.get("snippet", "").replace("\n", " ").strip()
                if len(snippet) > 220:
                    snippet = snippet[:217] + "…"
                lines.append(f"       \"{snippet}\"")
                lines.append(f"       — {it.get('passage_id', '?')} ({it.get('source', '?')}, rank {it.get('passage_rank', '?')})")
        else:
            lines.append("  (no entities surfaced from retrieved passages)")
        lines.append("")
        lines.append(f"Underlying passages ({len(payload['retrieved_passages'])}):")
        for p in payload["retrieved_passages"]:
            snippet = p["text"][:160].replace("\n", " ").strip()
            lines.append(f"  [{p['rank']}] {p['passage_id']}  ({p['source']})")
            lines.append(f"      {snippet}…")
        return "\n".join(lines)

    # Standard extractive flow
    lines.extend([
        "",
        f"A: {payload['answer']!r}",
        f"   confidence: {payload['confidence']:.3f}  type_match: {payload['type_match']}",
        "",
        f"Source [{payload['source_passage']['passage_id']}]:",
        f"   {payload['source_passage']['text']}",
    ])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="UrbanQA — ask a question.")
    parser.add_argument("question", type=str, help="Natural-language question")
    parser.add_argument("--mode", choices=["bm25", "dense", "hybrid"], default="hybrid")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--no-rerank", action="store_true")
    parser.add_argument("--json", action="store_true",
                        help="Emit JSON only — for piping into the future socket server")
    args = parser.parse_args()

    qa = UrbanQA(mode=args.mode)
    payload = qa.answer(
        args.question,
        mode=args.mode,
        top_k=args.top_k,
        rerank=not args.no_rerank,
    )

    if args.json:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print()
        print(_format_human(payload))


if __name__ == "__main__":
    main()
