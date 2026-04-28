"""UrbanQA Streamlit demo.

Thin UI over `ask.UrbanQA`. The whole answer payload comes from one call to
`qa.answer(question)` and the same payload is what the future Unreal/UDP
server will consume — this UI is just renders + controls.

Run with:
    streamlit run app.py
"""

import streamlit as st
import json
import re

from ask import UrbanQA


# ── Page setup ─────────────────────────────────────────────────────────
st.set_page_config(
    page_title="UrbanQA",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Mirror the artifact's accent palette (dark + lime green)
st.markdown("""
<style>
  .stApp { background-color: #0d0f0e; }
  h1, h2, h3 { color: #e8ebe6; font-family: 'Georgia', serif; }
  .answer-box {
    background: linear-gradient(135deg, rgba(184,224,104,0.12), rgba(104,196,184,0.06));
    border: 1px solid rgba(184,224,104,0.3);
    border-radius: 12px; padding: 1.5rem; margin: 1rem 0;
  }
  .answer-text { font-size: 28px; color: #b8e068; font-weight: 600; }
  .meta-pill {
    display: inline-block; padding: 3px 10px; border-radius: 12px;
    font-size: 11px; letter-spacing: 0.05em; text-transform: uppercase;
    margin-right: 6px; font-family: 'Courier New', monospace;
  }
  .pill-city { background: rgba(184,224,104,0.15); color: #b8e068; border: 1px solid rgba(184,224,104,0.3); }
  .pill-type { background: rgba(104,196,184,0.15); color: #68c4b8; border: 1px solid rgba(104,196,184,0.3); }
  .pill-mode { background: rgba(232,168,74,0.15); color: #e8a84a; border: 1px solid rgba(232,168,74,0.3); }
  .answer-highlight {
    background: rgba(184,224,104,0.4); color: #fff;
    padding: 1px 4px; border-radius: 3px; font-weight: 600;
  }
  .source-box {
    background: rgba(255,255,255,0.03);
    border-left: 3px solid #b8e068;
    padding: 0.8rem 1rem; border-radius: 4px;
    font-size: 14px; line-height: 1.7; color: #c8ccc4;
  }
  .stButton button {
    background: #b8e068 !important; color: #0d0f0e !important;
    border: none !important; font-weight: 600 !important;
  }
</style>
""", unsafe_allow_html=True)


# ── Resource loading (cached so models load once across reruns) ────────
@st.cache_resource
def load_qa(mode):
    """Load the QA stack once. Streamlit reruns the script on every interaction
    but @st.cache_resource keeps the model objects in memory across reruns."""
    return UrbanQA(mode=mode)


# ── Sidebar: settings ─────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙ Settings")
    mode = st.radio(
        "Retrieval mode",
        ["hybrid", "bm25", "dense"],
        index=0,
        help="hybrid = BM25 + dense + cross-encoder rerank (best). bm25 / dense are ablations.",
    )
    top_k = st.slider("Passages to display", 1, 10, 5)
    rerank = st.checkbox("Cross-encoder rerank (slower, better)", value=True)
    read_k = st.slider("Passages read by QA model", 1, 5, 3,
                       help="More = higher recall, slower extraction.")

    st.markdown("---")
    st.markdown("### 📊 Eval (200 questions)")
    st.markdown("""
    | Mode | EM | F1 | R@5 | MRR |
    |---|---:|---:|---:|---:|
    | bm25 | 0.75 | 0.83 | 0.74 | 0.37 |
    | dense | 0.71 | 0.78 | 0.71 | 0.40 |
    | **hybrid** | **0.77** | **0.85** | **0.92** | **0.57** |
    """)

    st.markdown("---")
    st.caption("Models: mpnet-base-v2 (retrieval) · "
               "ms-marco-MiniLM-L-6-v2 (rerank) · "
               "roberta-base-squad2 (extract)")


# ── Main: header + question input ──────────────────────────────────────
st.markdown("# 🌍 UrbanQA")
st.markdown("*Ask anything about 20 cities. Powered by hybrid retrieval + extractive QA.*")

question = st.text_input(
    "Your question",
    placeholder="e.g. When was Cairo founded?  Who designed the Sydney Opera House?  How many people live in Tokyo?",
    label_visibility="collapsed",
)

example_qs = [
    "When was Cairo founded?",
    "Who designed the Sydney Opera House?",
    "What river runs through Paris?",
    "How many people live in Tokyo?",
    "What was Istanbul previously called?",
]
ex_cols = st.columns(len(example_qs))
for col, ex in zip(ex_cols, example_qs):
    if col.button(ex, key=f"ex_{ex}", use_container_width=True):
        question = ex

ask_clicked = st.button("Ask", type="primary", use_container_width=True)


# ── Helper: highlight answer span inside a passage ────────────────────
def highlight_answer(passage_text, answer_text):
    """Wrap every case-insensitive occurrence of answer_text in a span tag."""
    if not answer_text or not passage_text:
        return passage_text
    pattern = re.escape(answer_text)
    return re.sub(
        pattern,
        lambda m: f'<span class="answer-highlight">{m.group(0)}</span>',
        passage_text,
        flags=re.IGNORECASE,
    )


# ── Render answer ──────────────────────────────────────────────────────
if (ask_clicked or question) and question.strip():
    with st.spinner("Loading models (one-time, ~30s) and searching..."):
        qa = load_qa(mode)
        payload = qa.answer(
            question,
            mode=mode,
            top_k=top_k,
            rerank=rerank,
            read_k=read_k,
        )

    # Answer box
    city = payload["query"]["detected_city"] or "—"
    qtype = payload["query"]["question_type"]
    answer = payload["answer"] or "(no answer found)"
    conf = payload["confidence"]

    st.markdown(f"""
    <div class="answer-box">
      <div>
        <span class="meta-pill pill-city">city · {city}</span>
        <span class="meta-pill pill-type">type · {qtype}</span>
        <span class="meta-pill pill-mode">{mode}</span>
      </div>
      <div class="answer-text" style="margin-top: 0.8rem;">{answer}</div>
      <div style="color: #8a9186; margin-top: 0.5rem; font-size: 13px;">
        confidence {conf:.2f}
        {' · type matched ✓' if payload['type_match'] else ' · type mismatch'}
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Source passage
    src = payload["source_passage"]
    st.markdown("##### 📄 Source passage")
    st.markdown(f"""
    <div class="source-box">
      {highlight_answer(src['text'], answer)}
    </div>
    <div style="color: #8a9186; font-size: 12px; margin-top: 0.4rem;">
      <code>{src['passage_id']}</code> · {src['city']} · source: {src['source']}
    </div>
    """, unsafe_allow_html=True)

    # All retrieved passages
    with st.expander(f"🔍 All {len(payload['retrieved_passages'])} retrieved passages"):
        for p in payload["retrieved_passages"]:
            st.markdown(f"""
            **#{p['rank']}** · score {p['score']:.3f} ·
            `{p['passage_id']}` · {p['city']} · {p['source']}
            """)
            st.markdown(f"<div class='source-box' style='font-size:13px;'>{highlight_answer(p['text'], answer)}</div>",
                        unsafe_allow_html=True)
            st.markdown("---")

    # Raw JSON — what the future Unreal/UDP server will consume
    with st.expander("📦 Raw JSON payload (what feeds the Unreal/UDP server)"):
        st.code(json.dumps(payload, ensure_ascii=False, indent=2), language="json")
