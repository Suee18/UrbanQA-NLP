"""Germany RAG — a clean Retrieval-Augmented Generation system.

Target: a user asks a question about a German city/location and the system
answers it, grounded in retrieved Wikipedia context.

Architecture (LangGraph, 3 nodes):
    question -> [rewrite] -> [retrieve] -> [answer] -> {answer, sources}

Stack:
    - Ingestion : LangChain WikipediaLoader (German cities)
    - Chunking  : split by location, NO overlap
    - Embedding : BAAI/bge-large-en-v1.5 via sentence-transformers
    - Vector DB : Qdrant Cloud, single collection
    - LLM nodes : pluggable generator (local Qwen2.5 / Claude API)
"""
