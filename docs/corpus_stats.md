# Corpus Statistics

## Summary

| Metric | Value |
|---|---|
| Cities covered | 20 |
| Total passages | 20,554 |
| Data sources | 3 (Wikipedia, NewsAPI, Tourism) |
| Raw files | 60 (3 per city) |
| Processed files | 20 (1 passages file per city) |
| Passage window | 3 sentences, stride 1 |

## Passages per city

| City | Passages | Wikipedia | News | Tourism |
|---|---|---|---|---|
| Sydney | 1,379 | ~1,100 | ~180 | ~99 |
| New York City | 1,231 | ~960 | ~160 | ~111 |
| London | 1,228 | ~980 | ~150 | ~98 |
| São Paulo | 1,199 | ~950 | ~160 | ~89 |
| Paris | 1,157 | ~920 | ~140 | ~97 |
| Berlin | 1,063 | ~820 | ~140 | ~103 |
| Toronto | 1,081 | ~860 | ~130 | ~91 |
| Dubai | 1,081 | ~860 | ~150 | ~71 |
| Rome | 1,041 | ~820 | ~140 | ~81 |
| Beijing | 1,037 | ~820 | ~150 | ~67 |
| Cairo | 1,082 | ~840 | ~150 | ~92 |
| Buenos Aires | 1,000 | ~790 | ~140 | ~70 |
| Mexico City | 956 | ~750 | ~150 | ~56 |
| Istanbul | 950 | ~760 | ~150 | ~40 |
| Lagos | 946 | ~740 | ~150 | ~56 |
| Bangkok | 940 | ~730 | ~150 | ~60 |
| Tokyo | 909 | ~700 | ~130 | ~79 |
| Nairobi | 895 | ~710 | ~130 | ~55 |
| Mumbai | 723 | ~580 | ~130 | ~13 |
| Jakarta | 656 | ~510 | ~120 | ~26 |
| **Total** | **20,554** | | | |

*Note: Wikipedia/news/tourism breakdown is approximate — run `notebooks/01_corpus_exploration.ipynb` for exact counts.*

## Coverage notes

**Well-covered cities (1,100+ passages):** Sydney, New York City, London, São Paulo, Paris — rich Wikipedia articles with many sections and good NewsAPI coverage.

**Thinner cities (under 800 passages):** Mumbai (723), Jakarta (656) — shorter Wikipedia articles and fewer tourism sections. This may affect QA performance on these cities and is worth noting in the evaluation error analysis.

## Token statistics

Approximate figures based on segmentation output. Run `notebooks/01_corpus_exploration.ipynb` for exact distribution plots.

| Metric | Approximate value |
|---|---|
| Avg raw tokens per passage | ~45 |
| Avg normalized tokens per passage | ~22 |
| Total raw tokens (corpus) | ~925,000 |
| Total normalized tokens (corpus) | ~452,000 |

## Data freshness

- Wikipedia articles: scraped at project start — static snapshot
- NewsAPI articles: scraped at project start — reflects news at that date
- Tourism sections: extracted from Wikipedia — same snapshot as Wikipedia

For reproducibility, all scraping timestamps are stored in the `scraped_at` field of each raw JSON file.
