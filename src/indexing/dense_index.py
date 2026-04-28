import json
import os
import yaml
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer


MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"
EMBED_DIM = 768
BATCH_SIZE = 64


def load_config(config_path="configs/config.yaml"):
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_all_passages(processed_dir, cities):
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


def encode_passages(passages, model):
    """L2-normalized float32 vectors so inner product == cosine similarity."""
    texts = [p["text"] for p in passages]
    vectors = model.encode(
        texts,
        batch_size=BATCH_SIZE,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    ).astype("float32")
    return vectors


def build_faiss(vectors):
    """Flat IP index — exact search, no training needed at this scale (~20k vectors)."""
    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)
    return index


def save_index(index, passages, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    faiss.write_index(index, os.path.join(out_dir, "dense.faiss"))

    meta = [
        {
            "passage_id": p["passage_id"],
            "city":       p["city"],
            "source":     p["source"],
            "text":       p["text"],
        }
        for p in passages
    ]
    with open(os.path.join(out_dir, "dense_meta.json"), "w", encoding="utf-8") as f:
        json.dump({"model": MODEL_NAME, "dim": EMBED_DIM, "passages": meta}, f, ensure_ascii=False)


def load_index(out_dir):
    index = faiss.read_index(os.path.join(out_dir, "dense.faiss"))
    with open(os.path.join(out_dir, "dense_meta.json"), "r", encoding="utf-8") as f:
        meta = json.load(f)
    return index, meta["passages"]


if __name__ == "__main__":
    config = load_config()
    cities = config["cities"]
    processed_dir = config["paths"]["processed_data"]
    indexes_dir = config["paths"]["indexes"]

    print(f"Loading passages from {processed_dir}...")
    passages = load_all_passages(processed_dir, cities)
    print(f"  {len(passages)} passages across {len(cities)} cities")

    print(f"Loading model {MODEL_NAME}...")
    model = SentenceTransformer(MODEL_NAME)

    print("Encoding passages...")
    vectors = encode_passages(passages, model)
    print(f"  vectors shape: {vectors.shape}")

    print("Building FAISS index...")
    index = build_faiss(vectors)

    print(f"Saving to {indexes_dir}...")
    save_index(index, passages, indexes_dir)

    faiss_size = os.path.getsize(os.path.join(indexes_dir, "dense.faiss")) / (1024 * 1024)
    print(f"Done. FAISS index: {faiss_size:.1f} MB")
