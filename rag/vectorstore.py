"""Qdrant vector store — ONE collection for the whole corpus.

Reads QDRANT_URL / QDRANT_API_KEY from .env. Works against Qdrant Cloud or a
local docker instance with the same code. Payload carries the location so we
can show (and optionally filter by) the city a chunk came from.
"""

from __future__ import annotations
import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue,
)

from rag.config import load_config, qdrant_url, qdrant_api_key


class VectorStore:
    """Thin wrapper around a single Qdrant collection."""

    def __init__(self, config: dict | None = None):
        cfg = config or load_config()
        qc = cfg["qdrant"]
        self.collection = qc["collection"]
        self.dim = cfg["embeddings"]["dim"]
        self.distance = getattr(Distance, qc.get("distance", "Cosine").upper())

        self.client = QdrantClient(
            url=qdrant_url(),
            api_key=qdrant_api_key(),
            timeout=60,
        )

    # ── collection lifecycle ───────────────────────────────────────────
    def recreate_collection(self) -> None:
        """Drop + create the single collection. Called by build_index before
        a fresh ingest so re-runs are idempotent."""
        self.client.recreate_collection(
            collection_name=self.collection,
            vectors_config=VectorParams(size=self.dim, distance=self.distance),
        )

    def count(self) -> int:
        return self.client.count(self.collection, exact=True).count

    # ── write ───────────────────────────────────────────────────────────
    def upsert(self, vectors: list[list[float]], payloads: list[dict],
               batch_size: int = 128) -> None:
        """Insert chunks. Each payload should contain: text, location, source."""
        assert len(vectors) == len(payloads)
        points = [
            PointStruct(id=str(uuid.uuid4()), vector=v, payload=p)
            for v, p in zip(vectors, payloads)
        ]
        for i in range(0, len(points), batch_size):
            self.client.upsert(
                collection_name=self.collection,
                points=points[i:i + batch_size],
            )

    # ── read ─────────────────────────────────────────────────────────────
    def search(self, query_vector: list[float], top_k: int = 10,
               location: str | None = None) -> list[dict]:
        """Return top-k hits as dicts: {score, text, location, source}.

        Optional `location` filter narrows search to one city's chunks (single
        collection, filtered by payload — no extra collections needed).
        """
        flt = None
        if location:
            flt = Filter(must=[
                FieldCondition(key="location", match=MatchValue(value=location))
            ])

        # qdrant-client >= 1.10 uses query_points() (search() is deprecated/removed).
        response = self.client.query_points(
            collection_name=self.collection,
            query=query_vector,
            limit=top_k,
            query_filter=flt,
            with_payload=True,
        )
        hits = response.points
        return [
            {
                "score":    float(h.score),
                "text":     h.payload.get("text", ""),
                "location": h.payload.get("location", ""),
                "source":   h.payload.get("source", ""),
            }
            for h in hits
        ]
