import json
import os
import yaml
import spacy


def load_config(config_path="configs/config.yaml"):
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_spacy():
    print("Loading spaCy model...")
    return spacy.load("en_core_web_lg")


def sentencize(text, nlp):
    doc = nlp(text)
    return [sent.text.strip() for sent in doc.sents if sent.text.strip()]


def make_passages(sentences, window=3, stride=1):
    passages = []
    for i in range(0, len(sentences) - window + 1, stride):
        passage = " ".join(sentences[i:i + window])
        passages.append({
            "passage_id": i,
            "sentences": sentences[i:i + window],
            "text": passage
        })
    # catch any remaining sentences at the end
    if len(sentences) % window != 0:
        remainder = " ".join(sentences[-(len(sentences) % window):])
        if remainder not in [p["text"] for p in passages]:
            passages.append({
                "passage_id": len(passages),
                "sentences": sentences[-(len(sentences) % window):],
                "text": remainder
            })
    return passages


def segment_wikipedia(data, nlp, city):
    sentences = sentencize(data["text"], nlp)
    passages = make_passages(sentences)
    return [{
        "city": city,
        "source": "wikipedia",
        "passage_id": f"{city}_wiki_{p['passage_id']}",
        "text": p["text"],
        "sentences": p["sentences"]
    } for p in passages]


def segment_news(data, nlp, city):
    all_passages = []
    for i, article in enumerate(data.get("articles", [])):
        sentences = sentencize(article["content"], nlp)
        passages = make_passages(sentences)
        for p in passages:
            all_passages.append({
                "city": city,
                "source": "news",
                "article_title": article.get("title", ""),
                "article_source": article.get("source", ""),
                "passage_id": f"{city}_news_{i}_{p['passage_id']}",
                "text": p["text"],
                "sentences": p["sentences"]
            })
    return all_passages


def segment_tourism(data, nlp, city):
    all_passages = []
    for i, section in enumerate(data.get("sections", [])):
        sentences = sentencize(section["text"], nlp)
        if not sentences:
            continue
        passages = make_passages(sentences)
        for p in passages:
            all_passages.append({
                "city": city,
                "source": "tourism",
                "section": section.get("section", ""),
                "passage_id": f"{city}_tourism_{i}_{p['passage_id']}",
                "text": p["text"],
                "sentences": p["sentences"]
            })
    return all_passages


def process_city(city_name, processed_dir, out_dir, nlp):
    slug = city_name.lower().replace(" ", "_")
    os.makedirs(out_dir, exist_ok=True)
    all_passages = []

    # Wikipedia
    wiki_path = os.path.join(processed_dir, f"{slug}_wikipedia_clean.json")
    if os.path.exists(wiki_path):
        with open(wiki_path, "r", encoding="utf-8") as f:
            all_passages += segment_wikipedia(json.load(f), nlp, city_name)

    # News
    news_path = os.path.join(processed_dir, f"{slug}_news_clean.json")
    if os.path.exists(news_path):
        with open(news_path, "r", encoding="utf-8") as f:
            all_passages += segment_news(json.load(f), nlp, city_name)

    # Tourism
    tourism_path = os.path.join(processed_dir, f"{slug}_tourism_clean.json")
    if os.path.exists(tourism_path):
        with open(tourism_path, "r", encoding="utf-8") as f:
            all_passages += segment_tourism(json.load(f), nlp, city_name)

    # save all passages for this city in one file
    out_path = os.path.join(out_dir, f"{slug}_passages.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "city": city_name,
            "passage_count": len(all_passages),
            "passages": all_passages
        }, f, ensure_ascii=False, indent=2)

    return len(all_passages)


if __name__ == "__main__":
    config = load_config()
    cities = config["cities"]
    processed_dir = config["paths"]["processed_data"]
    out_dir = config["paths"]["processed_data"]

    nlp = load_spacy()
    print(f"\nSegmenting {len(cities)} cities...\n")

    success, failed = 0, []
    total_passages = 0

    for city in cities:
        try:
            print(f"Segmenting: {city}")
            count = process_city(city, processed_dir, out_dir, nlp)
            print(f"  {count} passages")
            total_passages += count
            success += 1
        except Exception as e:
            print(f"  Failed: {city} — {e}")
            failed.append(city)

    print(f"\nDone. {success} cities, {total_passages} total passages, {len(failed)} failed.")
    if failed:
        print(f"Failed: {failed}")