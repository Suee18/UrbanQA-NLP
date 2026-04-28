# Error analysis — `bm25` mode

- Total questions: **200**
- Failures (EM = 0): **50** (25.0%)

## Failures by category

| Category | Count | % of total |
|---|---:|---:|
| `RETRIEVAL_MISS` | 21 | 10.5% |
| `PARTIAL_MATCH` | 17 | 8.5% |
| `EXTRACTION_FAIL` | 12 | 6.0% |

## Failures by question type

| Type | Failures / Total |
|---|---:|
| what | 22 / 83 |
| when | 7 / 31 |
| who | 7 / 22 |
| how_many | 6 / 18 |
| other | 3 / 28 |
| how | 3 / 4 |
| where | 1 / 8 |
| which | 1 / 6 |

## Failures by city

| City | Failures / Total |
|---|---:|
| Cairo | 5 / 10 |
| Lagos | 4 / 10 |
| São Paulo | 4 / 10 |
| Rome | 4 / 10 |
| London | 3 / 10 |
| Bangkok | 3 / 10 |
| Jakarta | 3 / 10 |
| Paris | 2 / 10 |
| Tokyo | 2 / 10 |
| New York City | 2 / 10 |
| Istanbul | 2 / 10 |
| Buenos Aires | 2 / 10 |
| Mumbai | 2 / 10 |
| Mexico City | 2 / 10 |
| Berlin | 2 / 10 |
| Sydney | 2 / 10 |
| Toronto | 2 / 10 |
| Nairobi | 2 / 10 |
| Beijing | 1 / 10 |
| Dubai | 1 / 10 |

## Example failures per category

### `PARTIAL_MATCH`

- **Q:** When did the throne of the Mamluk Sultanate pass from one mamluk to another?
  - city: `Cairo`, type: `when`
  - predicted: `'Between 1250 and 1517'`
  - gold: `['Between 1250']`

- **Q:** How many times higher is the air pollution in Cairo than the safety level?
  - city: `Cairo`, type: `how_many`
  - predicted: `'12'`
  - gold: `['nearly 12']`

- **Q:** What are the three departments of the inner suburbs called?
  - city: `Paris`, type: `what`
  - predicted: `'Hauts-de-Seine, Seine-Saint-Denis and Val-de-Marne'`
  - gold: `['Hauts-de-Seine']`

### `RETRIEVAL_MISS`

- **Q:** When did Tahrir Square continue to be the primary destination for protests in Cairo?
  - city: `Cairo`, type: `when`
  - predicted: `'In the following days'`
  - gold: `['the following days']`

- **Q:** Where is the Metropolitan Assembly located?
  - city: `Tokyo`, type: `where`
  - predicted: `'Shinjuku Ward'`
  - gold: `['Metropolis']`

- **Q:** Who created Japan's first emissions cap system?
  - city: `Tokyo`, type: `who`
  - predicted: `'Governor Shintaro Ishihara'`
  - gold: `['Shintaro Ishihara']`

### `EXTRACTION_FAIL`

- **Q:** What organization offers support for company incorporation?
  - city: `Cairo`, type: `what`
  - predicted: `"GAFI's Investor Service Center"`
  - gold: `['GAFI']`

- **Q:** How many lines are in the Metro system?
  - city: `Cairo`, type: `how_many`
  - predicted: `'three'`
  - gold: `['1 to 3']`

- **Q:** In what year did Paris host the FIFA World Cup?
  - city: `Paris`, type: `other`
  - predicted: `'1998'`
  - gold: `['1938']`
