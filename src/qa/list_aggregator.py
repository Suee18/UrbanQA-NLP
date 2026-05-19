"""List-mode aggregation: turn retrieved passages into a ranked, evidenced
list of items, not a frequency-counted name list.

For list-style questions ("top 10 attractions in Paris", "things to visit in
Cairo", "popular museums in Berlin"), extractive QA can only return a single
span and is structurally wrong. The retriever returns relevant passages, but
the consumer needs *items*, not paragraphs. This module bridges the gap.

Pipeline:
  1. Run spaCy NER over each retrieved passage.
  2. Drop low-signal entities (the query city itself, single-char strings,
     pure numerics, generic noun phrases).
  3. Merge near-duplicate surface forms ("Louvre" ↔ "the Louvre" ↔
     "Louvre Museum") into a single item with a canonical name + aliases.
  4. Score each item by rank-weighted mention count, boosted when its NER
     label matches the question's intent (keyword cue or expected_entity_types).
  5. For each kept item, pull the best supporting sentence from the highest-
     ranked passage where it appears — this is the "evidence snippet" the UI
     surfaces.
  6. Return top-N items.

Each item is JSON-serializable so it flows through to Streamlit / the
WebSocket server / Unreal without reshaping.
"""

from collections import defaultdict


# When the question contains one of these keywords, entities of the
# corresponding labels are boosted. Captures "top museums" → FAC, etc.
# Plurals/singulars listed explicitly — simpler and clearer than stemming.
KEYWORD_LABEL_BOOSTS = {
    "museum": {"FAC", "ORG"}, "museums": {"FAC", "ORG"},
    "gallery": {"FAC", "ORG"}, "galleries": {"FAC", "ORG"},
    "restaurant": {"ORG", "FAC"}, "restaurants": {"ORG", "FAC"},
    "cafe": {"ORG", "FAC"}, "cafes": {"ORG", "FAC"},
    "hotel": {"ORG", "FAC"}, "hotels": {"ORG", "FAC"},
    "park": {"LOC", "FAC"}, "parks": {"LOC", "FAC"},
    "beach": {"LOC"}, "beaches": {"LOC"},
    "landmark": {"FAC", "LOC"}, "landmarks": {"FAC", "LOC"},
    "attraction": {"FAC", "LOC", "EVENT"}, "attractions": {"FAC", "LOC", "EVENT"},
    "sight": {"FAC", "LOC"}, "sights": {"FAC", "LOC"},
    "building": {"FAC"}, "buildings": {"FAC"},
    "monument": {"FAC"}, "monuments": {"FAC"},
    "church": {"FAC"}, "churches": {"FAC"},
    "cathedral": {"FAC"}, "cathedrals": {"FAC"},
    "temple": {"FAC"}, "temples": {"FAC"},
    "mosque": {"FAC"}, "mosques": {"FAC"},
    "palace": {"FAC"}, "palaces": {"FAC"},
    "neighborhood": {"LOC", "GPE"}, "neighborhoods": {"LOC", "GPE"},
    "district": {"LOC", "GPE"}, "districts": {"LOC", "GPE"},
    "event": {"EVENT"}, "events": {"EVENT"},
    "festival": {"EVENT"}, "festivals": {"EVENT"},
    "dish": {"PRODUCT"}, "dishes": {"PRODUCT"},
    "food": {"PRODUCT"}, "foods": {"PRODUCT"},
}

# NER labels worth surfacing in a list answer. Anything else (DATE,
# CARDINAL, MONEY, PERSON, NORP, …) is filtered before scoring.
WANTED_LABELS = {"FAC", "LOC", "GPE", "ORG", "EVENT", "WORK_OF_ART", "PRODUCT"}

# Surface forms we never want as list items even if NER tags them.
# These slip through as GPE/LOC/ORG and pollute "top places" lists.
GENERIC_DROPS = {
    "the city", "the area", "the region", "the country", "the world",
    "the centre", "the center", "downtown", "uptown", "midtown",
    "the north", "the south", "the east", "the west",
}

# Boost magnitudes — small enough that a single mention can't outrank
# something with several mentions, large enough to break ties in
# the desired direction.
KEYWORD_BOOST = 1.4
TYPE_BOOST = 1.3


def _norm(s):
    """Light normalization for matching surface forms. Keeps it tight so
    'Louvre' and 'the Louvre' collide but 'New York' and 'New York City'
    do not (the second is a distinct, more specific reference).
    """
    s = s.lower().strip()
    # strip leading articles
    for art in ("the ", "a ", "an "):
        if s.startswith(art):
            s = s[len(art):]
            break
    return s.strip()


def _is_generic(surface):
    n = _norm(surface)
    if n in GENERIC_DROPS:
        return True
    if len(n) < 3:
        return True
    if n.isdigit():
        return True
    return False


def _city_aliases(query, alias_lookup=None):
    """Surface forms we should drop because they refer to the query city
    itself. 'Top attractions in Paris' should not list 'Paris'."""
    out = set()
    city = query.get("detected_city")
    if city:
        out.add(_norm(city))
    if alias_lookup:
        for alias, mapped in alias_lookup.items():
            if mapped == city:
                out.add(_norm(alias))
    return out


def _is_city_reference(surface, city_norms):
    """True if surface refers to the query city — exact match or as a token
    inside a phrase like 'Greater Paris', 'Paris region', 'Central Paris'.
    Catches spaCy mis-tags where geographic areas get labeled ORG/LOC and
    pollute the list."""
    if not city_norms:
        return False
    n = _norm(surface)
    tokens = set(n.split())
    return any(c in tokens or n == c for c in city_norms)


