# AMLFaith Benchmark Annotation Protocol

This directory contains the tools and schema for constructing **AMLFaith**, a 150-query annotated benchmark for evaluating faithfulness, grounding, and abstention in AML compliance RAG systems.

---

## 1. Schema Overview (`eval/dataset/schema.py`)

Each benchmark item adheres to the Pydantic `QueryItem` schema:
- `query_id`: Unique identifier (e.g., `AMLFAITH-001`).
- `query_text`: Natural language question.
- `query_type`: `typology_lookup`, `threshold_rule`, `transaction_triage`, `multi_hop`, or `unanswerable`.
- `difficulty`: `easy`, `medium`, or `hard`.
- `gold_passage_ids`: Array of ground-truth relevant chunk IDs in `kb_store`. **Must be populated by human annotators**.
- `reference_answer`: Human-written gold reference answer.
- `answerable`: `true` if answerable from `kb_store`; `false` if unanswerable.
- `expected_abstention`: `true` if agent should refuse to answer due to missing evidence.

---

## 2. Annotation Protocol Instructions

1. **Candidate Seeding**: Run `python eval/dataset/seed_candidates.py` to generate candidate queries into `eval/dataset/candidates.jsonl`.
2. **Launch Annotation UI**: Run `streamlit run eval/dataset/annotate.py`.
3. **Passage Selection**:
   - For answerable queries: Search `kb_store` candidates and check all chunks containing evidence required to answer the question.
   - For unanswerable queries: Leave `gold_passage_ids` empty (`[]`), set `answerable=False`, and set `expected_abstention=True`.
4. **Reference Answer**: Write a concise, 2-3 sentence reference answer based *only* on the selected gold passages.
5. **Validation**: Run `python eval/dataset/validate.py` to verify schema compliance and passage ID existence.

---

## 3. Human Inter-Annotator Agreement (Cohen's Kappa)

To measure annotation reliability, two annotators annotate candidates separately into `pass1.jsonl` and `pass2.jsonl`. Run `validate.py` to compute Cohen's $\kappa$ over gold passage judgments.
