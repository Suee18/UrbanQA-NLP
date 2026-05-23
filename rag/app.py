"""Streamlit demo for the Germany RAG system.

Run:
    streamlit run rag/app.py

Two views:
  - "Ask" tab: type a question, get the grounded answer + sources + passages.
  - "Graph trace" tab: watch the question flow through the LangGraph nodes
    (rewrite → retrieve → answer), inspecting each node's state — the same idea
    as LangGraph Studio, but works on Python 3.10 (Studio needs 3.11+).
"""

import os
import sys

# Streamlit runs this file with rag/ on sys.path but not the project root, so
# `import rag.*` fails. Add the project root (parent of this file's dir).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from rag.graph import build_app


st.set_page_config(page_title="Germany RAG", page_icon="🇩🇪", layout="wide")
st.title("🇩🇪 Germany RAG — ask about a German city")


@st.cache_resource(show_spinner="Loading models + connecting to Qdrant...")
def get_app():
    """Load the pipeline once and reuse across reruns."""
    return build_app()


app = get_app()

# Sidebar: the compiled graph structure.
with st.sidebar:
    st.subheader("LangGraph pipeline")
    st.graphviz_chart(
        """
        digraph {
            rankdir=TB;
            node [shape=box style="rounded,filled" fillcolor="#EEE8FF" fontname="Arial"];
            start [label="__start__" shape=oval fillcolor="#FFFFFF"];
            end   [label="__end__" shape=oval fillcolor="#BFB6FC"];
            start -> rewrite -> retrieve -> answer -> end;
        }
        """
    )
    st.caption("State: question → rewritten_query → retrieved_docs → answer")

question = st.text_input(
    "Your question",
    placeholder="e.g. How many people live in Munich?",
)

tab_answer, tab_trace = st.tabs(["💬 Ask", "🔎 Graph trace"])

# ── Tab 1: standard answer ────────────────────────────────────────────────
with tab_answer:
    if st.button("Ask", type="primary", key="ask_btn") and question.strip():
        with st.spinner("Rewriting → retrieving → answering..."):
            result = app.ask(question)

        st.subheader("Answer")
        st.write(result["answer"])

        locs = ", ".join(s["location"] for s in result["sources"] if s.get("location"))
        if locs:
            st.caption(f"Sources: {locs}")

        with st.expander("Rewritten query (node 1)"):
            st.code(result["rewritten_query"], language="text")

        with st.expander(f"Retrieved passages ({len(result['retrieved_docs'])})"):
            for i, d in enumerate(result["retrieved_docs"], start=1):
                st.markdown(f"**[{i}] {d['location']}** · score={d['score']:.3f}")
                st.write(d["text"])
                st.caption(d["source"])
                st.divider()

# ── Tab 2: live node-by-node trace (LangGraph Studio-style) ────────────────
with tab_trace:
    st.caption("Watch the question flow through each LangGraph node and inspect its output.")
    if st.button("Run with trace", type="primary", key="trace_btn") and question.strip():
        icons = {"rewrite": "1️⃣ rewrite", "retrieve": "2️⃣ retrieve", "answer": "3️⃣ answer"}
        for node, delta in app.ask_traced(question):
            with st.status(f"Node: {icons.get(node, node)}", state="complete", expanded=True):
                if node == "rewrite":
                    st.markdown("**rewritten_query**")
                    st.code(delta.get("rewritten_query", ""), language="text")
                elif node == "retrieve":
                    docs = delta.get("retrieved_docs", [])
                    st.markdown(f"**retrieved_docs** — {len(docs)} passages")
                    for i, d in enumerate(docs, start=1):
                        st.markdown(f"`[{i}]` **{d['location']}** · score={d['score']:.3f}")
                        st.caption(d["text"][:200] + ("…" if len(d["text"]) > 200 else ""))
                elif node == "answer":
                    st.markdown("**answer**")
                    st.write(delta.get("answer", ""))
                    srcs = delta.get("sources", [])
                    locs = ", ".join(s["location"] for s in srcs if s.get("location"))
                    if locs:
                        st.caption(f"sources: {locs}")
                else:
                    st.json(delta)
        st.success("Graph complete: __start__ → rewrite → retrieve → answer → __end__")
