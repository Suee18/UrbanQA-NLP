"""Load custom digital-twin documentation as a corpus source.

The Munich Smart City Digital Twin is the user's own project — not on Wikipedia
and not in the news. This loader pulls a hand-curated markdown doc describing
the digital twin (architecture, agents, protocols, dashboard, etc.) and emits
a `*_digital_twin_clean.json` file in exactly the same shape the cleaner
produces for the other source types. The segmenter reads it just like
wikipedia/news/tourism — no other code path needs to know about it.

Source file: data/digital_twin/{slug}.md
Output:      data/processed/{slug}_digital_twin_clean.json

The output is tagged `source="digital_twin"`, so retrieved passages are
attributable in the answer payload (your future Unreal dashboard can show
"source: digital_twin" vs "source: wikipedia" right next to the answer).
"""

import json
import os
import re
import yaml
from datetime import datetime, timezone


def load_config(config_path="configs/config.yaml"):
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def strip_markdown(text):
    """Drop markdown control chars but keep all the prose. The downstream
    cleaner does additional cleanup; we only need to be 'good enough' here.
    """
    # Remove markdown headings (## Title → Title)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # Strip emphasis markers (*x*, **x**, _x_)
    text = re.sub(r"(\*\*|__)(.*?)\1", r"\2", text)
    text = re.sub(r"(\*|_)(.*?)\1", r"\2", text)
    # Strip inline code backticks
    text = re.sub(r"`([^`]+)`", r"\1", text)
    # Collapse multiple blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def load_one(city_name, source_dir, out_dir):
    """Read data/digital_twin/{slug}.md → data/processed/{slug}_digital_twin_clean.json."""
    slug    = city_name.lower().replace(" ", "_")
    md_path = os.path.join(source_dir, f"{slug}.md")

    if not os.path.exists(md_path):
        return None  # silently skip cities without a digital-twin doc

    with open(md_path, "r", encoding="utf-8") as f:
        raw = f.read()

    cleaned = strip_markdown(raw)

    # Match the shape produced by cleaner.clean_wikipedia — same fields, just
    # source="digital_twin" instead. Segmenter then handles it identically.
    record = {
        "city":       city_name,
        "source":     "digital_twin",
        "url":        "",  # internal doc, no URL
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "text":       cleaned,
    }

    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{slug}_digital_twin_clean.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)

    return out_path, len(cleaned)


if __name__ == "__main__":
    config = load_config()
    cities = config["cities"]
    source_dir = "data/digital_twin"
    out_dir    = config["paths"]["processed_data"]

    print(f"Loading digital-twin docs from {source_dir}...\n")

    found = 0
    for city in cities:
        result = load_one(city, source_dir, out_dir)
        if result is None:
            continue
        out_path, char_count = result
        print(f"  {city}: {char_count:,} chars → {out_path}")
        found += 1

    if found == 0:
        print(f"  No digital-twin docs found in {source_dir}.")
    else:
        print(f"\nDone. {found} city/cities loaded.")
