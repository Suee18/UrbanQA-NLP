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
               rerank=True, read_k=3):
        """End-to-end QA over one question. Returns JSON-serializable dict."""
        mode = mode or self.mode

        # 1. Query processing
        query = process_query(question, self.cities, self.nlp, self.alias_lookup)

        # 2. Retrieval
        passages = self.retriever.retrieve(
            question,
            city=query["detected_city"],
            mode=mode,
            top_k=top_k,
            retrieve_k=retrieve_k,
            rerank=rerank,
        )

        # 3. Answer extraction
        result = self.extractor.extract(
            question,
            passages,
            expected_types=query["expected_entity_types"],
            read_k=read_k,
        )

        # 4. Assemble unified payload — what every UI surface consumes
        return {
            "question":         question,
            "mode":             mode,
            "query":            query,
            "answer":           result["answer"],
            "confidence":       result["confidence"],
            "type_match":       result["type_match"],
            "source_passage":   result["source_passage"],
            "retrieved_passages": passages,
            "all_candidates":   result["all_candidates"],
        }


def _format_human(payload):
    """Pretty CLI print — readable, preserves structure for debugging."""
    q = payload["query"]
    lines = [
        f"Q: {payload['question']}",
        f"   city: {q['detected_city']}  (conf {q['city_confidence']:.2f})  "
        f"type: {q['question_type']}  mode: {payload['mode']}",
        "",
        f"A: {payload['answer']!r}",
        f"   confidence: {payload['confidence']:.3f}  type_match: {payload['type_match']}",
        "",
        f"Source [{payload['source_passage']['passage_id']}]:",
        f"   {payload['source_passage']['text']}",
    ]
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
