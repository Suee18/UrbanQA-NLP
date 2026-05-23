"""LangGraph pipeline: rewrite -> retrieve -> answer.

    START -> [rewrite] -> [retrieve] -> [answer] -> END

Shared state flows through the three nodes. Heavy resources (embedder, vector
store, generator) are loaded once and closed over by the node functions, so the
compiled graph can serve many questions without reloading models.

Public entry point: build_app() returns an object with .ask(question) -> dict.
"""

from __future__ import annotations
from typing import TypedDict

from langgraph.graph import StateGraph, START, END

from rag.config import load_config
from rag.embeddings import Embedder
from rag.vectorstore import VectorStore
from rag.generator import make_generator
from rag.prompts import build_rewrite_messages, build_answer_messages


class RAGState(TypedDict, total=False):
    """State passed between nodes."""
    question: str           # original user question (input)
    rewritten_query: str    # node 1 output
    retrieved_docs: list    # node 2 output (list of {score, text, location, source})
    answer: str             # node 3 output
    sources: list           # node 3 output (deduped location/source pairs)


class RAGApp:
    """Holds the compiled graph + the loaded resources."""

    def __init__(self, config: dict | None = None):
        self.config = config or load_config()
        self.top_k = self.config["retrieval"]["top_k"]

        # Load heavy resources once.
        self.embedder = Embedder(self.config)
        self.store = VectorStore(self.config)
        self.generator = make_generator(self.config)

        self.graph = self._build_graph()

    # ── nodes ────────────────────────────────────────────────────────────
    def _node_rewrite(self, state: RAGState) -> RAGState:
        """NODE 1 — LLM rewrites the question into a clean search query."""
        msgs = build_rewrite_messages(state["question"])
        rewritten = self.generator.chat(msgs).strip().strip('"')
        # Fallback: if the model returns nothing usable, keep the original.
        return {"rewritten_query": rewritten or state["question"]}

    def _node_retrieve(self, state: RAGState) -> RAGState:
        """NODE 2 — embed the rewritten query, search Qdrant (top-k)."""
        qvec = self.embedder.embed_query(state["rewritten_query"])
        docs = self.store.search(qvec, top_k=self.top_k)
        return {"retrieved_docs": docs}

    def _node_answer(self, state: RAGState) -> RAGState:
        """NODE 3 — final agent answers grounded in the retrieved context."""
        docs = state.get("retrieved_docs", [])
        msgs = build_answer_messages(state["question"], docs)
        answer = self.generator.chat(msgs)

        # Dedupe sources for display.
        seen, sources = set(), []
        for d in docs:
            key = (d.get("location"), d.get("source"))
            if key not in seen:
                seen.add(key)
                sources.append({"location": d.get("location"), "source": d.get("source")})
        return {"answer": answer, "sources": sources}

    # ── graph wiring ──────────────────────────────────────────────────────
    def _build_graph(self):
        g = StateGraph(RAGState)
        g.add_node("rewrite", self._node_rewrite)
        g.add_node("retrieve", self._node_retrieve)
        g.add_node("answer", self._node_answer)

        g.add_edge(START, "rewrite")
        g.add_edge("rewrite", "retrieve")
        g.add_edge("retrieve", "answer")
        g.add_edge("answer", END)
        return g.compile()

    # ── public API ─────────────────────────────────────────────────────────
    def ask(self, question: str) -> dict:
        """Run the full graph for one question. JSON-serializable result."""
        final = self.graph.invoke({"question": question})
        return {
            "question":        question,
            "rewritten_query": final.get("rewritten_query", ""),
            "answer":          final.get("answer", ""),
            "sources":         final.get("sources", []),
            "retrieved_docs":  final.get("retrieved_docs", []),
        }

    def ask_traced(self, question: str):
        """Run the graph and yield each node's output as it fires.

        Yields (node_name, state_delta) tuples in execution order — the same
        "watch it flow through rewrite → retrieve → answer and inspect the
        state at each step" experience LangGraph Studio gives, usable from the
        Streamlit UI without the Studio dev server.
        """
        for update in self.graph.stream({"question": question}, stream_mode="updates"):
            for node, delta in update.items():
                yield node, delta


def build_app(config: dict | None = None) -> RAGApp:
    return RAGApp(config)
