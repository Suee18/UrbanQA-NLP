# UrbanQA

A multi-city question answering system. Ask anything about 20 cities — Cairo, Paris, Tokyo, London, NYC, Istanbul, Buenos Aires, Lagos, Mumbai, Beijing, Mexico City, São Paulo, Berlin, Sydney, Dubai, Rome, Bangkok, Toronto, Nairobi, Jakarta — and get an extracted answer with the source passage.

Built end-to-end through the standard NLP pipeline: data collection → preprocessing → NER + POS → indexing (sparse + dense) → query processing → hybrid retrieval → extractive QA → evaluation.

## Results

Hybrid retrieval (BM25 + FAISS dense + RRF + cross-encoder rerank) on a 200-question auto-generated gold set:

| Metric        | Target | Achieved |
|---------------|-------:|---------:|
| Exact Match   |   0.45 | **0.77** |
| Token F1      |   0.60 | **0.85** |
| Recall@5      |   0.75 | **0.92** |
| MRR           |   0.60 | 0.57     |

## Architecture

```
question
   ↓
query processor      ── classify type (what/who/when/...), detect city via alias map + spaCy NER
   ↓
hybrid retriever     ── BM25 (rank-bm25)  +  dense (mpnet-base-v2 → FAISS)
                       fused via Reciprocal Rank Fusion (k=60)
                       reranked with cross-encoder/ms-marco-MiniLM-L-6-v2
   ↓
answer extractor     ── deepset/roberta-base-squad2  ·  multi-passage span search  ·  type validation
   ↓
JSON payload         ── { answer, confidence, source_passage, retrieved_passages, ... }
```

The same JSON payload feeds the CLI, the Streamlit demo, and (later) a UDP/socket.io server for an Unreal Engine dashboard.

## Quickstart

### 1. Setup
```bash
# Mac/Linux
bash setup/setup.sh

# Windows
setup\setup.bat
```

### 2. Activate the venv (every terminal session)
```bash
# Mac/Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. NewsAPI key
Register at [newsapi.org](https://newsapi.org), then create `.env` in the project root:
```env
NEWSAPI_KEY=your_key_here
```
`.env` is gitignored — each teammate needs their own key.

### 4. Build the corpus + indexes
```bash
# First time — runs collection + preprocessing + NER + indexing
python main.py

# Skip collection if raw data already exists
python main.py --skip-collection

# Run a single stage by name
python main.py --stage tokenizer
```

## Using the system

### CLI
```bash
python ask.py "When was Cairo founded?"
python ask.py "Who designed the Sydney Opera House?" --mode dense
python ask.py "How many people live in Tokyo?" --json    # machine-readable payload
```

### Streamlit demo
```bash
streamlit run app.py
# open http://localhost:8501
```
Browser UI with mode toggle, top-k slider, answer-span highlighting in the source passage, and the raw JSON payload visible in an expander.

### Evaluation
```bash
# Auto-generate a gold QA candidate set from the corpus
python src/evaluation/gold_qa_builder.py --per-city 10

# Promote candidates to the eval set
cp data/gold_qa/gold_candidates.jsonl data/gold_qa/gold.jsonl

# Run all three modes (BM25 / dense / hybrid)
python src/evaluation/metrics.py

# Generate per-mode error analysis (markdown reports)
python src/evaluation/error_analysis.py
```

## Project structure

```
src/
  collection/         scrapers — Wikipedia, NewsAPI, tourism
  preprocessing/      cleaner · segmenter (3-sent, stride 1) · tokenizer
  analysis/           NER + POS tagging
  indexing/           bm25_index.py · dense_index.py
  retrieval/          query_processor.py (city detect + type classify)
                      retriever.py (bm25 / dense / hybrid + RRF + rerank)
  qa/                 extractor.py (RoBERTa-squad2 + type validation)
  evaluation/         metrics.py · error_analysis.py · gold_qa_builder.py

ask.py                CLI entry point — wraps UrbanQA.answer()
app.py                Streamlit demo — wraps the same call
main.py               Pipeline runner for the offline build stages

configs/config.yaml   List of cities + paths
data/raw/             Scraped sources (gitignored)
data/processed/       One {city}_passages.json per city (gitignored)
data/indexes/         BM25 pickle + FAISS index (gitignored)
data/gold_qa/         Eval set + per-mode results + error analysis
```

## Models

| Stage                | Model                                      | Size   |
|----------------------|--------------------------------------------|-------:|
| Linguistic analysis  | spaCy `en_core_web_lg`                     | 580 MB |
| Dense embeddings     | `sentence-transformers/all-mpnet-base-v2`  | 440 MB |
| Cross-encoder rerank | `cross-encoder/ms-marco-MiniLM-L-6-v2`     |  85 MB |
| Answer extraction    | `deepset/roberta-base-squad2`              | 500 MB |
| Gold QA generation   | `valhalla/t5-base-qg-hl`                   | 250 MB |

All models cache in `~/.cache/huggingface/` after first download.

## Adding a dependency
```bash
pip install new-library
pip freeze > requirements.txt
git add requirements.txt
git commit -m "add new-library to requirements"
```
