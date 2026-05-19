"""Sweep extractor hyperparameters against the gold set.

Tunes (type_penalty, vote_weight) on hybrid mode only — that's the production
config — and prints a small grid so we pick the best point. Loads models once
across the sweep so it's cheap.
"""

import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.evaluation.metrics import (
    load_config, load_gold, evaluate_system,
)
from src.retrieval.retriever import Retriever
from src.retrieval.query_processor import process_query, load_spacy, _build_alias_lookup
from src.qa.extractor import AnswerExtractor


def main():
    config = load_config()
    cities = config["cities"]
    gold_path = os.path.join(config["paths"]["gold_qa"], "gold.jsonl")
    gold = load_gold(gold_path)

    nlp = load_spacy()
    alias_lookup = _build_alias_lookup(cities)
    retriever = Retriever(config)
    extractor = AnswerExtractor()

    # ── Sweep grid ──────────────────────────────────────────────────────
    # Also vary read_k so we can see whether the lift from read_k=5 is real
    # vs read_k=3; and include vote_weight=0.0 to isolate the ensemble effect.
    grid = []
    for rk in (3, 5):
        for tp in (0.3, 0.5, 0.7, 1.0):
            for vw in (0.0, 0.4):
                grid.append((rk, tp, vw))

    print(f"\nSweeping {len(grid)} (read_k, type_penalty, vote_weight) combos on hybrid mode, {len(gold)} questions...\n")
    print(f"{'rk':>3}  {'tp':>5}  {'vw':>5}  {'EM':>6}  {'F1':>6}  {'cR@5':>6}  {'cMRR':>6}")
    print("-" * 50)

    rows = []
    for rk, tp, vw in grid:
        results = evaluate_system(
            gold, retriever, extractor, process_query,
            cities, nlp, alias_lookup, mode="hybrid", rerank=True,
            read_k=rk, type_penalty=tp, vote_weight=vw,
        )

        rows.append({
            "read_k":       rk,
            "type_penalty": tp,
            "vote_weight":  vw,
            "em":           results["em"],
            "f1":           results["f1"],
            "content_recall@5": results.get("content_recall@5"),
            "content_mrr":  results.get("content_mrr"),
        })
        print(f"{rk:3d}  {tp:5.2f}  {vw:5.2f}  {results['em']:6.3f}  {results['f1']:6.3f}"
              f"  {results.get('content_recall@5', 0):6.3f}  {results.get('content_mrr', 0):6.3f}")

    # Best by F1 (more sensitive than EM at this scale)
    best = max(rows, key=lambda r: r["f1"])
    print("\n=== Best by F1 ===")
    print(json.dumps(best, indent=2))

    out_path = os.path.join(config["paths"]["gold_qa"], "results", "sweep_extractor.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"grid": rows, "best": best}, f, indent=2, ensure_ascii=False)
    print(f"\nSaved → {out_path}")


if __name__ == "__main__":
    main()
