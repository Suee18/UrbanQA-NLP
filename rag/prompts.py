"""The two system prompts of the pipeline (instructor's 2-prompt requirement).

  1. SYSTEM_PROMPT_REWRITE  — drives the query-rewrite LLM node. It reshapes the
     user's raw question into one clean, standalone, retrieval-optimized query.

  2. SYSTEM_PROMPT_ANSWER   — drives the final answer agent. It writes the
     grounded answer using ONLY the retrieved context (anti-hallucination).

Helper builders below assemble the user-side messages for each node.
"""

# ── Prompt 1: query rewrite agent ────────────────────────────────────────
SYSTEM_PROMPT_REWRITE = """\
You are a query-rewriting assistant for a search system about German cities and \
locations. Rewrite the user's question into ONE clean, standalone search query \
that maximizes retrieval of relevant facts.

Rules:
- Make the query self-contained: resolve pronouns ("it", "there", "this city") \
to the explicit German location when it is known from the conversation.
- Keep and normalize the German location name (e.g. "munich" -> "Munich").
- Remove greetings, chit-chat, and filler; keep only the information need.
- Do NOT answer the question. Do NOT add facts that are not in the question.
- Output ONLY the rewritten query as a single line, with no quotes or labels.

Examples:
- User: "hey, how big is its population?" (about Munich) -> Population of Munich, Germany
- User: "tell me a bit about the history there" (about Berlin) -> History of Berlin, Germany
- User: "what river runs through cologne?" -> River running through Cologne, Germany
"""


# ── Prompt 2: final answer agent ──────────────────────────────────────────
SYSTEM_PROMPT_ANSWER = """\
You are a factual assistant that answers questions about German cities and \
locations using ONLY the provided context passages.

Rules:
- Use only facts that appear in the context. Do NOT use outside knowledge.
- If the context does not contain the answer, reply exactly:
  "I don't have enough information to answer that."
- Be concise, accurate, and directly answer the question.
- End your answer with a short source note naming the location/article(s) used,
  e.g. "(Source: Munich — Wikipedia)".
"""


def build_rewrite_messages(question: str, history: str | None = None) -> list[dict]:
    """Messages for the rewrite node. `history` is optional prior turns text."""
    user = question if not history else f"Conversation so far:\n{history}\n\nLatest question: {question}"
    return [
        {"role": "system", "content": SYSTEM_PROMPT_REWRITE},
        {"role": "user", "content": user},
    ]


def format_context(passages: list[dict]) -> str:
    """Render retrieved passages into a numbered, citable context block."""
    blocks = []
    for i, p in enumerate(passages, start=1):
        loc = p.get("location", "?")
        src = p.get("source", "")
        blocks.append(f"[{i}] (Location: {loc}) {p['text']}\n    Source: {src}")
    return "\n\n".join(blocks)


def build_answer_messages(question: str, passages: list[dict]) -> list[dict]:
    """Messages for the final answer node: context block + the user question."""
    context = format_context(passages) or "(no context retrieved)"
    user = (
        f"Context passages:\n{context}\n\n"
        f"Question: {question}\n\n"
        f"Answer using only the context above."
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT_ANSWER},
        {"role": "user", "content": user},
    ]
