"""Evaluation metrics — runs the system end-to-end against a gold QA set
and reports per-mode (bm25 / dense / hybrid) numbers for the report.

Metrics:
  - Exact Match  (EM)             — answer-quality, strict
  - Token F1                       — answer-quality, partial credit
  - Recall@k                       — retrieval quality (gold passage in top-k?)
  - MRR                            — retrieval quality (rank-weighted)

Gold QA file format (data/gold_qa/gold.jsonl) — one JSON object per line:
  {
    "id":           "001",
    "city":         "Cairo",
    "question":     "When was Cairo founded?",
    "answer":       "969",
    "answer_aliases": ["969 AD", "969 CE"],   # optional — extra valid answers
    "question_type": "when",                    # optional — for slicing
    "gold_passage_id": "Cairo_wiki_6"          # optional — needed for retrieval metrics
  }
"""

import json
import os
import re
import string
import yaml
from collections import Counter, defaultdict


def load_config(config_path="configs/config.yaml"):
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ── Answer-quality metrics ─────────────────────────────────────────────
# Standard SQuAD normalization: lowercase, strip punctuation, drop
# articles, collapse whitespace. Without this you'd mark "the Eiffel Tower"
# != "Eiffel tower" — meaningless for QA grading.
def normalize_answer(s):
    if not s:
        return ""
    s = s.lower()
    s = re.sub(r"\b(a|an|the)\b", " ", s)
    s = "".join(ch for ch in s if ch not in set(string.punctuation))
    s = re.sub(r"\s+", " ", s).strip()
    return s


def exact_match(pred, golds):
    """1 if pred matches ANY gold answer (after normalization), else 0.
    Multiple golds let us accept '969 AD' / '969 CE' as the same right answer."""
    pred_n = normalize_answer(pred)
    return float(any(pred_n == normalize_answer(g) for g in golds))


def token_f1(pred, golds):
    """Best per-token F1 across all gold variants. Standard SQuAD definition."""
    def f1_one(pred_tokens, gold_tokens):
        if not pred_tokens or not gold_tokens:
            return float(pred_tokens == gold_tokens)  # both empty == 1, one empty == 0
        common = Counter(pred_tokens) & Counter(gold_tokens)
        n_same = sum(common.values())
        if n_same == 0:
            return 0.0
        prec = n_same / len(pred_tokens)
        rec  = n_same / len(gold_tokens)
        return 2 * prec * rec / (prec + rec)

    pred_tokens = normalize_answer(pred).split()
    return max(f1_one(pred_tokens, normalize_answer(g).split()) for g in golds)


# ── Retrieval-quality metrics ──────────────────────────────────────────

def recall_at_k(retrieved_passage_ids, gold_passage_id, k):
    """1 if the gold passage shows up in the top-k retrieved, else 0."""
    if gold_passage_id is None:
        return None
    return float(gold_passage_id in retrieved_passage_ids[:k])


def reciprocal_rank(retrieved_passage_ids, gold_passage_id):
    """1 / rank-of-gold-passage. 0 if gold not retrieved at all."""
    if gold_passage_id is None:
        return None
    for i, pid in enumerate(retrieved_passage_ids, start=1):
        if pid == gold_passage_id:
            return 1.0 / i
    return 0.0


# Content-overlap variant: with sliding-window passages (window=3, stride=1),
# the gold answer often lives in passages adjacent to the labeled gold_passage_id.
# Strict-ID recall scores those retrievals as misses even though the system
# actually found the answer. Content-overlap recall checks whether the gold
# answer string appears in any retrieved passage's text — a more honest measure
# of whether retrieval worked.
def _answer_in_text(gold_answer, passage_text):
    return normalize_answer(gold_answer) in normalize_answer(passage_text)


def content_recall_at_k(retrieved_passages, golds, k):
    """1 if any gold answer string appears in any of the top-k retrieved passages."""
    for p in retrieved_passages[:k]:
        text = p.get("text", "")
        if any(_answer_in_text(g, text) for g in golds):
            return 1.0
    return 0.0


def content_reciprocal_rank(retrieved_passages, golds):
    """1 / rank-of-first-passage-containing-any-gold-answer. 0 if none do."""
    for i, p in enumerate(retrieved_passages, start=1):
        text = p.get("text", "")
        if any(_answer_in_text(g, text) for g in golds):
            return 1.0 / i
    return 0.0


