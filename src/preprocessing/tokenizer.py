import json
import os
import yaml
import spacy
from pathlib import Path


def load_config(config_path="configs/config.yaml"):
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_spacy():
    print("Loading spaCy model...")
    return spacy.load("en_core_web_lg")


def tokenize_passage(text, nlp):
    doc = nlp(text)

    # raw tokens — keep casing and punctuation, just split
    raw_tokens = [token.text for token in doc]

    # normalized tokens — lowercase, remove stopwords and punctuation
    normalized_tokens = [
        token.lemma_.lower()
        for token in doc
        if not token.is_stop
        and not token.is_punct
        and not token.is_space
        and len(token.text.strip()) > 1
    ]

    return raw_tokens, normalized_tokens


def process_city(city_name, processed_dir, nlp):
    slug = city_name.lower().replace(" ", "_")
    passages_path = os.path.join(processed_dir, f"{slug}_passages.json")

    if not os.path.exists(passages_path):
        print(f"  Missing passages file: {passages_path}")
        return 0

    with open(passages_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    passages = data["passages"]
    tokenized = []

    for passage in passages:
        raw_tokens, norm_tokens = tokenize_passage(passage["text"], nlp)
        tokenized.append({
            **passage,
            "raw_tokens": raw_tokens,
            "normalized_tokens": norm_tokens,
            "token_count": len(raw_tokens),
            "normalized_token_count": len(norm_tokens)
        })

    # overwrite the passages file with tokenized version
    out_path = passages_path
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "city": city_name,
            "passage_count": len(tokenized),
            "passages": tokenized
        }, f, ensure_ascii=False, indent=2)

    return len(tokenized)


if __name__ == "__main__":
    config = load_config()
    cities = config["cities"]
    processed_dir = config["paths"]["processed_data"]

    nlp = load_spacy()
    print(f"\nTokenizing {len(cities)} cities...\n")

    success, failed = 0, []
    total = 0

    for city in cities:
        try:
            print(f"Tokenizing: {city}")
            count = process_city(city, processed_dir, nlp)
            print(f"  {count} passages tokenized")
            total += count
            success += 1
        except Exception as e:
            print(f"  Failed: {city} — {e}")
            failed.append(city)

    print(f"\nDone. {success} cities, {total} passages tokenized, {len(failed)} failed.")
    if failed:
        print(f"Failed: {failed}")