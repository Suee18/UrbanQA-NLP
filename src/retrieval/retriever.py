"""Passage retrieval — runs at QA time on a processed query.

Three retrieval modes for the ablation in stage 8:
  - bm25    sparse keyword retrieval  (rank-bm25 over normalized tokens)
  - dense   semantic retrieval         (FAISS over mpnet embeddings)
  - hybrid  fused both via RRF, then optionally cross-encoder reranked

City filter is applied BEFORE scoring — if the query processor identified a
city, we only score passages from that city. Falls back to corpus-wide search
when no city was detected.

Returns a JSON-serializable list of hits so the same payload feeds Streamlit,
the eval loop, and the future Unreal/UDP server unchanged.
"""

import os
import pickle
import yaml
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer, CrossEncoder


# Same model as the index builder — must match for embedding compatibility.
DENSE_MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"
RERANKER_NAME    = "cross-encoder/ms-marco-MiniLM-L-6-v2"

# RRF constant from the original Cormack et al. paper. Insensitive within [10,100].
RRF_K = 60


def load_config(config_path="configs/config.yaml"):
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ── Index loaders ──────────────────────────────────────────────────────

def load_bm25(path):
    with open(path, "rb") as f:
        bundle = pickle.load(f)
    return bundle["bm25"], bundle["meta"]


def load_dense(out_dir):
    import json
    index = faiss.read_index(os.path.join(out_dir, "dense.faiss"))
    with open(os.path.join(out_dir, "dense_meta.json"), "r", encoding="utf-8") as f:
        meta = json.load(f)
    return index, meta["passages"]


# ── Query tokenization for BM25 ────────────────────────────────────────

def tokenize_query_for_bm25(question, nlp):
    """Match the corpus tokenization done in src/preprocessing/tokenizer.py:
    lemma + lowercase, drop stopwords, punctuation, and 1-char tokens."""
    doc = nlp(question)
    return [
        tok.lemma_.lower()
        for tok in doc
        if not tok.is_stop and not tok.is_punct and not tok.is_space
        and len(tok.text.strip()) > 1
    ]


# ── Single-mode searches ───────────────────────────────────────────────

def _city_mask(meta, city):
    """Boolean array — True for passages belonging to `city`. None means
    'corpus-wide' (no city filter)."""
    if city is None:
        return None
    return np.array([m["city"] == city for m in meta], dtype=bool)


def bm25_search(query_tokens, bm25, meta, city, top_k):
    scores = np.asarray(bm25.get_scores(query_tokens))

    mask = _city_mask(meta, city)
    if mask is not None:
        scores = np.where(mask, scores, -np.inf)

    top_idx = np.argsort(-scores)[:top_k]
    return [(int(i), float(scores[i])) for i in top_idx if scores[i] > -np.inf]


def dense_search(query_vec, index, meta, city, top_k):
    """Over-fetch then mask: FAISS Flat doesn't support per-query filtering, so
    we ask for more results than needed and drop the ones outside the city."""
    mask = _city_mask(meta, city)
    fetch = top_k * 10 if mask is not None else top_k

    scores, idxs = index.search(query_vec.reshape(1, -1), fetch)
    scores, idxs = scores[0], idxs[0]

    hits = []
    for i, s in zip(idxs, scores):
        if i == -1:
            continue
        if mask is not None and not mask[i]:
            continue
        hits.append((int(i), float(s)))
        if len(hits) >= top_k:
            break
    return hits


# ── Reciprocal Rank Fusion ─────────────────────────────────────────────

def rrf_fuse(*ranked_lists, top_k):
    """Cormack et al. — score = sum(1 / (RRF_K + rank_in_list)).
    Each input is [(passage_idx, original_score), ...] in descending order."""
    fused = {}
    for results in ranked_lists:
        for rank, (idx, _) in enumerate(results):
            fused[idx] = fused.get(idx, 0.0) + 1.0 / (RRF_K + rank + 1)
    ranked = sorted(fused.items(), key=lambda x: -x[1])[:top_k]
    return [(idx, score) for idx, score in ranked]


# ── Main retrieval entry point ─────────────────────────────────────────