# ── Gold loader ────────────────────────────────────────────────────────

def load_gold(path):
    """Read JSONL. Each line is one QA pair."""
    items = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def get_golds(item):
    """All accepted gold answers for one item (answer + answer_aliases)."""
    return [item["answer"]] + item.get("answer_aliases", [])


# ── End-to-end evaluation ─────────────────────────────────────────────

def evaluate_system(gold_items, retriever, extractor, query_processor_fn,
                    cities, nlp, alias_lookup, mode="hybrid",
                    top_k=5, retrieve_k=20, rerank=True, read_k=3,
                    type_penalty=None, vote_weight=None):
    """Run every gold question through the system and accumulate metrics.

    Returns:
      {
        "mode": str,
        "n_questions": int,
        "em": float,
        "f1": float,
        "recall@1/3/5/10": float,        # strict passage-ID; only items w/ gold_passage_id
        "mrr": float,                      # strict passage-ID
        "content_recall@1/3/5/10": float,  # gold answer substring in any retrieved passage
        "content_mrr": float,              # 1 / rank of first passage containing gold answer
        "by_question_type": { type: {em, f1, n}, ... },
        "by_city":          { city: {em, f1, n}, ... },
        "per_item":         [ { id, em, f1, recall@k, rr, content_recall@k, content_rr, predicted, ... }, ... ],
      }
    """
    per_item = []
    type_buckets = defaultdict(lambda: {"em": 0.0, "f1": 0.0, "n": 0})
    city_buckets = defaultdict(lambda: {"em": 0.0, "f1": 0.0, "n": 0})

    for item in gold_items:
        q = item["question"]
        golds = get_golds(item)
        gold_pid = item.get("gold_passage_id")

        # Use the gold-labeled city if present, else let query processor detect.
        if "city" in item:
            detected_city = item["city"]
            qproc = query_processor_fn(q, cities, nlp, alias_lookup)
            qproc["detected_city"] = detected_city
        else:
            qproc = query_processor_fn(q, cities, nlp, alias_lookup)
            detected_city = qproc["detected_city"]

        # Retrieve + extract
        passages = retriever.retrieve(
            q, city=detected_city, mode=mode,
            top_k=top_k, retrieve_k=retrieve_k, rerank=rerank,
        )
        extract_kwargs = {
            "expected_types": qproc["expected_entity_types"],
            "read_k": read_k,
        }
        if type_penalty is not None:
            extract_kwargs["type_penalty"] = type_penalty
        if vote_weight is not None:
            extract_kwargs["vote_weight"] = vote_weight
        result = extractor.extract(q, passages, **extract_kwargs)

        # Score
        em = exact_match(result["answer"], golds)
        f1 = token_f1(result["answer"], golds)
        retrieved_pids = [p["passage_id"] for p in passages]

        record = {
            "id":              item.get("id"),
            "question":        q,
            "city":            detected_city,
            "question_type":   item.get("question_type") or qproc["question_type"],
            "predicted":       result["answer"],
            "gold":            golds,
            "em":              em,
            "f1":              f1,
            "source_passage":  result["source_passage"]["passage_id"],
            "retrieved":       retrieved_pids,
        }
        if gold_pid is not None:
            record["recall@1"]  = recall_at_k(retrieved_pids, gold_pid, 1)
            record["recall@3"]  = recall_at_k(retrieved_pids, gold_pid, 3)
            record["recall@5"]  = recall_at_k(retrieved_pids, gold_pid, 5)
            record["recall@10"] = recall_at_k(retrieved_pids, gold_pid, 10)
            record["rr"]        = reciprocal_rank(retrieved_pids, gold_pid)

        record["content_recall@1"]  = content_recall_at_k(passages, golds, 1)
        record["content_recall@3"]  = content_recall_at_k(passages, golds, 3)
        record["content_recall@5"]  = content_recall_at_k(passages, golds, 5)
        record["content_recall@10"] = content_recall_at_k(passages, golds, 10)
        record["content_rr"]        = content_reciprocal_rank(passages, golds)

        per_item.append(record)

        # Slice buckets
        qt = record["question_type"]
        type_buckets[qt]["em"] += em
        type_buckets[qt]["f1"] += f1
        type_buckets[qt]["n"]  += 1

        city = record["city"] or "<unknown>"
        city_buckets[city]["em"] += em
        city_buckets[city]["f1"] += f1
        city_buckets[city]["n"]  += 1

    # Aggregate
    n = len(per_item)
    out = {
        "mode":         mode,
        "n_questions":  n,
        "em":           sum(r["em"] for r in per_item) / n,
        "f1":           sum(r["f1"] for r in per_item) / n,
    }

    with_gold_pid = [r for r in per_item if "rr" in r]
    if with_gold_pid:
        m = len(with_gold_pid)
        out["recall@1"]  = sum(r["recall@1"]  for r in with_gold_pid) / m
        out["recall@3"]  = sum(r["recall@3"]  for r in with_gold_pid) / m
        out["recall@5"]  = sum(r["recall@5"]  for r in with_gold_pid) / m
        out["recall@10"] = sum(r["recall@10"] for r in with_gold_pid) / m
        out["mrr"]       = sum(r["rr"]        for r in with_gold_pid) / m
        out["n_with_gold_passage"] = m

    # Content-overlap metrics are computed for every item (no gold_passage_id needed).
    out["content_recall@1"]  = sum(r["content_recall@1"]  for r in per_item) / n
    out["content_recall@3"]  = sum(r["content_recall@3"]  for r in per_item) / n
    out["content_recall@5"]  = sum(r["content_recall@5"]  for r in per_item) / n
    out["content_recall@10"] = sum(r["content_recall@10"] for r in per_item) / n
    out["content_mrr"]       = sum(r["content_rr"]        for r in per_item) / n

    out["by_question_type"] = {
        qt: {"em": v["em"]/v["n"], "f1": v["f1"]/v["n"], "n": v["n"]}
        for qt, v in type_buckets.items()
    }
    out["by_city"] = {
        c: {"em": v["em"]/v["n"], "f1": v["f1"]/v["n"], "n": v["n"]}
        for c, v in city_buckets.items()
    }
    out["per_item"] = per_item

    return out


