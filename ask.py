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

        # 3a. List mode — skip extraction, aggregate entities, return passages.
        if query["is_list_query"]:
            entities = self._aggregate_entities(passages, top_n=15)
            return {
                "question":           question,
                "mode":               mode,
                "list_mode":          True,
                "query":              query,
                "answer":             "",          # no single span; consumers should render passages + entities
                "confidence":         0.0,
                "type_match":         True,
                "source_passage":     passages[0] if passages else {},
                "retrieved_passages": passages,
                "aggregated_entities": entities,    # list of {text, label, count}
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
            "aggregated_entities": [],
            "all_candidates":     result["all_candidates"],
        }

    def _aggregate_entities(self, passages, top_n=15):
        """Run NER over the retrieved passages, collect typed-entity mentions,
        dedupe case-insensitively, count, and return the top-N most frequent.

        Restricted to entity types useful in a 'list things in X' answer:
        FAC (buildings, museums), LOC (geographic features), GPE (cities),
        ORG (institutions, teams, companies), EVENT, WORK_OF_ART, PRODUCT.

        We re-NER at query time rather than reading entities from the
        on-disk passages because the retriever's metadata is intentionally
        lightweight (no entities/POS) — a freshly tagged 5-passage list takes
        ~150 ms with the already-loaded spaCy model, which is fine here.
        """
        from collections import Counter
        WANTED = {"FAC", "LOC", "GPE", "ORG", "EVENT", "WORK_OF_ART", "PRODUCT"}

        counts = Counter()
        first_label = {}
        for p in passages:
            doc = self.nlp(p["text"])
            for ent in doc.ents:
                if ent.label_ not in WANTED:
                    continue
                key = ent.text.strip().lower()
                if len(key) < 2:
                    continue
                counts[key] += 1
                if key not in first_label:
                    first_label[key] = (ent.text.strip(), ent.label_)

        return [
            {"text": first_label[k][0], "label": first_label[k][1], "count": c}
            for k, c in counts.most_common(top_n)
        ]


def _format_human(payload):
    """Pretty CLI print — readable, preserves structure for debugging."""
    q = payload["query"]
    lines = [
        f"Q: {payload['question']}",
        f"   city: {q['detected_city']}  (conf {q['city_confidence']:.2f})  "
        f"type: {q['question_type']}  mode: {payload['mode']}",
    ]

    # List-mode rendering: skip the single-span "answer" (always empty),
    # show the aggregated entities and a brief summary of the retrieved
    # passages. Honest "here's what I found" instead of forcing a wrong span.
    if payload.get("list_mode"):
        lines.append("")
        lines.append("List question detected — extractive QA can't synthesize lists.")
        lines.append("Showing what was found across the most relevant passages:")
        if payload.get("aggregated_entities"):
            lines.append("")
            lines.append("Mentioned across passages (top entities by frequency):")
            for e in payload["aggregated_entities"]:
                lines.append(f"  · {e['text']:30s} [{e['label']}]  ×{e['count']}")
        lines.append("")
        lines.append(f"Top {len(payload['retrieved_passages'])} passages:")
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