def _question_label_boosts(question, query):
    """Labels that should be boosted for this question.

    Priority:
      1. keyword cue in the question itself (most specific signal)
      2. expected_entity_types from query processing (question-type heuristic)
    """
    q_lower = question.lower()
    boosted = set()
    for kw, labels in KEYWORD_LABEL_BOOSTS.items():
        # word-boundary check — avoid matching 'parks' inside 'sparkling'
        if f" {kw} " in f" {q_lower} " or q_lower.startswith(kw + " ") or q_lower.endswith(" " + kw) or q_lower == kw:
            boosted |= labels
    if not boosted:
        # fall back to question-type expected entity types
        expected = query.get("expected_entity_types") or []
        boosted = set(expected) & WANTED_LABELS
    return boosted


def _best_sentence_for(entity_text, passage_doc):
    """Return the sentence in passage_doc that contains entity_text (case-
    insensitive). Falls back to the first sentence if no match (shouldn't
    happen since the entity came from this passage)."""
    target = entity_text.lower()
    for sent in passage_doc.sents:
        if target in sent.text.lower():
            return sent.text.strip()
    return passage_doc.text[:200].strip()


def aggregate_list_results(passages, nlp, query, alias_lookup=None, top_n=10):
    """Build the enhanced list-mode payload.

    Args:
        passages: retrieved passages, each {rank, passage_id, city, source, text, score}
        nlp: loaded spaCy pipeline (en_core_web_lg)
        query: query-processor output (uses detected_city, expected_entity_types)
        alias_lookup: optional city alias map; lets us drop variants of the
            query city ('NYC' for 'New York City', 'CDMX' for 'Mexico City')
        top_n: how many items to return

    Returns:
        list[dict]: each item is
          {name, label, score, mentions, aliases, snippet,
           passage_id, source, passage_rank}
        sorted by score desc.
    """
    if not passages:
        return []

    drop_norms = _city_aliases(query, alias_lookup)
    boosted_labels = _question_label_boosts(query.get("question", ""), query)

    # Pass 1: collect all mentions, grouped by normalized surface form.
    # We also keep the parsed doc for each passage so we can pull snippets
    # in pass 2 without re-parsing.
    docs_by_rank = {}
    raw_mentions = []  # list of {surface, label, passage_rank, passage_idx}
    for idx, p in enumerate(passages):
        rank = p.get("rank", idx + 1)
        doc = nlp(p["text"])
        docs_by_rank[rank] = doc
        for ent in doc.ents:
            if ent.label_ not in WANTED_LABELS:
                continue
            surface = ent.text.strip()
            if _is_generic(surface):
                continue
            if _is_city_reference(surface, drop_norms):
                continue
            raw_mentions.append({
                "surface": surface,
                "label": ent.label_,
                "passage_rank": rank,
                "passage_idx": idx,
            })

    if not raw_mentions:
        return []

    # Pass 2: merge near-duplicates. Two surfaces are merged if one's
    # normalized form is contained in the other's (token-level via space-
    # boundary check, to avoid 'York' eating 'New York'). We process in
    # descending surface length so the longer canonical form wins.
    raw_mentions_sorted = sorted(raw_mentions, key=lambda m: -len(m["surface"]))
    groups = []  # each: {canonical, label, surfaces:set, mentions:list}

    def _contains_as_phrase(longer_norm, shorter_norm):
        if shorter_norm == longer_norm:
            return True
        return (f" {shorter_norm} " in f" {longer_norm} "
                or longer_norm.startswith(shorter_norm + " ")
                or longer_norm.endswith(" " + shorter_norm))

    for m in raw_mentions_sorted:
        m_norm = _norm(m["surface"])
        merged = False
        for g in groups:
            g_norm = _norm(g["canonical"])
            if _contains_as_phrase(g_norm, m_norm) or _contains_as_phrase(m_norm, g_norm):
                # Take the longer form as canonical
                if len(m["surface"]) > len(g["canonical"]):
                    g["canonical"] = m["surface"]
                g["surfaces"].add(m["surface"])
                g["mentions"].append(m)
                merged = True
                break
        if not merged:
            groups.append({
                "canonical": m["surface"],
                "label": m["label"],
                "surfaces": {m["surface"]},
                "mentions": [m],
            })

    # Pass 3: score each group. Base score is rank-weighted; boost when
    # the label matches a query-cued type.
    scored = []
    for g in groups:
        base = sum(1.0 / m["passage_rank"] for m in g["mentions"])
        score = base
        if g["label"] in boosted_labels:
            # apply both boosts if the keyword cue lands; type-only fallback
            # already covered by boosted_labels being populated from one source.
            score *= KEYWORD_BOOST
        # Best evidence: the mention in the highest-ranked (lowest-numbered) passage.
        best = min(g["mentions"], key=lambda m: m["passage_rank"])
        best_doc = docs_by_rank[best["passage_rank"]]
        snippet = _best_sentence_for(best["surface"], best_doc)
        best_passage = passages[best["passage_idx"]]
        aliases = sorted(s for s in g["surfaces"] if s != g["canonical"])

        scored.append({
            "name":         g["canonical"],
            "label":        g["label"],
            "score":        round(score, 4),
            "mentions":     len(g["mentions"]),
            "aliases":      aliases,
            "snippet":      snippet,
            "passage_id":   best_passage.get("passage_id"),
            "source":       best_passage.get("source"),
            "passage_rank": best["passage_rank"],
        })

    scored.sort(key=lambda x: -x["score"])
    return scored[:top_n]
