"""Error analysis — categorizes every wrong prediction by which pipeline
stage broke. Reads the JSON produced by metrics.py and writes a markdown
report that's ready to drop into the final write-up.

Failure categories (in priority order — first match wins):
  1. CITY_NOT_DETECTED   — query processor failed to find the city
  2. RETRIEVAL_MISS      — gold passage wasn't in retrieved top-k
  3. EXTRACTION_FAIL     — gold passage WAS retrieved, but extractor
                           returned an empty/wrong span
  4. TYPE_MISMATCH       — extracted span has wrong entity type
                           (e.g. 'when' question got a non-DATE answer)
  5. PARTIAL_MATCH       — F1 > 0 but EM = 0 (mostly right, slightly off)

The point of this module is the report's analysis section: "of N failures,
X% were retrieval misses, Y% extraction failures, Z% type mismatches" —
which lets you propose targeted fixes per category.
"""

import json
import os
from collections import Counter, defaultdict


def categorize_failure(record):
    """Return a category string for one per-item record from metrics.evaluate_system().

    Preconditions: record["em"] == 0.0  (don't call this on successes).
    """
    if record.get("city") is None:
        return "CITY_NOT_DETECTED"

    # Did retrieval put the gold passage anywhere in the top-k?
    # Only meaningful if the gold set carried a gold_passage_id.
    if "recall@5" in record:
        if record["recall@5"] == 0.0:
            return "RETRIEVAL_MISS"

    # F1 > 0 but EM = 0 — mostly right, partial credit case
    if record["f1"] > 0.0:
        return "PARTIAL_MATCH"

    # Empty prediction = the QA reader gave up (SQuAD 2.0 unanswerable)
    if not record["predicted"].strip():
        return "EXTRACTION_FAIL"

    # Got an answer, but it's wrong type or just plain wrong
    return "EXTRACTION_FAIL"


def analyze(results):
    """Produce summary stats from the JSON returned by metrics.evaluate_system()."""
    per_item = results["per_item"]
    failures = [r for r in per_item if r["em"] == 0.0]

    cat_counts = Counter()
    cat_examples = defaultdict(list)
    for r in failures:
        cat = categorize_failure(r)
        cat_counts[cat] += 1
        if len(cat_examples[cat]) < 3:
            cat_examples[cat].append(r)

    by_type_failures = defaultdict(int)
    by_type_total    = defaultdict(int)
    for r in per_item:
        qt = r.get("question_type", "other")
        by_type_total[qt] += 1
        if r["em"] == 0.0:
            by_type_failures[qt] += 1

    by_city_failures = defaultdict(int)
    by_city_total    = defaultdict(int)
    for r in per_item:
        c = r.get("city") or "<unknown>"
        by_city_total[c] += 1
        if r["em"] == 0.0:
            by_city_failures[c] += 1

    return {
        "n_total":        len(per_item),
        "n_failures":     len(failures),
        "categories":     dict(cat_counts),
        "examples":       {c: cat_examples[c] for c in cat_counts},
        "by_question_type": {
            qt: {"failures": by_type_failures[qt], "total": by_type_total[qt]}
            for qt in by_type_total
        },
        "by_city": {
            c: {"failures": by_city_failures[c], "total": by_city_total[c]}
            for c in by_city_total
        },
    }


def to_markdown(analysis, mode_label="hybrid"):
    """Render analysis dict as a markdown section for the final report."""
    n_total    = analysis["n_total"]
    n_failures = analysis["n_failures"]
    pct = lambda x: f"{100*x/n_total:.1f}%"

    lines = []
    lines.append(f"# Error analysis — `{mode_label}` mode\n")
    lines.append(f"- Total questions: **{n_total}**")
    lines.append(f"- Failures (EM = 0): **{n_failures}** ({pct(n_failures)})\n")

    lines.append("## Failures by category\n")
    lines.append("| Category | Count | % of total |")
    lines.append("|---|---:|---:|")
    for cat, count in sorted(analysis["categories"].items(), key=lambda x: -x[1]):
        lines.append(f"| `{cat}` | {count} | {pct(count)} |")
    lines.append("")

    lines.append("## Failures by question type\n")
    lines.append("| Type | Failures / Total |")
    lines.append("|---|---:|")
    for qt, v in sorted(analysis["by_question_type"].items(), key=lambda x: -x[1]["failures"]):
        lines.append(f"| {qt} | {v['failures']} / {v['total']} |")
    lines.append("")

    lines.append("## Failures by city\n")
    lines.append("| City | Failures / Total |")
    lines.append("|---|---:|")
    for c, v in sorted(analysis["by_city"].items(), key=lambda x: -x[1]["failures"]):
        lines.append(f"| {c} | {v['failures']} / {v['total']} |")
    lines.append("")

    lines.append("## Example failures per category\n")
    for cat, examples in analysis["examples"].items():
        lines.append(f"### `{cat}`\n")
        for ex in examples:
            lines.append(f"- **Q:** {ex['question']}")
            lines.append(f"  - city: `{ex.get('city')}`, type: `{ex.get('question_type')}`")
            lines.append(f"  - predicted: `{ex['predicted']!r}`")
            lines.append(f"  - gold: `{ex['gold']}`")
            lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    import yaml

    def load_config(p="configs/config.yaml"):
        with open(p, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    config = load_config()
    results_dir = os.path.join(config["paths"]["gold_qa"], "results")
    out_dir     = os.path.join(config["paths"]["gold_qa"], "analysis")
    os.makedirs(out_dir, exist_ok=True)

    found = False
    for mode in ("bm25", "dense", "hybrid"):
        results_path = os.path.join(results_dir, f"{mode}.json")
        if not os.path.exists(results_path):
            continue
        found = True

        with open(results_path, "r", encoding="utf-8") as f:
            results = json.load(f)

        analysis = analyze(results)
        md       = to_markdown(analysis, mode)

        json_out = os.path.join(out_dir, f"{mode}_analysis.json")
        md_out   = os.path.join(out_dir, f"{mode}_analysis.md")
        with open(json_out, "w", encoding="utf-8") as f:
            json.dump(analysis, f, ensure_ascii=False, indent=2)
        with open(md_out, "w", encoding="utf-8") as f:
            f.write(md)

        print(f"\n=== {mode} ===")
        print(f"  total: {analysis['n_total']}, failures: {analysis['n_failures']}")
        print(f"  categories: {analysis['categories']}")
        print(f"  saved to {md_out}")

    if not found:
        print("No results files found. Run metrics.py first.")
        sys.exit(1)