class Retriever:
    """Loads indexes once, serves many queries. Pass `mode` per call.

    Heavy resources (BM25 pickle, FAISS index, dense encoder, cross-encoder,
    spaCy) load lazily — a BM25-only run never pays the cost of loading the
    cross-encoder.
    """

    def __init__(self, config=None):
        self.config = config or load_config()
        self.indexes_dir = self.config["paths"]["indexes"]

        self._bm25 = None
        self._bm25_meta = None
        self._dense_index = None
        self._dense_meta = None
        self._dense_model = None
        self._reranker = None
        self._nlp = None

    # lazy loaders ------------------------------------------------------
    def _ensure_bm25(self):
        if self._bm25 is None:
            self._bm25, self._bm25_meta = load_bm25(
                os.path.join(self.indexes_dir, "bm25.pkl")
            )

    def _ensure_dense(self):
        if self._dense_index is None:
            self._dense_index, self._dense_meta = load_dense(self.indexes_dir)
        if self._dense_model is None:
            self._dense_model = SentenceTransformer(DENSE_MODEL_NAME)

    def _ensure_reranker(self):
        if self._reranker is None:
            self._reranker = CrossEncoder(RERANKER_NAME)

    def _ensure_nlp(self):
        if self._nlp is None:
            import spacy
            self._nlp = spacy.load("en_core_web_lg")

    # rerank -----------------------------------------------------------
    def _rerank(self, question, hits, meta):
        self._ensure_reranker()
        pairs = [(question, meta[idx]["text"]) for idx, _ in hits]
        scores = self._reranker.predict(pairs)
        reranked = sorted(zip(hits, scores), key=lambda x: -x[1])
        return [(idx, float(score)) for (idx, _), score in reranked]

    # public API -------------------------------------------------------
    def retrieve(self, question, city=None, mode="hybrid", top_k=5,
                 retrieve_k=20, rerank=True):
        """Return top-`top_k` passages as JSON-serializable dicts.

        `retrieve_k` is the candidate pool size from each retriever before
        fusion + rerank; `top_k` is what we keep at the end.
        """
        if mode not in ("bm25", "dense", "hybrid"):
            raise ValueError(f"Unknown mode: {mode}")

        # Fetch raw hits per mode -----------------------------------------
        if mode == "bm25":
            self._ensure_bm25()
            self._ensure_nlp()
            tokens = tokenize_query_for_bm25(question, self._nlp)
            hits = bm25_search(tokens, self._bm25, self._bm25_meta, city, retrieve_k)
            meta = self._bm25_meta

        elif mode == "dense":
            self._ensure_dense()
            qvec = self._dense_model.encode(
                question, normalize_embeddings=True, convert_to_numpy=True
            ).astype("float32")
            hits = dense_search(qvec, self._dense_index, self._dense_meta, city, retrieve_k)
            meta = self._dense_meta

        else:  # hybrid
            self._ensure_bm25()
            self._ensure_dense()
            self._ensure_nlp()

            tokens = tokenize_query_for_bm25(question, self._nlp)
            bm25_hits = bm25_search(tokens, self._bm25, self._bm25_meta, city, retrieve_k)

            qvec = self._dense_model.encode(
                question, normalize_embeddings=True, convert_to_numpy=True
            ).astype("float32")
            dense_hits = dense_search(qvec, self._dense_index, self._dense_meta, city, retrieve_k)

            # BM25 and dense indexes were built from the same passage list in
            # the same order, so passage_idx is comparable across them.
            hits = rrf_fuse(bm25_hits, dense_hits, top_k=retrieve_k)
            meta = self._bm25_meta  # equivalent to dense_meta — same order

        # Optional cross-encoder rerank -----------------------------------
        if rerank and hits:
            hits = self._rerank(question, hits, meta)

        # Trim to top_k and hydrate to dicts ------------------------------
        return [
            {
                "rank":        rank + 1,
                "score":       score,
                "passage_id":  meta[idx]["passage_id"],
                "city":        meta[idx]["city"],
                "source":      meta[idx]["source"],
                "text":        meta[idx]["text"],
            }
            for rank, (idx, score) in enumerate(hits[:top_k])
        ]


if __name__ == "__main__":
    # Smoke test — runs all three modes against one question and prints
    # the top hit from each. Requires both BM25 and dense indexes built.
    import json

    r = Retriever()
    q = "When was Cairo founded?"
    city = "Cairo"

    for mode in ("bm25", "dense", "hybrid"):
        try:
            hits = r.retrieve(q, city=city, mode=mode, top_k=3, rerank=False)
            print(f"\n── {mode} ──")
            for h in hits:
                print(f"  [{h['rank']}] {h['score']:.3f}  {h['passage_id']}")
                print(f"      {h['text'][:140]}...")
        except (FileNotFoundError, RuntimeError) as e:
            print(f"\n── {mode} ── skipped (index missing — build dense_index.py first)")
