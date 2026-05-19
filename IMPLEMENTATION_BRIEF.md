# UrbanQA — Implementation Brief for Technical-Document Sync

**Purpose.** This document is the ground-truth snapshot of the UrbanQA implementation as it exists in the repo. Use it as the authoritative source when editing the LaTeX technical document. If a claim in the .tex contradicts a fact here, the .tex is wrong — update it.

**Scope.** Architecture, models, hyperparameters, data flow, evaluation. Not: prose, motivation, related work.

**Repo:** `E:/CS/NLP/urbanqa/` — public mirror at https://github.com/Suee18/UrbanQA-NLP

---

## 1. System overview

UrbanQA is a retrieval-augmented extractive QA system over a multi-city corpus. Single public entry point: `UrbanQA.answer(question)` in [`ask.py`](ask.py), returning one JSON-serializable dict. Both the Streamlit demo (`app.py`) and the planned Unreal Engine / WebSocket server are thin wrappers over this call.

**Pipeline (offline → online):**

```
Offline:  scrape → clean → segment → tokenize → NER+POS → index (BM25 + FAISS)
Online:   question → query-process → retrieve (hybrid + RRF + rerank) → extract → answer
```

**Corpus:** 25,847 passages across 21 cities. Sources per city: Wikipedia, NewsAPI articles, Wikipedia tourism sections, and (Munich only) a hand-authored Digital Twin technical document.

---

## 2. Single entry point — `ask.py`

```python
class UrbanQA:
    def __init__(self, config=None, mode="hybrid", load_extractor=True): ...
    def answer(self, question, mode=None, top_k=5, retrieve_k=20,
               rerank=True, read_k=3, list_top_k=8) -> dict: ...
```

**Return shape (all keys always present):**

| Key | Type | Notes |
|---|---|---|
| `question` | str | original query |
| `mode` | str | `"bm25"` / `"dense"` / `"hybrid"` |
| `list_mode` | bool | True when question matches a LIST pattern |
| `query` | dict | `{question, question_type, expected_entity_types, detected_city, city_confidence, is_list_query}` |
| `answer` | str | extracted span; empty string in list mode |
| `confidence` | float | ∈ [0, 1] |
| `type_match` | bool | answer span carried the expected entity type |
| `source_passage` | dict | `{passage_id, city, source, text}` |
| `retrieved_passages` | list[dict] | `{rank, score, passage_id, city, source, text}` |
| `aggregated_entities` | list[dict] | `{text, label, count}` — populated only in list mode |
| `all_candidates` | list[dict] | per-passage candidate spans — populated only in extractive mode |

The payload is JSON-serializable and is the contract for any downstream UI (Streamlit, Unreal/WebSocket).

---

## 3. Pipeline stages — file and function references

| Stage | File | Key symbol |
|---|---|---|
| Wikipedia scraper | `src/collection/scraper.py` | `fetch_city()`, `save_city()` |
| News scraper | `src/collection/news_scraper.py` | `fetch_city_news()` (NewsAPI) |
| Tourism extractor | `src/collection/tourism_extractor.py` | `extract_tourism_sections()` (parses Wiki section headers) |
| Digital twin loader | `src/collection/digital_twin_loader.py` | `load_one()` (reads `data/digital_twin/{slug}.md`) |
| Cleaner | `src/preprocessing/cleaner.py` | `clean_wikipedia()`, `clean_news()`, `clean_tourism()` |
| Segmenter | `src/preprocessing/segmenter.py` | `segment_wikipedia/news/tourism/digital_twin()` — all use `make_passages(window=3, stride=1)` |
| Tokenizer | `src/preprocessing/tokenizer.py` | `tokenize_passage()` — emits `raw_tokens` and `normalized_tokens` |
| NER + POS | `src/analysis/ner_pos.py` | `analyze_passage()` (spaCy `en_core_web_lg`) |
| BM25 index | `src/indexing/bm25_index.py` | `build_bm25()` (rank-bm25 `BM25Okapi` over normalized tokens) |
| FAISS index | `src/indexing/dense_index.py` | `encode_passages()`, `build_faiss()` (`IndexFlatIP`, dim 768) |
| Query processing | `src/retrieval/query_processor.py` | `process_query()` — question type, city detection, list-query check |
| Retrieval | `src/retrieval/retriever.py` | `Retriever.retrieve()` — BM25 / dense / hybrid + RRF + cross-encoder rerank |
| Answer extraction | `src/qa/extractor.py` | `AnswerExtractor.extract()` — RoBERTa SQuAD 2.0 |
| Evaluation | `src/evaluation/metrics.py` | `evaluate_system()` — EM, F1, Recall@k, MRR |

---

## 4. Models

| Component | HuggingFace / library identifier |
|---|---|
| Dense embedder | `sentence-transformers/all-mpnet-base-v2` |
| Cross-encoder reranker | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| Extractive QA reader | `deepset/roberta-base-squad2` |
| NER + POS | spaCy `en_core_web_lg` |

