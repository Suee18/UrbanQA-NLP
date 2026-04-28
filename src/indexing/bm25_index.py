import json
import os
import pickle
import yaml
from rank_bm25 import BM25Okapi


def load_config(config_path="configs/config.yaml"):
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_all_passages(processed_dir, cities):
    """Flatten every city's processed passages into one list.

    Each passage already has: passage_id, city, source, text, sentences,
    raw_tokens, normalized_tokens, entities, pos_tags.
    """
    all_passages = []
    missing = []

    for city in cities:
        slug = city.lower().replace(" ", "_")
        path = os.path.join(processed_dir, f"{slug}_passages.json")

        if not os.path.exists(path):
            missing.append(city)
            continue

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        all_passages.extend(data["passages"])

    if missing:
        print(f"  Warning — missing processed files for: {missing}")

    return all_passages


def build_bm25(passages):
    """BM25 over normalized tokens — stopwords removed, lemmatized, lowercased."""
    tokenized_corpus = [p["normalized_tokens"] for p in passages]
    return BM25Okapi(tokenized_corpus)


def save_bm25(bm25, passages, out_path):
    """Persist BM25 model + lightweight metadata so the retriever can rehydrate
    top-k hits without re-reading 20 city files (the heavy entity/POS arrays stay on disk).
    """
    meta = [
        {
            "passage_id": p["passage_id"],
            "city":       p["city"],
            "source":     p["source"],
            "text":       p["text"],
        }
        for p in passages
    ]

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "wb") as f:
        pickle.dump({"bm25": bm25, "meta": meta}, f)


def load_bm25(path):
    with open(path, "rb") as f:
        bundle = pickle.load(f)
    return bundle["bm25"], bundle["meta"]


if __name__ == "__main__":
    config = load_config()
    cities = config["cities"]
    processed_dir = config["paths"]["processed_data"]
    indexes_dir = config["paths"]["indexes"]
    out_path = os.path.join(indexes_dir, "bm25.pkl")

    print(f"Loading passages from {processed_dir}...")
    passages = load_all_passages(processed_dir, cities)
    print(f"  {len(passages)} passages across {len(cities)} cities")

    print("Building BM25 index...")
    bm25 = build_bm25(passages)

    print(f"Saving to {out_path}...")
    save_bm25(bm25, passages, out_path)

    size_mb = os.path.getsize(out_path) / (1024 * 1024)
    print(f"Done. Index size: {size_mb:.1f} MB")
