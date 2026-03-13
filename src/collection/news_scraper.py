import os
import json
from datetime import datetime
from dotenv import load_dotenv
from newsapi import NewsApiClient
import yaml

load_dotenv()

def load_config(config_path="configs/config.yaml"):
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def fetch_city_news(client, city_name, max_articles=10):
    response = client.get_everything(
        q=city_name,
        language="en",
        sort_by="relevancy",
        page_size=max_articles
    )
    articles = []
    for a in response.get("articles", []):
        if a.get("content") and a.get("title"):
            articles.append({
                "title": a["title"],
                "source": a["source"]["name"],
                "published_at": a["publishedAt"],
                "url": a["url"],
                "content": a["content"]
            })
    return articles

def save_news(city_name, articles, out_dir="data/raw"):
    filename = city_name.lower().replace(" ", "_") + "_news.json"
    path = os.path.join(out_dir, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({
            "city": city_name,
            "scraped_at": datetime.utcnow().isoformat(),
            "article_count": len(articles),
            "articles": articles
        }, f, ensure_ascii=False, indent=2)
    print(f"  Saved: {path} ({len(articles)} articles)")

if __name__ == "__main__":
    config = load_config()
    cities = config["cities"]
    out_dir = config["paths"]["raw_data"]

    api_key = os.getenv("NEWSAPI_KEY")
    if not api_key:
        raise ValueError("NEWSAPI_KEY not found in .env file")

    client = NewsApiClient(api_key=api_key)

    print(f"Fetching news for {len(cities)} cities...\n")
    success, failed = 0, []

    for city in cities:
        try:
            print(f"Fetching news: {city}")
            articles = fetch_city_news(client, city)
            save_news(city, articles, out_dir)
            success += 1
        except Exception as e:
            print(f"  Failed: {city} — {e}")
            failed.append(city)

    print(f"\nDone. {success} saved, {len(failed)} failed.")
    if failed:
        print(f"Failed cities: {failed}")