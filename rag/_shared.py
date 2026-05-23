"""Shared, single-load RAG app instance.

Both studio_graph.py and chat_graph.py import `app` from here so the heavy
resources (embedder, Qdrant client, generator) load exactly once per process,
even though two graphs are registered with the langgraph dev server.
"""

from rag.graph import build_app

app = build_app()
