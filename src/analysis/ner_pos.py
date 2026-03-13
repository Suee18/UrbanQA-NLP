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


def analyze_passage(text, nlp):
    doc = nlp(text)

    # extract named entities
    entities = [
        {
            "text":  ent.text,
            "label": ent.label_,
            "start": ent.start_char,
            "end":   ent.end_char
        }
        for ent in doc.ents
    ]

    # extract POS tags
    pos_tags = [
        {
            "text":    token.text,
            "pos":     token.pos_,
            "tag":     token.tag_,
            "dep":     token.dep_,
            "lemma":   token.lemma_
        }
        for token in doc
        if not token.is_space
    ]

    return entities, pos_tags


def process_city(city_name, processed_dir, nlp):
    slug = city_name.lower().replace(" ", "_")
    path = os.path.join(processed_dir, f"{slug}_passages.json")

    if not os.path.exists(path):
        print(f"  Missing: {path}")
        return 0

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    passages = data["passages"]
    entity_types = {}

    for passage in passages:
        entities, pos_tags = analyze_passage(passage["text"], nlp)
        passage["entities"] = entities
        passage["pos_tags"] = pos_tags

        # count entity types for summary
        for ent in entities:
            entity_types[ent["label"]] = entity_types.get(ent["label"], 0) + 1

    # save enriched passages back to same file
    with open(path, "w", encoding="utf-8") as f:
        json.dump({
            "city":          city_name,
            "passage_count": len(passages),
            "entity_summary": entity_types,
            "passages":      passages
        }, f, ensure_ascii=False, indent=2)

    total_entities = sum(entity_types.values())
    return len(passages), total_entities, entity_types


if __name__ == "__main__":
    config    = load_config()
    cities    = config["cities"]
    processed = config["paths"]["processed_data"]

    nlp = load_spacy()
    print(f"\nRunning NER + POS tagging for {len(cities)} cities...\n")

    success, failed = 0, []
    total_passages = 0
    total_entities = 0

    for city in cities:
        try:
            print(f"Analyzing: {city}")
            passages, entities, ent_summary = process_city(city, processed, nlp)
            top = sorted(ent_summary.items(), key=lambda x: x[1], reverse=True)[:3]
            top_str = "  |  ".join([f"{k}: {v}" for k, v in top])
            print(f"  {passages} passages  |  {entities} entities  |  top: {top_str}")
            total_passages += passages
            total_entities += entities
            success += 1
        except Exception as e:
            print(f"  Failed: {city} — {e}")
            failed.append(city)

    print(f"\nDone. {success} cities, {total_passages} passages, {total_entities} total entities.")
    if failed:
        print(f"Failed: {failed}")