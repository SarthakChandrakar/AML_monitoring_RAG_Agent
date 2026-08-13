# CLAIMS_AUDIT.md — Adversarial Audit of Quantitative & Technical Claims

This document provides a strict, adversarial audit of all factual, quantitative, and architectural claims made in prior repository documentation (`README.md` and `docs/TECHNICAL_REPORT.md`) against the actual Python code in `src/`, `ui/`, `evaluation.py`, and outputs.

---

## 1. Summary Audit Table

| Claim | Location in Report | Code / Test Substantiation | Audit Verdict | Audit Explanation & Defect Detail |
| :--- | :--- | :--- | :---: | :--- |
| **Precision@5 = 0.4800** | Section 14 (TECHNICAL_REPORT.md) | `evaluation.py` L75 (`relevant_docs / top_k`) | `UNSUBSTANTIATED` | Computed from keyword-overlap (`any(kw in text)`), not a ground-truth relevant passage set. |
| **Recall@5 = 0.4800** | Section 14 (TECHNICAL_REPORT.md) | `evaluation.py` L76 (`relevant_docs / len(expected_kw)`) | `CONTRADICTED_BY_CODE` | Identical to Precision@5 by formula coincidence ($5/5 \times \text{matches}$). True recall is undefined without a ground-truth set of total relevant documents in the corpus. |
| **MRR = 0.8000** | Section 14 (TECHNICAL_REPORT.md) | `evaluation.py` L77 (`1.0 / first_hit_rank`) | `PARTIAL` | Computed over $n=5$ queries only ($4/5$ hits at rank 1, $1/5$ missed). Sample size $n=5$ is an anecdote, not a statistical evaluation. |
| **Hit Rate = 0.8000** | Section 14 (TECHNICAL_REPORT.md) | `evaluation.py` L78 (`1 if relevant_docs > 0 else 0`) | `PARTIAL` | Computed over $n=5$ test queries. Round number reflects small sample size. |
| **Faithfulness = 0.9500** | Section 14 (TECHNICAL_REPORT.md) | `evaluation.py` L98 (`faithfulness = 0.95 if (score > 0 and reasons) else 0.90`) | `CONTRADICTED_BY_CODE` | **Hardcoded constant** in python code (`0.95`). Not computed from entailment or claim evaluation. In offline mode, narrative is generated from rules, creating circular self-agreement. |
| **Groundedness = 0.1521** | Section 14 (TECHNICAL_REPORT.md) | `evaluation.py` L94 (`grounded_lines / max(1, len(report_lines))`) | `PARTIAL` | Measures text line string matching, disagreeing by 6x with the hardcoded 0.95 Faithfulness metric without explanation. |
| **Average Latency = 46.68 ms** | Section 14 (TECHNICAL_REPORT.md) | `evaluation.py` L64 (`time.perf_counter()`) | `VERIFIED` | Measured in `evaluation.py` over 5 queries on FAISS `IndexFlatL2` search. |
| **Deterministic Risk Engine** | Section 10 (TECHNICAL_REPORT.md) | `src/risk_engine.py` L82 (`score += 3` per retrieved doc keyword) | `CONTRADICTED_BY_CODE` | **Not deterministic**: Risk score changes if vector retrieval $k$ changes, because `src/risk_engine.py` iterates over `retrieved_docs` and mutates score. |
| **Zero Hallucinated Compliance Decisions** | Section 1.2 (TECHNICAL_REPORT.md) | `ui/backend.py` L141 (`src/explanation_generator.py`) | `CONTRADICTED_BY_CODE` | In offline mode, text is produced from python string templates. There is no free-form LLM generation, making zero hallucination trivial (like a calculator). |
| **AHT reduced from 45m to <2m** | Section 1.4 (TECHNICAL_REPORT.md) | None | `UNSUBSTANTIATED` | No user study or timing logs exist in code. Speculative marketing hypothesis. |
| **Status: Production-Ready** | Header & Sec 18 (TECHNICAL_REPORT.md) | None | `UNSUBSTANTIATED` | Code lacks authentication, RBAC, immutable audit logging, PEP/sanctions feeds, or formal unit tests. |

---

## 2. Detailed Technical Defects Identified

### Defect A: Circular & Hardcoded Faithfulness Metric
- In `evaluation.py`, lines 96-98:
  ```python
  faithfulness = 0.95 if (score > 0 and reasons) else 0.90
  ```
- **Finding**: The reported 0.9500 Faithfulness score was literally a hardcoded number returned when a rule triggered. It did not perform claim decomposition, NLI entailment, or model-based evaluation.

### Defect B: Contamination of Risk Engine by Retrieval
- In `src/risk_engine.py`, lines 76-84:
  ```python
  for doc in retrieved_docs:
      text = doc["text"].lower()
      for word in suspicious_keywords:
          if word in text:
              score += 3
  ```
- **Finding**: The transaction risk score depends directly on which documents FAISS returns. Changing top-$k$ from 5 to 10 changes the score for the *exact same transaction*. This breaks the invariant that risk scoring is a pure function of transaction attributes.

### Defect C: Retrieval Store Collision (Single Index Error)
- **Finding**: `outputs/combined_corpus.json` embeds 20,000 templated transaction rows alongside FATF regulatory PDF pages into a single vector space (`outputs/faiss.index`). Near-duplicate transaction records crowd out FATF regulatory passages during top-$k$ retrieval.

---

## 3. Remediation Mandate

1. All quantitative metrics in docs must be replaced with `TBD_RUN_REQUIRED` until computed by the new `eval/` harness.
2. `risk/risk_engine.py` must be refactored as a pure function of transaction data.
3. Retrieval must be split into `kb_store` (regulatory FATF/typologies) and `txn_store` (DuckDB structured SQL).
4. Build `AMLFaith` gold dataset and NLI cross-encoder entailment harness.
