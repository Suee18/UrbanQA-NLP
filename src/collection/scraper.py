import wikipedia
import json
import os
import yaml
from datetime import datetime, timezone


def load_config(config_path="configs/config.yaml"):
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def fetch_city(city_name, auto_suggest=False):
    page = wikipedia.page(city_name, auto_suggest=auto_suggest)
    return {
        "city": city_name,
        "title": page.title,
        "url": page.url,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "sections": page.sections,
        "text": page.content
    }


def save_city(data, out_dir="data/raw"):
    os.makedirs(out_dir, exist_ok=True)
    filename = data["city"].lower().replace(" ", "_") + ".json"
    path = os.path.join(out_dir, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  Saved: {path}")


if __name__ == "__main__":
    config = load_config()
    cities = config["cities"]
    out_dir = config["paths"]["raw_data"]
    auto_suggest = config["scraper"]["auto_suggest"]

    print(f"Scraping {len(cities)} cities...\n")
    success, failed = 0, []

    for city in cities:
        try:
            print(f"Fetching: {city}")
            data = fetch_city(city, auto_suggest=auto_suggest)
            save_city(data, out_dir)
            success += 1
        except Exception as e:
            print(f"  Failed: {city} — {e}")
            failed.append(city)

    print(f"\nDone. {success} saved, {len(failed)} failed.")
    if failed:
        print(f"Failed cities: {failed}")