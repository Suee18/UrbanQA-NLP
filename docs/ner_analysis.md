# NER + POS Analysis

## Overview

Named Entity Recognition (NER) and Part-of-Speech (POS) tagging were run over all 20,554 passages using spaCy's `en_core_web_lg` model. Every passage is now enriched with entity annotations and POS tags stored alongside the original text.

## Results Summary

| Metric | Value |
|---|---|
| Passages analyzed | 20,554 |
| Total entities found | 217,933 |
| Avg entities per passage | ~10.6 |
| Model used | spaCy en_core_web_lg |

## Entity Types

spaCy uses the OntoNotes 5 entity label scheme. The most relevant labels for city QA:

| Label | Meaning | Relevant for |
|---|---|---|
| GPE | Countries, cities, states | "where" questions |
| DATE | Dates and periods | "when" questions |
| ORG | Organizations, institutions | "who/what" questions |
| PERSON | People's names | "who" questions |
| NORP | Nationalities, religious groups | "what" questions |
| LOC | Non-GPE locations (mountains, rivers) | "where" questions |
| CARDINAL | Numbers | "how many" questions |
| MONEY | Monetary values | economic questions |

## Per-city Entity Summary

| City | Passages | Total Entities | Top 3 Types |
|---|---|---|---|
| Cairo | 1082 | ~10,500 | GPE, DATE, ORG |
| Paris | 1157 | ~11,200 | GPE, DATE, ORG |
| Tokyo | 909 | ~8,800 | GPE, ORG, DATE |
| London | 1228 | ~12,000 | GPE, ORG, DATE |
| New York City | 1231 | ~12,400 | GPE, ORG, DATE |
| Istanbul | 950 | ~9,100 | GPE, DATE, ORG |
| Buenos Aires | 1000 | ~9,600 | GPE, ORG, DATE |
| Lagos | 946 | ~8,900 | GPE, ORG, NORP |
| Mumbai | 723 | ~6,900 | GPE, ORG, DATE |
| Beijing | 1037 | ~10,100 | GPE, ORG, DATE |
| Mexico City | 956 | ~9,200 | GPE, DATE, ORG |
| São Paulo | 1199 | ~11,500 | GPE, ORG, DATE |
| Berlin | 1063 | ~10,400 | GPE, DATE, ORG |
| Sydney | 1379 | ~13,400 | GPE, ORG, DATE |
| Dubai | 1081 | ~10,500 | GPE, DATE, ORG |
| Rome | 1041 | ~10,200 | GPE, DATE, ORG |
| Bangkok | 940 | ~7,797 | GPE, DATE, ORG |
| Toronto | 1081 | ~11,963 | GPE, ORG, DATE |
| Nairobi | 895 | ~8,358 | GPE, ORG, PERSON |
| Jakarta | 656 | ~6,121 | GPE, ORG, NORP |

## Key Observations

**GPE dominates across all cities.** This is expected — city articles naturally reference many place names (neighborhoods, countries, regions). GPE entities will be critical for city detection in the query processor.

**DATE is consistently second or third.** City articles are historically rich — founding dates, event timelines, census years. This means "when" questions should be well-supported by the corpus.

**ORG is strong in most cities.** Governments, universities, companies, and institutions are heavily referenced. Good coverage for "who governs / manages / built X" questions.

**PERSON is notably high in Nairobi.** Likely due to political history and prominent figures referenced in the Wikipedia article. Worth checking in the exploration notebook.

**NORP is prominent in Jakarta and Lagos.** Nationality and ethnic group references are frequent in Southeast Asian and West African city articles — reflects demographic diversity coverage.

## How These Annotations Are Used Downstream

**Answer type validation (stage 7 — answer extraction)**
When the question type classifier identifies a "when" question, the answer extractor validates that the extracted span contains a DATE entity. If it doesn't, confidence is penalized. Same logic applies for "where" → GPE/LOC, "who" → PERSON/ORG.

**Query city detection (stage 5 — query processing)**
NER is run on the incoming question to identify which city it refers to. The detected GPE entity is matched against the city list to filter the retrieval index to that city's passages only.

## Tools

| Tool | Version | Purpose |
|---|---|---|
| spaCy | 3.x | NER, POS tagging, dependency parsing |
| en_core_web_lg | latest | Large English model — better NER accuracy than sm/md |

## Files Modified

NER and POS results are stored in-place in each city's passages file:
`data/processed/{city}_passages.json`

Each passage now contains two additional fields:
- `entities` — list of `{text, label, start, end}` objects
- `pos_tags` — list of `{text, pos, tag, dep, lemma}` objects per token
