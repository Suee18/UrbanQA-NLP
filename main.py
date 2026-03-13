import argparse
import subprocess
import sys


PIPELINE = [
    {
        "name": "Wikipedia scraper",
        "script": "src/collection/scraper.py",
        "once": True,
        "desc": "Scrapes Wikipedia articles for all 20 cities"
    },
    {
        "name": "News scraper",
        "script": "src/collection/news_scraper.py",
        "once": True,
        "desc": "Fetches NewsAPI articles for all 20 cities — requires NEWSAPI_KEY in .env"
    },
    {
        "name": "Tourism extractor",
        "script": "src/collection/tourism_extractor.py",
        "once": True,
        "desc": "Extracts tourism sections from Wikipedia JSONs"
    },
    {
        "name": "Cleaner",
        "script": "src/preprocessing/cleaner.py",
        "once": False,
        "desc": "Strips markup, citations, and noise from all raw files"
    },
    {
        "name": "Segmenter",
        "script": "src/preprocessing/segmenter.py",
        "once": False,
        "desc": "Splits cleaned text into overlapping 3-sentence passages"
    },
]


def run_stage(stage):
    print(f"\n{'='*60}")
    print(f"  {stage['name']}")
    print(f"  {stage['desc']}")
    print(f"{'='*60}\n")
    result = subprocess.run(
        [sys.executable, stage["script"]],
        check=False
    )
    if result.returncode != 0:
        print(f"\nERROR: {stage['name']} failed. Stopping pipeline.")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="UrbanQA pipeline runner")
    parser.add_argument(
        "--skip-collection",
        action="store_true",
        help="Skip data collection stages (Wikipedia, News, Tourism) — use if data already exists"
    )
    parser.add_argument(
        "--stage",
        type=str,
        help="Run a single stage by name e.g. --stage cleaner"
    )
    args = parser.parse_args()

    if args.stage:
        # run a single named stage
        match = next((s for s in PIPELINE if args.stage.lower() in s["name"].lower()), None)
        if not match:
            print(f"Stage '{args.stage}' not found.")
            print(f"Available: {[s['name'] for s in PIPELINE]}")
            sys.exit(1)
        run_stage(match)
        return

    for stage in PIPELINE:
        if args.skip_collection and stage["once"]:
            print(f"Skipping (--skip-collection): {stage['name']}")
            continue
        run_stage(stage)

    print("\nPipeline complete.")


if __name__ == "__main__":
    main()