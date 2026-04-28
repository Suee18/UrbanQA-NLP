# Error analysis — `hybrid` mode

- Total questions: **200**
- Failures (EM = 0): **47** (23.5%)

## Failures by category

| Category | Count | % of total |
|---|---:|---:|
| `PARTIAL_MATCH` | 26 | 13.0% |
| `EXTRACTION_FAIL` | 16 | 8.0% |
| `RETRIEVAL_MISS` | 5 | 2.5% |

## Failures by question type

| Type | Failures / Total |
|---|---:|
| what | 20 / 83 |
| when | 7 / 31 |
| who | 7 / 22 |
| how_many | 6 / 18 |
| other | 3 / 28 |
| how | 3 / 4 |
| which | 1 / 6 |
| where | 0 / 8 |

## Failures by city

| City | Failures / Total |
|---|---:|
| Cairo | 5 / 10 |
| Lagos | 4 / 10 |
| New York City | 3 / 10 |
| São Paulo | 3 / 10 |
| Rome | 3 / 10 |
| Bangkok | 3 / 10 |
| Jakarta | 3 / 10 |
| Paris | 2 / 10 |
| London | 2 / 10 |
| Istanbul | 2 / 10 |
| Buenos Aires | 2 / 10 |
| Beijing | 2 / 10 |
| Mexico City | 2 / 10 |
| Berlin | 2 / 10 |
| Sydney | 2 / 10 |
| Toronto | 2 / 10 |
| Nairobi | 2 / 10 |
| Tokyo | 1 / 10 |
| Mumbai | 1 / 10 |
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

- **Q:** How many lines are in the Metro system?
  - city: `Cairo`, type: `how_many`
  - predicted: `'three operational lines numbered from 1 to 3'`
  - gold: `['1 to 3']`

### `RETRIEVAL_MISS`

- **Q:** When did Tahrir Square continue to be the primary destination for protests in Cairo?
  - city: `Cairo`, type: `when`
  - predicted: `'In the following days'`
  - gold: `['the following days']`

- **Q:** Who directs the administration of Beijing?
  - city: `Beijing`, type: `who`
  - predicted: `'Municipal CCP Committee'`
  - gold: `['the State Council']`

- **Q:** How many municipalities are in the State of Mexico?
  - city: `Mexico City`, type: `how_many`
  - predicted: `'twenty-two'`
  - gold: `['59']`

### `EXTRACTION_FAIL`

- **Q:** What organization offers support for company incorporation?
  - city: `Cairo`, type: `what`
  - predicted: `"GAFI's Investor Service Center"`
  - gold: `['GAFI']`

- **Q:** In what year did Paris host the FIFA World Cup?
  - city: `Paris`, type: `other`
  - predicted: `'1998'`
  - gold: `['1938']`

- **Q:** What is the largest municipal healthcare system in the United States?
  - city: `New York City`, type: `what`
  - predicted: `'NYC Health + Hospitals'`
  - gold: `['HHC']`