All models run locally on CPU; no paid APIs. All loaded lazily (BM25-only paths never instantiate transformers).

---

## 5. Hyperparameters (exact values — do not paraphrase)

| Parameter | Value | Where |
|---|---|---|
| RRF constant `k` | **60** | `src/retrieval/retriever.py` |
| Passage window (sentences) | **3** | `src/preprocessing/segmenter.py` |
| Passage stride (sentences) | **1** | `src/preprocessing/segmenter.py` |
| Dense embedding dim | **768** | `src/indexing/dense_index.py` |
| FAISS index type | `IndexFlatIP` (exact, L2-normalized) | `src/indexing/dense_index.py` |
| Encoding batch size | 64 | `src/indexing/dense_index.py` |
| Default `top_k` (final) | 5 | `ask.py` |
| Default `retrieve_k` (pre-rerank pool) | 20 | `ask.py` |
| Default `read_k` (passages → reader) | 3 | `src/qa/extractor.py` |
| `list_top_k` (passages in list mode) | 8 | `ask.py` |
| `MAX_ANSWER_LEN` | 30 tokens | `src/qa/extractor.py` |
| `TOPN_START_END` (candidate (s,e) per passage) | 20 | `src/qa/extractor.py` |
| `TYPE_MISMATCH_PENALTY` (multiplicative) | 0.5 | `src/qa/extractor.py` |
| City detection confidence (NER pass) | 0.7 | `src/retrieval/query_processor.py` |

---

## 6. Corpus

- **Total passages:** 25,847
- **Cities (21):** Cairo, Paris, Tokyo, London, New York City, Istanbul, Buenos Aires, Lagos, Mumbai, Beijing, Mexico City, São Paulo, Berlin, Sydney, Dubai, Rome, Bangkok, Toronto, Nairobi, Jakarta, Munich
- **Munich is intentionally over-represented** (~5,293 passages vs ~1k average) because it is the focal city for the Smart City Digital Twin integration.
- **Gold QA set:** 200 question-answer pairs at `data/gold_qa/gold.jsonl`.

**Source types per passage:** `wikipedia`, `news`, `tourism`, `digital_twin`. Stored as `source` in passage metadata and carried through to retrieved-passage attribution in the answer payload.

---

## 7. Retrieval — hybrid + RRF + rerank

**Modes:** `bm25` (sparse only), `dense` (FAISS only), `hybrid` (default).

**Hybrid order of operations:**

1. BM25 returns top-`retrieve_k`, FAISS returns top-`retrieve_k`.
2. **Reciprocal Rank Fusion** combines the two ranked lists with `k = 60` (Cormack et al.). RRF runs *before* reranking.
3. The fused top-`retrieve_k` go to the cross-encoder, which produces final scores.
4. Final top-`top_k` passages are returned.

**City filtering.** FAISS `IndexFlatIP` does not support per-query filtering. The retriever over-fetches (`top_k × 10`) and masks non-matching cities post-hoc.

---

## 8. Query processing

`src/retrieval/query_processor.py` produces:

- `question_type` — what / who / where / when / how / how-many / why / yes-no — via regex.
- `expected_entity_types` — mapping from question type to spaCy entity labels (e.g. *where* → `{GPE, LOC, FAC}`). Used downstream to validate extracted spans.
- `detected_city` + `city_confidence` — **two-pass** detection:
  1. Longest-alias-first substring match against a curated alias map (catches `nyc`, `bombay`, `cdmx` at zero NLP cost).
  2. Fallback to spaCy NER (`GPE`/`LOC`/`FAC`) with alias resolution, confidence 0.7.
- `is_list_query` — boolean, drives list mode (see §10).

---

## 9. Answer extraction

[`src/qa/extractor.py`](src/qa/extractor.py) runs RoBERTa SQuAD 2.0 over the top-`read_k` passages.

**SQuAD 2.0 semantics retained.** The model can emit an empty answer; the `[CLS]-[CLS]` no-answer score gates against forced extraction from passages that don't actually contain the answer. This is intentional — most retrieved passages are not the gold passage, and forcing a span hurts F1 more than it helps EM.

**Entity-type validation.** Each candidate span is run through spaCy at extraction time; if its entity type is not in `expected_entity_types`, its score is multiplied by `TYPE_MISMATCH_PENALTY = 0.5`. This is a *penalty*, not a *filter* — a strong wrong-type answer can still win over a weak right-type one. The .tex should not describe this as a hard type filter.

**Candidate selection per passage.** Top 20 `(start, end)` index pairs by joint logit, filtered to `end - start + 1 ≤ MAX_ANSWER_LEN = 30`.

---

## 10. List mode

