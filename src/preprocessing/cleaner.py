import json
import os
import re
import yaml
from pathlib import Path


def load_config(config_path="configs/config.yaml"):
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def clean_text(text):
    # remove citation brackets e.g. [1], [12], [citation needed]
    text = re.sub(r'\[.*?\]', '', text)
    # remove Wikipedia section headers e.g. == History ==
    text = re.sub(r'={2,}.*?={2,}', '', text)
    # remove HTML tags if any slipped through
    text = re.sub(r'<.*?>', '', text)
    # remove URLs
    text = re.sub(r'http\S+', '', text)
    # remove lines that are just punctuation or symbols
    text = re.sub(r'^\s*[^\w\s]+\s*$', '', text, flags=re.MULTILINE)
    # collapse multiple newlines into one
    text = re.sub(r'\n{3,}', '\n\n', text)
    # collapse multiple spaces
    text = re.sub(r' {2,}', ' ', text)
    # strip leading/trailing whitespace
    text = text.strip()
    return text


def clean_wikipedia(raw):
    return {
        "city": raw["city"],
        "source": "wikipedia",
        "url": raw.get("url", ""),
        "scraped_at": raw.get("scraped_at", ""),
        "text": clean_text(raw["text"])
    }


def clean_news(raw):
    articles = []
    for article in raw.get("articles", []):
        content = clean_text(article.get("content", ""))
        title = clean_text(article.get("title", ""))
        if content and title:
            articles.append({
                "title": title,
                "source": article.get("source", ""),
                "published_at": article.get("published_at", ""),
                "url": article.get("url", ""),
                "content": content
            })
    return {
        "city": raw["city"],
        "source": "newsapi",
        "scraped_at": raw.get("scraped_at", ""),
        "article_count": len(articles),
        "articles": articles
    }


def clean_tourism(raw):
    sections = []
    for section in raw.get("sections", []):
        cleaned = clean_text(section.get("text", ""))
        if cleaned:
            sections.append({
                "section": section.get("section", ""),
                "text": cleaned
            })
    return {
        "city": raw["city"],
        "source": "wikipedia_tourism",
        "section_count": len(sections),
        "sections": sections
    }


def process_city(city_name, raw_dir, out_dir):
    slug = city_name.lower().replace(" ", "_")
    os.makedirs(out_dir, exist_ok=True)
    results = []

    # Wikipedia
    wiki_path = os.path.join(raw_dir, f"{slug}.json")
    if os.path.exists(wiki_path):
        with open(wiki_path, "r", encoding="utf-8") as f:
            results.append(("wikipedia", clean_wikipedia(json.load(f))))

    # News
    news_path = os.path.join(raw_dir, f"{slug}_news.json")
    if os.path.exists(news_path):
        with open(news_path, "r", encoding="utf-8") as f:
            results.append(("news", clean_news(json.load(f))))

    # Tourism
    tourism_path = os.path.join(raw_dir, f"{slug}_tourism.json")
    if os.path.exists(tourism_path):
        with open(tourism_path, "r", encoding="utf-8") as f:
            results.append(("tourism", clean_tourism(json.load(f))))

    # save each cleaned file
    for source_type, data in results:
        out_path = os.path.join(out_dir, f"{slug}_{source_type}_clean.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    return len(results)


if __name__ == "__main__":
    config = load_config()
    cities = config["cities"]
    raw_dir = config["paths"]["raw_data"]
    out_dir = config["paths"]["processed_data"]

    print(f"Cleaning data for {len(cities)} cities...\n")
    success, failed = 0, []

    for city in cities:
        try:
            print(f"Cleaning: {city}")
            count = process_city(city, raw_dir, out_dir)
            print(f"  Saved {count} cleaned files")
            success += 1
        except Exception as e:
            print(f"  Failed: {city} — {e}")
            failed.append(city)

    print(f"\nDone. {success} cities cleaned, {len(failed)} failed.")
    if failed:
        print(f"Failed: {failed}")