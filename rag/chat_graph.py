"""Chat-compatible RAG graph for LangChain's Agent Chat UI.

Same pipeline as rag/graph.py (rewrite -> retrieve -> answer) but the state is
message-based so the open-source Agent Chat UI can render it as a conversation:

  - input  : {"messages": [HumanMessage(question)]}
  - output : appends an AIMessage(answer) to messages

Internal scratch fields (rewritten_query, retrieved_docs, sources) ride along
in the state so they're still inspectable. Heavy resources are shared via
rag._shared so nothing loads twice.

Referenced by langgraph.json:  "./rag/chat_graph.py:graph"
"""

from __future__ import annotations
from typing import Annotated, TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import AIMessage

from rag._shared import app
from rag.prompts import build_rewrite_messages, build_answer_messages


class ChatState(TypedDict, total=False):
    messages: Annotated[list, add_messages]   # conversation (UI renders this)
    rewritten_query: str
    retrieved_docs: list
    sources: list


def _last_human_text(messages) -> str:
    """Pull the most recent human message's text out of the conversation."""
    for m in reversed(messages or []):
        # langgraph normalizes inbound messages to BaseMessage objects.
        if getattr(m, "type", None) == "human":
            return m.content
    return messages[-1].content if messages else ""


def node_rewrite(state: ChatState) -> dict:
    question = _last_human_text(state["messages"])
    rewritten = app.generator.chat(build_rewrite_messages(question)).strip().strip('"')
    return {"rewritten_query": rewritten or question}


def node_retrieve(state: ChatState) -> dict:
    qvec = app.embedder.embed_query(state["rewritten_query"])
    docs = app.store.search(qvec, top_k=app.top_k)
    return {"retrieved_docs": docs}


def node_answer(state: ChatState) -> dict:
    question = _last_human_text(state["messages"])
    docs = state.get("retrieved_docs", [])
    answer = app.generator.chat(build_answer_messages(question, docs))

    seen, sources = set(), []
    for d in docs:
        key = (d.get("location"), d.get("source"))
        if key not in seen:
            seen.add(key)
            sources.append({"location": d.get("location"), "source": d.get("source")})

    # Appending an AIMessage is what makes the answer show up in the chat UI.
    return {"messages": [AIMessage(content=answer)], "sources": sources}


def _build():
    g = StateGraph(ChatState)
    g.add_node("rewrite", node_rewrite)
    g.add_node("retrieve", node_retrieve)
    g.add_node("answer", node_answer)
    g.add_edge(START, "rewrite")
    g.add_edge("rewrite", "retrieve")
    g.add_edge("retrieve", "answer")
    g.add_edge("answer", END)
    return g.compile()


graph = _build()
