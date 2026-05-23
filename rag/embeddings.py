"""Embeddings — BAAI BGE loaded through sentence-transformers.

Two asymmetric methods because BGE is trained that way:
  - embed_passages(texts)  -> raw passage embeddings (no prefix)
  - embed_query(text)      -> query embedding WITH the bge search instruction

Both are L2-normalized so Qdrant cosine == dot product. The same model and
settings are used at ingest time and query time — they must match.
"""

from __future__ import annotations
from sentence_transformers import SentenceTransformer

from rag.config import load_config


class Embedder:
    """Wraps a single sentence-transformers model. Load once, reuse."""

    def __init__(self, config: dict | None = None):
        cfg = (config or load_config())["embeddings"]
        self.model_name = cfg["model"]
        self.dim = cfg["dim"]
        self.query_instruction = cfg.get("query_instruction", "")
        self.normalize = cfg.get("normalize", True)

        print(f"Loading embedding model {self.model_name} ...")
        # Uses GPU automatically if torch sees CUDA.
        self.model = SentenceTransformer(self.model_name)

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        """Embed corpus passages (no instruction prefix)."""
        vecs = self.model.encode(
            texts,
            normalize_embeddings=self.normalize,
            convert_to_numpy=True,
            show_progress_bar=len(texts) > 64,
            batch_size=32,
        )
        return vecs.tolist()

    def embed_query(self, text: str) -> list[float]:
        """Embed a single query, prefixed with the BGE search instruction."""
        vec = self.model.encode(
            self.query_instruction + text,
            normalize_embeddings=self.normalize,
            convert_to_numpy=True,
        )
        return vec.tolist()
