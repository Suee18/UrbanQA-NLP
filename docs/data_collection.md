# Data Collection

## Overview

Three data sources are used to build the city knowledge corpus. All raw files are stored in `data/raw/` and are gitignored — run the pipeline to regenerate them.

## Sources

### 1. Wikipedia API
**Script:** `src/collection/scraper.py`
**Output:** `data/raw/{city}.json`

The primary source. Wikipedia provides consistent, encyclopedic coverage for all 20 cities including history, geography, governance, economy, demographics, culture, and landmarks. Coverage quality is uniform across all cities which makes it the most reliable source for QA.

Each file contains:
- `city` — city name
- `title` — Wikipedia article title
- `url` — article URL
- `scraped_at` — UTC timestamp
- `sections` — list of section names in the article
- `text` — full article plain text

### 2. NewsAPI
**Script:** `src/collection/news_scraper.py`
**Output:** `data/raw/{city}_news.json`
**Requires:** `NEWSAPI_KEY` in `.env` file — register free at https://newsapi.org

Fetches the 10 most relevant recent news articles per city. NewsAPI aggregates 100+ outlets (BBC, Reuters, Al Jazeera, CNN etc.) so a single API call covers all major sources without individual site scraping. Adds recency and event-based knowledge that Wikipedia lacks.

Each file contains:
- `city` — city name
- `scraped_at` — UTC timestamp
- `article_count` — number of articles retrieved
- `articles` — list of articles, each with `title`, `source`, `published_at`, `url`, `content`

**Note:** NewsAPI free tier returns truncated article content (200 chars). Full content requires a paid plan. For the course project the truncated content is sufficient for passage generation.

### 3. Tourism Sections (Wikipedia)
**Script:** `src/collection/tourism_extractor.py`
**Output:** `data/raw/{city}_tourism.json`

Rather than scraping external tourism portals (which are inconsistent across cities and prone to bot-blocking), this extractor pulls tourism-relevant sections directly from the Wikipedia articles already collected. Sections matched include: tourism, attractions, landmarks, culture, sights, museums, architecture, places of interest.

Each file contains:
- `city` — city name
- `source` — `wikipedia_tourism_sections`
- `section_count` — number of matched sections
- `sections` — list of `{section, text}` objects

## City List

Defined in `configs/config.yaml`. 20 cities selected to cover diverse regions, population sizes, and cultural backgrounds:

| Region | Cities |
|---|---|
| Africa | Cairo, Lagos, Nairobi |
| Asia | Tokyo, Mumbai, Beijing, Bangkok, Jakarta |
| Europe | Paris, London, Berlin, Rome |
| Americas | New York City, Buenos Aires, Mexico City, São Paulo, Toronto |
| Middle East | Istanbul, Dubai |
| Oceania | Sydney |

## Design Decisions

**Why Wikipedia as primary source?**
Uniform coverage, clean text, freely accessible, reproducible. Every city has a detailed article with consistent section structure.

**Why not scrape tourism portals directly?**
Lonely Planet, TripAdvisor, and similar sites either block automated requests, require JavaScript rendering, or have inconsistent HTML structure across cities. Wikipedia's tourism sections provide equivalent content with zero scraping friction.

**Why NewsAPI over RSS feeds?**
A single API call replaces 100+ individual site scrapers. The free tier is sufficient for course project purposes.
