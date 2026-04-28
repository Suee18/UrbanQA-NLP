"""Deep Wikipedia scrape for Munich.

Standard `scraper.py` pulls only the main "Munich" article. This script
additionally pulls a curated list of Munich-related sub-articles
(landmarks, institutions, neighborhoods, sports, museums, history) and
concatenates them into a single Munich corpus tagged `city="Munich"`.

Sensitive WW2 / terrorism / appeasement topics are deliberately excluded
("taboos") — the QA system isn't built to handle those questions
responsibly.

Output: data/raw/munich.json — same format as the standard scraper, so the
rest of the pipeline (cleaner → segmenter → tokenizer → NER → indexing)
needs no changes.
"""

import json
import os
import time
from datetime import datetime, timezone

import wikipedia
import yaml


# Curated Munich sub-articles. Excluded by request: Beer Hall Putsch,
# Dachau concentration camp, Munich Agreement, Munich Massacre.
MUNICH_SUBARTICLES = [
    # core / geography
    "History of Munich",
    "Geography of Munich",
    "Bavaria",                        # state Munich is the capital of
    "Bavarian language",
    "Munich Metropolitan Region",

    # famous landmarks & places
    "Marienplatz",
    "Frauenkirche, Munich",
    "Hofbräuhaus am Platzl",
    "Englischer Garten",
    "Nymphenburg Palace",
    "Theresienwiese",
    "Olympiapark, Munich",
    "Asam Church",
    "St. Peter's Church, Munich",

    # museums & culture
    "BMW Welt",
    "BMW Museum",
    "Deutsches Museum",
    "Alte Pinakothek",
    "Neue Pinakothek",
    "Pinakothek der Moderne",
    "Lenbachhaus",
    "Bavarian National Museum",

    # events & festivals
    "Oktoberfest",

    # sports & teams
    "FC Bayern Munich",
    "TSV 1860 Munich",
    "Allianz Arena",
    "1972 Summer Olympics",

    # transportation & infrastructure
    "Munich U-Bahn",
    "Munich S-Bahn",
    "Munich Airport",
    "Munich Hauptbahnhof",

    # neighborhoods / districts
    "Schwabing",
    "Altstadt-Lehel",
    "Maxvorstadt",

    # institutions
    "Ludwig Maximilian University of Munich",
    "Technical University of Munich",
    "BMW",                            # Munich-headquartered, deeply tied to the city
    "Siemens",                        # Munich-headquartered

    # cuisine & local culture
    "Bavarian cuisine",
    "Weisswurst",
    "Bavarian beer",
]


def load_config(config_path="configs/config.yaml"):
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _to_record(page):
    return {
        "title":    page.title,
        "url":      page.url,
        "sections": page.sections,
        "text":     page.content,
    }


def fetch_one(title):
    """Robust fetch with three escalating strategies. Returns (record, error_str)
    where one is always None.

    1. Exact title, auto_suggest=False — strictest
    2. auto_suggest=True — Wikipedia's spell/redirect suggestion
    3. wikipedia.search(title)[0] — fall back to top search hit

    Disambiguation errors are caught and we fall through to strategy 3."""

    # Strategy 1: exact
    try:
        return _to_record(wikipedia.page(title, auto_suggest=False)), None
    except wikipedia.exceptions.DisambiguationError as e:
        # Strategy 1.5: try first disambiguation option
        try:
            return _to_record(wikipedia.page(e.options[0], auto_suggest=False)), None
        except Exception:
            pass
    except wikipedia.exceptions.PageError:
        pass
    except Exception as e:
        # Connection / parsing errors etc. — fall through to next strategy
        pass

    # Strategy 2: auto_suggest=True (lets Wikipedia spell-correct / redirect)
    try:
        return _to_record(wikipedia.page(title, auto_suggest=True)), None
    except Exception:
        pass

    # Strategy 3: search and take the top hit
    try:
        results = wikipedia.search(title, results=3)
        for candidate in results:
            try:
                return _to_record(wikipedia.page(candidate, auto_suggest=False)), None
            except Exception:
                continue
    except Exception as e:
        return None, f"search-failed: {type(e).__name__}: {e}"

    return None, "all-strategies-failed"


def main():
    config = load_config()
    out_dir = config["paths"]["raw_data"]
    os.makedirs(out_dir, exist_ok=True)

    titles = ["Munich"] + MUNICH_SUBARTICLES
    print(f"Deep-scraping {len(titles)} Munich articles...\n")

    parts = []
    sections = []
    fetched_titles = []
    failed = []

    for i, title in enumerate(titles, start=1):
        print(f"  [{i}/{len(titles)}] {title}", end="")
        result, err = fetch_one(title)
        if result is None:
            print(f"  ✗  {err}")
            failed.append(title)
            continue

        # Concatenate with a section separator so the downstream cleaner /
        # segmenter sees clear article boundaries.
        parts.append(f"\n\n== {result['title']} ==\n\n{result['text']}")
        sections.extend(result["sections"])
        fetched_titles.append(result["title"])
        print(f"  ✓  → {result['title']}")

        # Politeness delay. Wikipedia silently rate-limits after ~15 rapid
        # requests; 1 sec keeps us comfortably under that. Add an extra
        # 5-sec breath every 10 articles as belt-and-suspenders.
        time.sleep(1.0)
        if i % 10 == 0:
            time.sleep(5.0)

    # Write one combined JSON in the same shape as the standard scraper.
    combined = {
        "city":          "Munich",
        "title":         "Munich (deep scrape)",
        "url":           "https://en.wikipedia.org/wiki/Munich",
        "scraped_at":    datetime.now(timezone.utc).isoformat(),
        "sections":      sections,
        "text":          "".join(parts),
        "fetched_titles": fetched_titles,
        "failed":        failed,
    }

    path = os.path.join(out_dir, "munich.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(combined, f, ensure_ascii=False, indent=2)

    total_chars = len(combined["text"])
    print(f"\nDone. Saved {path}")
    print(f"  {len(fetched_titles)} articles fetched ({len(failed)} failed)")
    print(f"  {total_chars:,} characters total ({total_chars // 5_000} estimated passages)")
    if failed:
        print(f"  Failed: {failed}")


if __name__ == "__main__":
    main()
