"""Answer extraction — runs at QA time on the retrieved passages.

Wraps a pre-trained extractive QA model (RoBERTa fine-tuned on SQuAD 2.0) and
adds two domain-specific bits on top:

  1. Multi-passage scoring — we run the model on every retrieved passage,
     then pick the highest-confidence answer. This is the standard
     reader-over-retriever pattern; it lets us recover when retrieval got
     the right city but the wrong best passage.

  2. Entity-type validation — if the query processor said the question
     expects a DATE (e.g. 'when'), we run spaCy NER on the answer span and
     downweight spans whose type doesn't match. Cheap post-filter that
     catches obvious extraction failures the QA model is happy to make.

SQuAD 2.0 (vs 1.1) lets the model emit an empty answer when nothing in the
passage answers the question — important here because most retrieved
passages won't actually contain the answer.

Returns a JSON-serializable answer dict so the same payload feeds Streamlit,
the eval harness, and the future Unreal/UDP server.
"""

import yaml
import torch
from transformers import AutoModelForQuestionAnswering, AutoTokenizer


QA_MODEL_NAME = "deepset/roberta-base-squad2"
MAX_ANSWER_LEN = 30        # tokens — SQuAD-typical cap, prevents runaway spans
TOPN_START_END = 20        # candidate start/end positions to consider per passage

# How many of the retriever's top-k to actually run through the reader.
# More = higher recall, slower. 3 is the standard ODQA default.
DEFAULT_READ_K = 3

# Multiplicative penalty applied when answer span doesn't carry an
# expected entity type. Penalty (not zero) so a strong wrong-type answer
# can still win over a weak right-type one.
TYPE_MISMATCH_PENALTY = 0.5


def load_config(config_path="configs/config.yaml"):
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


