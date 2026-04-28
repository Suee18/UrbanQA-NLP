# Error analysis — `dense` mode

- Total questions: **200**
- Failures (EM = 0): **58** (29.0%)

## Failures by category

| Category | Count | % of total |
|---|---:|---:|
| `RETRIEVAL_MISS` | 29 | 14.5% |
| `PARTIAL_MATCH` | 16 | 8.0% |
| `EXTRACTION_FAIL` | 13 | 6.5% |

## Failures by question type

| Type | Failures / Total |
|---|---:|
| what | 25 / 83 |
| who | 9 / 22 |
| when | 8 / 31 |
| how_many | 7 / 18 |
| other | 4 / 28 |
| how | 3 / 4 |
| where | 1 / 8 |
| which | 1 / 6 |

## Failures by city

| City | Failures / Total |
|---|---:|
| Cairo | 6 / 10 |
| Rome | 6 / 10 |
| Lagos | 5 / 10 |
| Beijing | 4 / 10 |
| São Paulo | 4 / 10 |
| Jakarta | 4 / 10 |
| Paris | 3 / 10 |
| Tokyo | 3 / 10 |
| Sydney | 3 / 10 |
| Bangkok | 3 / 10 |
| London | 2 / 10 |
| New York City | 2 / 10 |
| Istanbul | 2 / 10 |
| Buenos Aires | 2 / 10 |
| Mumbai | 2 / 10 |
| Mexico City | 2 / 10 |
| Toronto | 2 / 10 |
| Nairobi | 2 / 10 |
| Berlin | 1 / 10 |
| Dubai | 0 / 10 |

## Example failures per category

### `PARTIAL_MATCH`

- **Q:** When did the throne of the Mamluk Sultanate pass from one mamluk to another?
  - city: `Cairo`, type: `when`
  - predicted: `'Between 1250 and 1517'`
  - gold: `['Between 1250']`

- **Q:** Who created Japan's first emissions cap system?
  - city: `Tokyo`, type: `who`
  - predicted: `'Governor Shintaro Ishihara'`
  - gold: `['Shintaro Ishihara']`

- **Q:** Who wrote Sherlock Holmes?
  - city: `London`, type: `who`
  - predicted: `'Arthur Conan Doyle'`
  - gold: `["Arthur Conan Doyle's"]`

### `RETRIEVAL_MISS`

- **Q:** When did Tahrir Square continue to be the primary destination for protests in Cairo?
  - city: `Cairo`, type: `when`
  - predicted: `'In the following days'`
  - gold: `['the following days']`

- **Q:** How many times higher is the air pollution in Cairo than the safety level?
  - city: `Cairo`, type: `how_many`
  - predicted: `''`
  - gold: `['nearly 12']`

- **Q:** How many books did the library of Cairo contain?
  - city: `Cairo`, type: `how_many`
  - predicted: `'several million'`
  - gold: `['hundreds of thousands']`

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