Triggered by `is_list_query()` matching any of 8 regex patterns (top-N, "list/name/enumerate", "what are the (main|popular|top) …", "where can I go", "things to visit", etc.). See `src/retrieval/query_processor.py:139-156` for the exact patterns.

When triggered:
- Extractive QA is **skipped** (`answer=""`, `all_candidates=[]`).
- Retrieval returns top-8 passages (vs 5).
- `aggregated_entities` is populated: deduplicated top-15 NER entities across retrieved passages, restricted to `{FAC, LOC, GPE, ORG, EVENT, WORK_OF_ART, PRODUCT}`, ranked by frequency.

Rationale: extractive QA can only produce a single span; "top 10 attractions" is structurally an aggregation, not a span. This is an honest-fallback design — the system tells the truth about what it can answer.

---

## 11. Digital Twin source — `digital_twin`

Hand-authored markdown (`data/digital_twin/munich.md`) for content not on the open web (Unreal Engine version, agent architecture, UDP protocols, Blueprint structure). Plumbing:

1. `digital_twin_loader.load_one()` reads the file, `strip_markdown()` removes `#` headings, `**/__` bold/italic, inline backticks, and collapses blank lines.
2. Output schema matches the cleaned-wiki/news/tourism shape: `{city, source: "digital_twin", url: "", scraped_at, text}`.
3. From segmentation onward, identical to other sources — same window=3 / stride=1, same tokenizer, same NER, same indexing.
4. `source="digital_twin"` is carried through to retrieved-passage attribution.

**No special retrieval logic** for digital-twin passages. Treated identically to other sources. The .tex should not describe this as a separate retrieval path.

---

## 12. Indexing — what is stored where

Metadata-only indexes:

- **BM25 index** (`data/indexes/bm25.pkl`) — pickled `BM25Okapi` + per-passage metadata (`passage_id`, `city`, `source`, `text`).
- **FAISS index** (`data/indexes/faiss.index` + `faiss_meta.json`) — same lightweight metadata; embeddings L2-normalized for cosine via inner product.

Heavy fields (`entities`, `pos_tags`, `raw_tokens`, `normalized_tokens`) live in the on-disk passages file and are re-loaded only when needed (list-mode aggregation, debugging). Re-running NER at query time would also be acceptable (~150ms) but is currently avoided.

---

## 13. Evaluation

`src/evaluation/metrics.py` runs the 200-question gold set through each mode and reports:

| Metric | Definition |
|---|---|
| **EM** | 1 if predicted answer matches *any* gold variant after SQuAD normalization (lowercase, strip articles, strip punctuation), else 0 |
| **Token F1** | Best token-overlap F1 across gold variants |
| **Recall@k** | 1 if the gold passage ID appears in top-k retrieved (k ∈ {1, 3, 5, 10}) |
| **MRR** | Mean reciprocal rank of the gold passage; 0 if not retrieved |

Per-mode results live at `data/gold_qa/results/{bm25,dense,hybrid}.json`, with overall scores plus breakdowns `by_question_type`, `by_city`, and full `per_item` traces.

**Headline numbers (hybrid mode, current run):**

| Metric | Value |
|---|---|
| EM | 0.765 |
| Token F1 | 0.8506 |
| Recall@5 | 0.915 |
| MRR | 0.568 |

These are the numbers to cite. If the .tex shows different values (e.g. older `EM 0.77 / F1 0.85` rounded approximations), update them to the precise values above.

---

## 14. Common drift points — likely fixes in the .tex

These are the places a technical document about a system like this typically gets it wrong. Check each:

1. **RRF order.** Fusion happens *before* cross-encoder reranking, not after.
2. **Type validation is a penalty, not a filter.** Spans of the "wrong" entity type are down-weighted, not discarded.
3. **List mode skips extraction.** The system does not attempt to extract spans for list queries — it returns aggregated entities. Document this as a deliberate choice, not a limitation.
4. **Digital-twin source is treated identically to other sources after cleaning.** No special retrieval, no special ranking.
5. **SQuAD 2.0 no-answer is preserved.** The reader is *allowed* to abstain on a per-passage basis; this is intentional given low Recall@1.
6. **All models run on CPU locally.** No GPU, no paid APIs. If a deployment / cost section claims GPU, fix it.
7. **City detection is two-pass** (alias substring → spaCy NER), not NER-only.
8. **Passages overlap** (window 3, stride 1). If the .tex says "non-overlapping passages", that is wrong.
9. **FAISS uses `IndexFlatIP`** (exact, not ANN). If the .tex says HNSW / IVF / approximate search, that is wrong.
10. **Default retrieval mode is `hybrid`.** All headline numbers are hybrid-mode.

---

## 15. What this document is *not*

- Not a complete API reference — only the public entry point is documented.
- Not a justification of design choices — see the .tex for that.
- Not a roadmap — Unreal Engine / WebSocket integration is planned, not built.

If the .tex needs facts not covered here, ask for a follow-up rather than guessing.
