"""One-shot orchestrator that runs the full pipeline for Munich only.

Saves having to edit configs/config.yaml temporarily or re-process the other
19 cities. Call this after Munich is added to configs and after you've run
src/collection/munich_deep_scraper.py to get the heavy Wikipedia data.

Steps it runs:
  1. (assumed already done) deep Wikipedia scrape       → data/raw/munich.json
  2. NewsAPI scrape                                      → data/raw/munich_news.json
  3. Tourism extractor (uses scraped Wiki sections)      → data/raw/munich_tourism.json
  4. Digital-twin loader (custom domain doc)             → data/processed/munich_digital_twin_clean.json
  5. Cleaner (Munich only)                               → data/processed/munich_*_clean.json
  6. Segmenter (Munich only)                             → data/processed/munich_passages.json
  7. Tokenizer (Munich only)                             → updates munich_passages.json
  8. NER + POS (Munich only)                             → updates munich_passages.json
  9. Rebuild BM25 index (all cities)                     → data/indexes/bm25.pkl
 10. Rebuild FAISS dense index (all cities)              → data/indexes/dense.faiss

Steps 9 + 10 must rebuild the WHOLE corpus because BM25 and FAISS are
single matrices spanning all passages — adding Munich means rewriting them.
"""

import os
import subprocess
import sys

CITY = "Munich"


def banner(label):
    print("\n" + "=" * 60)
    print(f"  {label}")
    print("=" * 60)


def run_step(label, fn):
    banner(label)
    fn()


# ── Step 2: News scraper for Munich only ─────────────────────────────
def step_news():
    from src.collection.news_scraper import fetch_city_news, save_news, load_config
    from dotenv import load_dotenv
    from newsapi import NewsApiClient

    load_dotenv()
    api_key = os.environ.get("NEWSAPI_KEY")
    if not api_key:
        print("  No NEWSAPI_KEY in env — skipping news scrape (corpus still works without it).")
        return

    config = load_config()
    out_dir = config["paths"]["raw_data"]
    client = NewsApiClient(api_key=api_key)

    print(f"  Fetching news for {CITY}...")
    articles = fetch_city_news(client, CITY, max_articles=10)
    print(f"  Got {len(articles)} articles")
    save_news(CITY, articles, out_dir)


# ── Step 3: Tourism extractor for Munich only ────────────────────────
def step_tourism():
    import json
    from src.collection.tourism_extractor import (
        load_config, extract_tourism_sections,
    )
    config = load_config()
    raw_dir = config["paths"]["raw_data"]

    wiki_path = os.path.join(raw_dir, "munich.json")
    if not os.path.exists(wiki_path):
        print(f"  Skip — {wiki_path} doesn't exist (run munich_deep_scraper.py first)")
        return

    with open(wiki_path, "r", encoding="utf-8") as f:
        wiki = json.load(f)

    sections = extract_tourism_sections(wiki)
    print(f"  Extracted {len(sections)} tourism-tagged sections")

    out_path = os.path.join(raw_dir, "munich_tourism.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "city":       CITY,
            "sections":   sections,
        }, f, ensure_ascii=False, indent=2)
    print(f"  Saved {out_path}")


# ── Step 4: Digital-twin loader ──────────────────────────────────────
def step_digital_twin():
    from src.collection.digital_twin_loader import load_one, load_config
    config = load_config()
    out_dir = config["paths"]["processed_data"]
    result = load_one(CITY, "data/digital_twin", out_dir)
    if result is None:
        print(f"  No data/digital_twin/munich.md — skipping digital twin source")
    else:
        out_path, n_chars = result
        print(f"  {n_chars:,} chars → {out_path}")


# ── Step 5: Cleaner for Munich only ──────────────────────────────────
def step_clean():
    from src.preprocessing.cleaner import process_city, load_config
    config = load_config()
    raw_dir = config["paths"]["raw_data"]
    out_dir = config["paths"]["processed_data"]
    n = process_city(CITY, raw_dir, out_dir)
    print(f"  Saved {n} cleaned files for {CITY}")


# ── Step 6: Segmenter for Munich only ────────────────────────────────
def step_segment():
    from src.preprocessing.segmenter import process_city, load_config, load_spacy
    config = load_config()
    processed_dir = config["paths"]["processed_data"]
    nlp = load_spacy()
    n = process_city(CITY, processed_dir, processed_dir, nlp)
    print(f"  {n} passages segmented for {CITY}")


# ── Step 7: Tokenizer for Munich only ────────────────────────────────
def step_tokenize():
    from src.preprocessing.tokenizer import process_city, load_config, load_spacy
    config = load_config()
    processed_dir = config["paths"]["processed_data"]
    nlp = load_spacy()
    n = process_city(CITY, processed_dir, nlp)
    print(f"  {n} passages tokenized for {CITY}")


# ── Step 8: NER + POS for Munich only ────────────────────────────────
def step_ner():
    from src.analysis.ner_pos import process_city, load_config, load_spacy
    config = load_config()
    processed_dir = config["paths"]["processed_data"]
    nlp = load_spacy()
    n = process_city(CITY, processed_dir, nlp)
    print(f"  {n} passages NER-tagged for {CITY}")


# ── Step 9 + 10: rebuild BOTH indexes (they cover all cities) ────────
def step_indexes():
    print("  Rebuilding BM25 (~15 sec)...")
    subprocess.run([sys.executable, "src/indexing/bm25_index.py"], check=True)
    print("\n  Rebuilding FAISS dense (~10 min on CPU)...")
    subprocess.run([sys.executable, "src/indexing/dense_index.py"], check=True)


def main():
    print(f"\nRunning Munich-only pipeline\n")

    run_step("Step 1 / Scrape news (NewsAPI)", step_news)
    run_step("Step 2 / Extract tourism sections", step_tourism)
    run_step("Step 3 / Load digital-twin doc", step_digital_twin)
    run_step("Step 4 / Clean", step_clean)
    run_step("Step 5 / Segment", step_segment)
    run_step("Step 6 / Tokenize", step_tokenize)
    run_step("Step 7 / NER + POS", step_ner)
    run_step("Step 8 / Rebuild indexes", step_indexes)

    print("\n" + "=" * 60)
    print("  Munich pipeline complete. Indexes updated.")
    print("=" * 60)


if __name__ == "__main__":
    main()