class AnswerExtractor:
    """Holds the QA pipeline (and lazily the spaCy model for type validation).
    Re-use one instance across many queries — model load is the expensive bit."""

    def __init__(self, model_name=QA_MODEL_NAME):
        print(f"Loading QA model {model_name}...")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForQuestionAnswering.from_pretrained(model_name)
        self.model.eval()
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model.to(self.device)
        self._nlp = None  # lazy — only loaded if validate_type is used

    def _ensure_nlp(self):
        if self._nlp is None:
            import spacy
            self._nlp = spacy.load("en_core_web_lg")

    # ── Type validation ────────────────────────────────────────────────
    def _span_matches_type(self, span_text, expected_types):
        """True if any NER entity in the span carries one of the expected
        types. An empty expected_types list = no constraint = always true."""
        if not expected_types:
            return True
        self._ensure_nlp()
        doc = self._nlp(span_text)
        return any(ent.label_ in expected_types for ent in doc.ents)

    # ── Single-passage extraction ─────────────────────────────────────
    def _extract_one(self, question, passage_text):
        """Run the QA model on one passage and pick the best (start, end) span.

        SQuAD 2.0 logic: the [CLS] token at index 0 represents 'no answer'.
        We compute scores for every (start, end) pair where start <= end and
        end - start < MAX_ANSWER_LEN, then compare against the [CLS]-[CLS]
        score. If [CLS]-[CLS] wins, we emit empty answer (model says 'no
        answer here') — that's what we want for irrelevant passages.
        """
        inputs = self.tokenizer(
            question, passage_text,
            return_tensors="pt", truncation="only_second",
            max_length=384, return_offsets_mapping=True,
        )
        offsets = inputs.pop("offset_mapping")[0].tolist()
        # Mask everything that isn't part of the passage (sequence-id 1).
        seq_ids = inputs.sequence_ids(0)
        passage_mask = torch.tensor([s == 1 for s in seq_ids], dtype=torch.bool)

        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        with torch.no_grad():
            outputs = self.model(**inputs)

        start_logits = outputs.start_logits[0].cpu()
        end_logits   = outputs.end_logits[0].cpu()

        # No-answer score (CLS-CLS).
        cls_score = (start_logits[0] + end_logits[0]).item()

        # Mask out non-passage positions (set to -inf so they never win).
        start_logits = start_logits.masked_fill(~passage_mask, float("-inf"))
        end_logits   = end_logits.masked_fill(~passage_mask, float("-inf"))

        # Top-N candidate start/end indices.
        top_starts = torch.topk(start_logits, min(TOPN_START_END, start_logits.numel())).indices.tolist()
        top_ends   = torch.topk(end_logits,   min(TOPN_START_END, end_logits.numel())).indices.tolist()

        best_score = float("-inf")
        best_start = best_end = 0
        for s in top_starts:
            for e in top_ends:
                if e < s or (e - s + 1) > MAX_ANSWER_LEN:
                    continue
                score = (start_logits[s] + end_logits[e]).item()
                if score > best_score:
                    best_score, best_start, best_end = score, s, e

        # No-answer wins: emit empty.
        if cls_score >= best_score or best_score == float("-inf"):
            return {"answer": "", "confidence": 0.0, "start": 0, "end": 0}

        # Map token indices back to character offsets in the original passage.
        char_start = offsets[best_start][0]
        char_end   = offsets[best_end][1]
        answer_text = passage_text[char_start:char_end].strip()

        # Confidence: softmax over (best_score - cls_score) — bounded [0,1].
        # Higher = model more confident than its 'no answer' option.
        confidence = float(torch.sigmoid(torch.tensor(best_score - cls_score)))

        return {
            "answer":     answer_text,
            "confidence": confidence,
            "start":      char_start,
            "end":        char_end,
        }

    # ── Public API ─────────────────────────────────────────────────────
    def extract(self, question, passages, expected_types=None, read_k=DEFAULT_READ_K):
        """Run extraction over the top-`read_k` passages, apply optional type
        validation penalty, return the best answer + every candidate considered.

        `passages` is the list returned by Retriever.retrieve(); each item has
        keys: rank, score, passage_id, city, source, text.
        """
        candidates = []
        for p in passages[:read_k]:
            out = self._extract_one(question, p["text"])

            # Apply type penalty (multiplicative on confidence).
            type_match = True
            if expected_types and out["answer"]:
                type_match = self._span_matches_type(out["answer"], expected_types)
            if not type_match:
                out["confidence"] *= TYPE_MISMATCH_PENALTY

            candidates.append({
                "answer":             out["answer"],
                "confidence":         out["confidence"],
                "raw_confidence":     out["confidence"] / (TYPE_MISMATCH_PENALTY if not type_match else 1.0),
                "type_match":         type_match,
                "passage_id":         p["passage_id"],
                "passage_city":       p["city"],
                "passage_source":     p["source"],
                "passage_text":       p["text"],
                "passage_rank":       p["rank"],
                "passage_score":      p["score"],
            })

        # Pick best non-empty answer; fall back to highest-confidence overall.
        non_empty = [c for c in candidates if c["answer"]]
        best = max(non_empty, key=lambda c: c["confidence"]) if non_empty \
               else max(candidates, key=lambda c: c["confidence"])

        return {
            "answer":          best["answer"],
            "confidence":      best["confidence"],
            "type_match":      best["type_match"],
            "source_passage":  {
                "passage_id":  best["passage_id"],
                "city":        best["passage_city"],
                "source":      best["passage_source"],
                "text":        best["passage_text"],
            },
            "all_candidates":  candidates,
        }


if __name__ == "__main__":
    # Smoke test — uses the retriever to fetch passages, then extracts.
    # Requires BM25 index built. Tests two questions covering different
    # question types so type-validation is exercised.
    import json
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from src.retrieval.retriever import Retriever
    from src.retrieval.query_processor import process_query, load_spacy, _build_alias_lookup

    config = load_config()
    cities = config["cities"]
    nlp = load_spacy()
    alias_lookup = _build_alias_lookup(cities)

    retriever = Retriever(config)
    extractor = AnswerExtractor()

    questions = [
        "When was Cairo founded?",
        "How many people live in Tokyo?",
    ]

    for q in questions:
        query = process_query(q, cities, nlp, alias_lookup)
        passages = retriever.retrieve(
            q, city=query["detected_city"], mode="bm25", top_k=5, rerank=False
        )
        answer = extractor.extract(q, passages, expected_types=query["expected_entity_types"])

        print(f"\nQ: {q}")
        print(f"  city detected: {query['detected_city']}  type: {query['question_type']}")
        print(f"  answer: {answer['answer']!r}  (conf {answer['confidence']:.3f}, type_match={answer['type_match']})")
        print(f"  source: {answer['source_passage']['passage_id']}")
