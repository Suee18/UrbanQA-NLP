"""Ingestion — build the knowledge base into Qdrant.

Flow (run once via `python -m rag.build_index`):
    for each German location in config:
        WikipediaLoader -> article text
        split into chunks (chunk_overlap = 0)         <- instructor constraint
        tag each chunk with its location               <- "chunk by location"
    embed all chunks (BAAI/bge via sentence-transformers)
    upsert into the single Qdrant collection

No overlap is used anywhere. If overlap is ever needed, ask the user first.
"""

from __future__ import annotations

import time

from langchain_community.document_loaders import WikipediaLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from rag.config import load_config
from rag.embeddings import Embedder
from rag.vectorstore import VectorStore


def load_location_text(location: str, lang: str, max_docs: int,
                        retries: int = 4, backoff: float = 3.0) -> list[dict]:
    """Fetch Wikipedia content for one location via LangChain.

    Returns a list of {text, source} — one per article. We query by the
    location name so the top article is the city's own page.

    Wikipedia's API occasionally returns a non-JSON body (transient), which
    raises JSONDecodeError. We retry with linear backoff so one blip doesn't
    abort the whole build.
    """
    docs = None
    for attempt in range(1, retries + 1):
        try:
            loader = WikipediaLoader(
                query=location,
                lang=lang,
                load_max_docs=max_docs,
                doc_content_chars_max=1_000_000,  # don't truncate; we chunk ourselves
            )
            docs = loader.load()
            break
        except Exception as e:  # transient network / JSON decode
            if attempt == retries:
                raise
            wait = backoff * attempt
            print(f"    ! fetch failed ({type(e).__name__}); retry {attempt}/{retries - 1} in {wait:.0f}s")
            time.sleep(wait)
    out = []
    for d in docs:
        out.append({
            "text":   d.page_content,
            "source": d.metadata.get("source")
                      or d.metadata.get("title", location),
        })
    return out


def chunk_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """Split into chunks. chunk_overlap is 0 per the instructor constraint."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,           # 0
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return [c.strip() for c in splitter.split_text(text) if c.strip()]


def build_chunks(config: dict) -> list[dict]:
    """Produce all chunks across all locations, each tagged with location.

    Returns list of {text, location, source}.
    """
    ing = config["ingest"]
    locations = config["locations"]
    all_chunks: list[dict] = []
    skipped: list[str] = []

    for loc in locations:
        print(f"  • {loc}: fetching Wikipedia ...")
        try:
            articles = load_location_text(loc, ing["lang"], ing["max_docs_per_location"])
        except Exception as e:
            # Don't let one stubborn city (Wikipedia rate-limit / API blip) abort
            # the whole build. Skip it; it can be backfilled by re-running later.
            print(f"    ! SKIPPED {loc} after retries ({type(e).__name__}). Re-run later to add it.")
            skipped.append(loc)
            continue

        loc_chunk_count = 0
        for art in articles:
            for piece in chunk_text(art["text"], ing["chunk_size"], ing["chunk_overlap"]):
                all_chunks.append({
                    "text":     piece,
                    "location": loc,            # chunk tagged by city/location
                    "source":   art["source"],
                })
                loc_chunk_count += 1
        print(f"    -> {loc_chunk_count} chunks")

        # Be polite to the Wikipedia API to avoid throttling on rapid requests.
        time.sleep(1.5)

    if skipped:
        print(f"\nNote: skipped {len(skipped)} location(s): {', '.join(skipped)}")
    return all_chunks


def build_index(config: dict | None = None) -> int:
    """End-to-end: fetch -> chunk -> embed -> upsert. Returns chunk count."""
    config = config or load_config()

    print("Building chunks from Wikipedia (German locations)...")
    chunks = build_chunks(config)
    if not chunks:
        raise RuntimeError("No chunks produced — check the locations list.")
    print(f"Total chunks: {len(chunks)}")

    embedder = Embedder(config)
    print("Embedding chunks...")
    vectors = embedder.embed_passages([c["text"] for c in chunks])

    store = VectorStore(config)
    print(f"Recreating Qdrant collection '{store.collection}' ...")
    store.recreate_collection()
    print("Upserting...")
    store.upsert(vectors, chunks)

    total = store.count()
    print(f"Done. Collection now holds {total} points.")
    return total
