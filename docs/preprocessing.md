# Preprocessing

## Overview

Three preprocessing stages transform raw scraped text into tokenized, indexed passages ready for NER and retrieval. All output lives in `data/processed/` and is gitignored.

## Stage 1 — Cleaning
**Script:** `src/preprocessing/cleaner.py`
**Input:** `data/raw/{city}.json`, `{city}_news.json`, `{city}_tourism.json`
**Output:** `data/processed/{city}_wikipedia_clean.json`, `{city}_news_clean.json`, `{city}_tourism_clean.json`

Cleans each raw file independently before any segmentation. Cleaning rules applied:

| Rule | Pattern removed |
|---|---|
| Citation brackets | `[1]`, `[12]`, `[citation needed]` |
| Section headers | `== History ==`, `=== Sub-section ===` |
| HTML tags | `<ref>`, `<br>`, any stray markup |
| URLs | `http://...`, `https://...` |
| Symbol-only lines | Lines containing only punctuation or special characters |
| Excess whitespace | Multiple consecutive spaces collapsed to one |
| Excess newlines | 3+ consecutive newlines collapsed to 2 |

Both Wikipedia and tourism files produce a single cleaned text block. News files produce a list of cleaned article objects, preserving title, source, and date metadata per article.

## Stage 2 — Segmentation
**Script:** `src/preprocessing/segmenter.py`
**Input:** `data/processed/{city}_*_clean.json`
**Output:** `data/processed/{city}_passages.json`

Splits cleaned text into overlapping passage windows for retrieval. Each passage is the unit that gets indexed and retrieved.

**Window parameters:**
- Window size: 3 sentences
- Stride: 1 sentence
- This means consecutive passages share 2 sentences of overlap

**Why overlapping windows?**
A factual answer may span a sentence boundary. Without overlap, a retriever could miss the relevant passage entirely if the answer starts at the end of one window and finishes at the start of the next. Overlap eliminates this gap.

**Passage metadata stored per passage:**
- `city` — source city
- `source` — `wikipedia`, `news`, or `tourism`
- `passage_id` — unique string ID
- `text` — full passage text
- `sentences` — individual sentence list

News passages additionally store `article_title` and `article_source`. Tourism passages store `section` name.

**Passage counts by city:**

| City | Passages |
|---|---|
| Cairo | 1082 |
| Paris | 1157 |
| Tokyo | 909 |
| London | 1228 |
| New York City | 1231 |
| Istanbul | 950 |
| Buenos Aires | 1000 |
| Lagos | 946 |
| Mumbai | 723 |
| Beijing | 1037 |
| Mexico City | 956 |
| São Paulo | 1199 |
| Berlin | 1063 |
| Sydney | 1379 |
| Dubai | 1081 |
| Rome | 1041 |
| Bangkok | 940 |
| Toronto | 1081 |
| Nairobi | 895 |
| Jakarta | 656 |
| **Total** | **20,554** |

## Stage 3 — Tokenization
**Script:** `src/preprocessing/tokenizer.py`
**Input:** `data/processed/{city}_passages.json`
**Output:** same file, passages enriched with token fields

Adds two token representations to every passage in-place:

**Raw tokens** — word-level split preserving original casing and punctuation. Used by the transformer QA model which requires original text form.

**Normalized tokens** — lemmatized, lowercased, stopwords removed, punctuation removed, single-character tokens removed. Used by BM25 which operates on keyword frequency and benefits from normalized vocabulary.

Both versions are stored alongside the original passage text so downstream modules can select whichever representation they need without re-tokenizing.

**Token fields added per passage:**
- `raw_tokens` — list of original tokens
- `normalized_tokens` — list of normalized lemmas
- `token_count` — length of raw token list
- `normalized_token_count` — length of normalized token list

## Tools Used

| Tool | Purpose |
|---|---|
| `spaCy en_core_web_lg` | Sentence segmentation, tokenization, lemmatization, stopword detection |
| `re` (stdlib) | Regex-based cleaning rules |
| `ftfy` | Unicode and encoding fixes (available, applied during cleaning) |
