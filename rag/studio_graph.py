"""Module-level compiled graph for LangGraph Studio / `langgraph dev`.

Studio needs a top-level `graph` variable (the compiled LangGraph), not one
hidden inside RAGApp. Importing this module builds the app once — which loads
the embedder, connects to Qdrant, and initializes the generator — then exposes
the compiled graph.

Referenced by langgraph.json:  "./rag/studio_graph.py:graph"
"""

from rag._shared import app

# Build once at import; Studio drives this compiled graph.
graph = app.graph
