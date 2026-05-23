# Germany RAG

A Retrieval-Augmented Generation system for **question answering about German cities**, built as a **LangGraph** pipeline. You ask a question; the system rewrites it, retrieves relevant passages from a Wikipedia-derived knowledge base in Qdrant, and an LLM writes a grounded answer with a source citation.

## Architecture — LangGraph (3 nodes)

```
question ─▶ [1 rewrite] ─▶ [2 retrieve] ─▶ [3 answer] ─▶ {answer, sources}
```

| Step | Tech / Model |
|------|--------------|
| Data | LangChain `WikipediaLoader` (German cities) |
| Chunking | split **by location**, **no overlap** |
| Embedding | `BAAI/bge-large-en-v1.5` via `sentence-transformers` (1024-dim) |
| Vector DB | **Qdrant Cloud** — single collection `germany_rag` |
| Query rewrite | LLM node + system prompt #1 |
| Retrieval | Qdrant similarity search, **top-k = 10** |
| Answer | LLM final agent + system prompt #2 |
| Orchestration | **LangGraph** |
| LLM backend | **Groq** Llama-3.3-70B (default) · local Qwen2.5 · Claude API |

## Project layout

```
rag/
  config.yaml        # cities, models, top-k, generator backend
  config.py          # config + .env loader
  ingest.py          # WikipediaLoader → chunk (no overlap) → embed → upsert
  build_index.py     # one-shot KB builder
  embeddings.py      # BAAI/BGE via sentence-transformers
  vectorstore.py     # Qdrant single-collection wrapper
  generator.py       # pluggable LLM: groq / local / api
  prompts.py         # the two system prompts (rewrite + answer)
  graph.py           # LangGraph: rewrite → retrieve → answer  (field-based state)
  chat_graph.py      # message-based variant for Agent Chat UI
  studio_graph.py    # module-level export for LangGraph Studio
  _shared.py         # single-load shared app instance
  cli.py             # CLI:  python -m rag.cli "question"
  app.py             # Streamlit UI (answer + graph trace)
langgraph.json       # registers both graphs for `langgraph dev`
agent-chat-ui/       # local chat front-end (LangChain open-source, Next.js)
```

## Quick start — one command

Once set up (see below), power up **all** UIs at once:

```bat
run.bat
```

This launches three services, each in its own window:

| Service | URL |
|---------|-----|
| Agent Chat UI | http://localhost:3000 |
| Streamlit app | http://localhost:8501 |
| LangGraph API/server | http://127.0.0.1:2024 |
| LangGraph Studio | `https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024` |
| LangSmith traces | project `germany-rag` (automatic) |

Close the three windows to stop everything. (The LangGraph server runs from the
`venv-studio` Python 3.11+ env; the CLI/Streamlit use the main env.)

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env     # then fill in QDRANT_URL, QDRANT_API_KEY, GROQ_API_KEY
```

## Build the knowledge base (run once)

```bash
python -m rag.build_index
```

## Ask questions

```bash
# CLI
python -m rag.cli "How many people live in Munich?"

# Streamlit web UI (answer + node-by-node graph trace)
streamlit run rag/app.py
```

## LangGraph dev server + UIs (optional)

The dev server needs **Python 3.11+** (use a separate env, e.g. `venv-studio`):

```bash
pip install "langgraph-cli[inmem]"
langgraph dev            # local API at http://127.0.0.1:2024
```

- **Drive it from the terminal:**
  `curl -X POST http://127.0.0.1:2024/runs/wait -H "Content-Type: application/json" -d '{"assistant_id":"germany_rag","input":{"question":"..."}}'`
- **Agent Chat UI (fully local):** `cd agent-chat-ui && pnpm install && pnpm dev` → http://localhost:3000
  (configured to point at the local server + the `germany_rag_chat` graph)
- **LangSmith tracing (optional):** set `LANGSMITH_TRACING=true` + `LANGSMITH_API_KEY` in `.env`; runs appear under project `germany-rag`.

## Configuration

All tunables live in `rag/config.yaml`: the `locations` list, chunk size,
embedding model, `top_k`, and the generator backend (`groq` / `local` / `api`).

> **Constraints baked in:** chunk overlap is fixed at `0`; the corpus lives in
> a single Qdrant collection; top-k stays ≤ 15; chunks are tagged by location.