def save_results(results, out_path):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    # Run all three modes (bm25 / dense / hybrid) and print the comparison
    # table. Saves per-mode JSON results for downstream error analysis.
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from src.retrieval.retriever import Retriever
    from src.retrieval.query_processor import process_query, load_spacy, _build_alias_lookup
    from src.qa.extractor import AnswerExtractor

    config = load_config()
    cities = config["cities"]
    gold_path = os.path.join(config["paths"]["gold_qa"], "gold.jsonl")
    out_dir   = os.path.join(config["paths"]["gold_qa"], "results")

    if not os.path.exists(gold_path):
        print(f"No gold set found at {gold_path}. Create one before running eval.")
        sys.exit(1)

    print(f"Loading {gold_path}...")
    gold = load_gold(gold_path)
    print(f"  {len(gold)} gold QA pairs")

    print("Loading models...")
    nlp = load_spacy()
    alias_lookup = _build_alias_lookup(cities)
    retriever = Retriever(config)
    extractor = AnswerExtractor()

    results_summary = []
    for mode in ("bm25", "dense", "hybrid"):
        print(f"\n=== Evaluating mode={mode} ===")
        try:
            results = evaluate_system(
                gold, retriever, extractor, process_query,
                cities, nlp, alias_lookup, mode=mode, rerank=(mode == "hybrid"),
            )
        except (FileNotFoundError, RuntimeError) as e:
            print(f"  skipped: {e}")
            continue

        save_results(results, os.path.join(out_dir, f"{mode}.json"))
        print(f"  EM={results['em']:.3f}  F1={results['f1']:.3f}", end="")
        if "recall@5" in results:
            print(f"  R@5={results['recall@5']:.3f}  MRR={results['mrr']:.3f}", end="")
        print(f"  cR@5={results['content_recall@5']:.3f}  cMRR={results['content_mrr']:.3f}")
        results_summary.append({k: results[k] for k in results if k not in ("per_item",)})

    print("\n=== Summary ===")
    print(json.dumps(results_summary, indent=2))
