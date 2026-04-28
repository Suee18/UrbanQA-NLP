"""Query processing — runs at QA time on the user's question.

Two jobs:
  1. Classify question type (what/who/when/where/how-many/why/which/other)
     and produce a list of expected NER entity types — used later in stage 7
     to validate that the extracted answer span has the right entity type.
  2. Detect which of the 20 corpus cities the question is about, so the
     retriever can filter to that city's passages before scoring.

Returns a JSON-serializable dict so the same call can feed Streamlit, the
future Unreal/UDP server, and the eval loop without any reshaping.
"""

import re
import yaml
import spacy


# ── Question type rules ────────────────────────────────────────────────
# Order matters — multi-token patterns checked before single-word ones.
QUESTION_PATTERNS = [
    ("how_many",   re.compile(r"^\s*how\s+(many|much)\b", re.I)),
    ("how",        re.compile(r"^\s*how\b", re.I)),
    ("what",       re.compile(r"^\s*what\b", re.I)),
    ("who",        re.compile(r"^\s*who\b", re.I)),
    ("when",       re.compile(r"^\s*when\b", re.I)),
    ("where",      re.compile(r"^\s*where\b", re.I)),
    ("why",        re.compile(r"^\s*why\b", re.I)),
    ("which",      re.compile(r"^\s*which\b", re.I)),
]

# Map question type → spaCy NER labels we'd expect a valid answer span to carry.
# Used in stage 7 (answer extraction) to filter out type-mismatched spans.
EXPECTED_ENTITY_TYPES = {
    "who":      ["PERSON", "ORG"],
    "when":     ["DATE", "TIME"],
    "where":    ["GPE", "LOC", "FAC"],
    "how_many": ["CARDINAL", "QUANTITY", "MONEY", "PERCENT"],
    "what":     [],   # too broad to constrain
    "how":      [],
    "which":    [],
    "why":      [],
    "other":    [],
}


# ── City alias map ─────────────────────────────────────────────────────
# Manually curated — covers historical names, abbreviations, and the
# ASCII-vs-diacritic variants users will type.
CITY_ALIASES = {
    "Cairo":         ["cairo", "al-qahirah", "el cairo"],
    "Paris":         ["paris"],
    "Tokyo":         ["tokyo", "edo"],
    "London":        ["london"],
    "New York City": ["new york city", "new york", "nyc", "the big apple", "manhattan"],
    "Istanbul":      ["istanbul", "constantinople", "byzantium"],
    "Buenos Aires":  ["buenos aires", "ba"],
    "Lagos":         ["lagos"],
    "Mumbai":        ["mumbai", "bombay"],
    "Beijing":       ["beijing", "peking"],
    "Mexico City":   ["mexico city", "ciudad de mexico", "cdmx", "distrito federal"],
    "São Paulo":     ["são paulo", "sao paulo", "sp"],
    "Berlin":        ["berlin"],
    "Sydney":        ["sydney"],
    "Dubai":         ["dubai"],
    "Rome":          ["rome", "roma"],
    "Bangkok":       ["bangkok", "krung thep"],
    "Toronto":       ["toronto"],
    "Nairobi":       ["nairobi"],
    "Jakarta":       ["jakarta", "batavia"],
}


def load_config(config_path="configs/config.yaml"):
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_spacy():
    return spacy.load("en_core_web_lg")


def classify_question_type(question):
    """Match against ordered regex patterns. Falls back to 'other'."""
    for q_type, pattern in QUESTION_PATTERNS:
        if pattern.match(question):
            return q_type
    return "other"


def _build_alias_lookup(cities):
    """Flatten alias map into {alias_lowercased: canonical_city}, scoped to
    the cities the corpus actually covers (config-driven)."""
    lookup = {}
    for city in cities:
        for alias in CITY_ALIASES.get(city, [city.lower()]):
            lookup[alias.lower()] = city
    return lookup


def detect_city(question, cities, nlp, alias_lookup=None):
    """Return (canonical_city, confidence) or (None, 0.0).

    Two-pass strategy:
      1. Substring match against the alias map — catches everything spaCy
         might miss ("nyc", "bombay", "cdmx") and runs at near-zero cost.
      2. Fall back to spaCy NER (GPE/LOC) and try to alias-match the
         entity text — catches casing/diacritic variants the substring
         pass missed.
    """
    if alias_lookup is None:
        alias_lookup = _build_alias_lookup(cities)

    q_lower = question.lower()

    # Pass 1: longest alias first so "new york city" beats "new york".
    for alias in sorted(alias_lookup.keys(), key=len, reverse=True):
        # word-boundary match, so "rome" doesn't fire on "chrome"
        if re.search(rf"\b{re.escape(alias)}\b", q_lower):
            return alias_lookup[alias], 1.0

    # Pass 2: NER fallback.
    doc = nlp(question)
    for ent in doc.ents:
        if ent.label_ in ("GPE", "LOC", "FAC"):
            ent_lower = ent.text.lower().strip()
            if ent_lower in alias_lookup:
                return alias_lookup[ent_lower], 0.7

    return None, 0.0


def process_query(question, cities, nlp, alias_lookup=None):
    """Top-level entry point — returns the JSON-serializable query record."""
    q_type = classify_question_type(question)
    city, conf = detect_city(question, cities, nlp, alias_lookup)

    return {
        "question":              question,
        "question_type":         q_type,
        "expected_entity_types": EXPECTED_ENTITY_TYPES[q_type],
        "detected_city":         city,
        "city_confidence":       conf,
    }


if __name__ == "__main__":
    # Quick smoke test — prints what process_query returns for a few queries
    # spanning every question type and every alias-detection branch.
    import json

    config = load_config()
    cities = config["cities"]
    nlp = load_spacy()
    alias_lookup = _build_alias_lookup(cities)

    samples = [
        "When was Cairo founded?",
        "Who designed the Sydney Opera House?",
        "Where is the Eiffel Tower in Paris?",
        "How many people live in Mumbai?",
        "What is Bombay famous for?",
        "Which year did Constantinople fall?",
        "Tell me about NYC subway system.",
        "Why is São Paulo so big?",
        "How does Tokyo manage earthquakes?",
        "What is the capital of France?",
    ]

    for q in samples:
        result = process_query(q, cities, nlp, alias_lookup)
        print(json.dumps(result, ensure_ascii=False))
