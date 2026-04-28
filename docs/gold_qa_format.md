# Gold QA Set — annotation guide

Evaluation reads `data/gold_qa/gold.jsonl` — one JSON object per line, each
representing one question-answer pair. Aim for **100+ pairs** spread across
all 20 cities and the 5 question types (`what`, `who`, `when`, `where`, `how_many`).

## Schema

| Field | Required | Notes |
|---|---|---|
| `id` | yes | Unique string. Just sequential — `"001"`, `"002"`, … |
| `city` | yes | Must match a city name from `configs/config.yaml` exactly. |
| `question` | yes | The natural-language question. |
| `answer` | yes | The canonical answer text. Keep it short — a span, not a sentence. |
| `answer_aliases` | no | List of additional valid answers (e.g. `["969 AD", "969 CE"]` for "969"). |
| `question_type` | no | One of `what`, `who`, `when`, `where`, `how_many`, `how`, `which`, `why`, `other`. If omitted, the query processor classifies it. |
| `gold_passage_id` | no | The exact passage ID where the answer lives (e.g. `"Cairo_wiki_6"`). **Including this enables Recall@k and MRR retrieval metrics** — strongly recommended for at least half the set. |

## Example entries

```jsonl
{"id": "001", "city": "Cairo", "question": "When was Cairo founded?", "answer": "969", "answer_aliases": ["969 AD", "969 CE"], "question_type": "when", "gold_passage_id": "Cairo_wiki_6"}
{"id": "002", "city": "Sydney", "question": "Who designed the Sydney Opera House?", "answer": "Jørn Utzon", "answer_aliases": ["Jorn Utzon"], "question_type": "who"}
{"id": "003", "city": "Paris", "question": "What river runs through Paris?", "answer": "Seine", "answer_aliases": ["the Seine"], "question_type": "what"}
{"id": "004", "city": "Tokyo", "question": "How many people live in Tokyo?", "answer": "13.96 million", "question_type": "how_many"}
{"id": "005", "city": "Istanbul", "question": "What was Istanbul previously called?", "answer": "Constantinople", "question_type": "what"}
```

## Annotation tips

1. **Find the answer first, write the question second.** Browse the passages in `data/processed/{city}_passages.json`, find a clean fact, then write a question for it. This makes `gold_passage_id` trivial and ensures answers are actually present in the corpus.

2. **Keep answers as spans.** "969" is gradeable; "Cairo was founded in 969 by the Fatimids" is not — it'll lose F1 because it's much longer than what the extractor will produce.

3. **Use `answer_aliases` for common variants.** Different date formats, ASCII vs diacritic spellings, with/without "the". The grader uses any of them.

4. **Spread across question types.** A 100-question set heavy on "what" tells you nothing about "when" performance. Aim for ~20 per type.

5. **Spread across cities.** Same logic — 80 Cairo questions and 1 Lagos question won't surface city-specific failures.

6. **Mix easy and hard.** Some answers should be in the very first sentence of a passage; others should require reasoning across multiple sentences. The mix is what makes the eval informative.

## Where it lives

- File: `data/gold_qa/gold.jsonl`
- Created by: you (manually) or via `notebooks/03_gold_qa_builder.ipynb` (helper notebook to come)
- Read by: `src/evaluation/metrics.py`
