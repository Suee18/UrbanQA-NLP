import json
import os
import yaml

TOURISM_SECTIONS = [
    "tourism", "attractions", "landmarks", "culture",
    "sights", "places of interest", "points of interest",
    "things to do", "museums", "architecture"
]

def load_config(config_path="configs/config.yaml"):
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def extract_tourism_sections(wiki_json):
    text = wiki_json.get("text", "")
    sections = wiki_json.get("sections", [])

    extracted = []
    lines = text.split("\n")
    current_section = None
    buffer = []

    for line in lines:
        # detect section headers (Wikipedia format uses == Header ==)
        stripped = line.strip().lower().replace("=", "").strip()
        if any(t in stripped for t in TOURISM_SECTIONS):
            if current_section and buffer:
                extracted.append({
                    "section": current_section,
                    "text": " ".join(buffer).strip()
                })
            current_section = stripped
            buffer = []
        elif current_section:
            if line.strip():
                buffer.append(line.strip())
            # stop collecting when next major section starts
            elif buffer and line.strip() == "":
                pass

    # flush last section
    if current_section and buffer:
        extracted.append({
            "section": current_section,
            "text": " ".join(buffer).strip()
        })

    return extracted

def save_tourism(city_name, sections, out_dir="data/raw"):
    if not sections:
        print(f"  No tourism sections found: {city_name}")
        return

    filename = city_name.lower().replace(" ", "_") + "_tourism.json"
    path = os.path.join(out_dir, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({
            "city": city_name,
            "source": "wikipedia_tourism_sections",
            "section_count": len(sections),
            "sections": sections
        }, f, ensure_ascii=False, indent=2)
    print(f"  Saved: {path} ({len(sections)} sections)")

if __name__ == "__main__":
    config = load_config()
    cities = config["cities"]
    raw_dir = config["paths"]["raw_data"]

    print(f"Extracting tourism sections for {len(cities)} cities...\n")
    success, failed = 0, []

    for city in cities:
        filename = city.lower().replace(" ", "_") + ".json"
        path = os.path.join(raw_dir, filename)

        try:
            print(f"Processing: {city}")
            with open(path, "r", encoding="utf-8") as f:
                wiki_json = json.load(f)

            sections = extract_tourism_sections(wiki_json)
            save_tourism(city, sections, raw_dir)
            success += 1
        except FileNotFoundError:
            print(f"  Missing Wikipedia file: {path}")
            failed.append(city)
        except Exception as e:
            print(f"  Failed: {city} — {e}")
            failed.append(city)

    print(f"\nDone. {success} processed, {len(failed)} failed.")
    if failed:
        print(f"Failed: {failed}")