# PORTFOLIO.md — Resume Bullets & Professional Descriptions

This file contains checkable resume bullet points, portfolio project descriptions, and social media copy for showcasing this work.

---

## 1. Resume Bullet Points

- **Built an evaluation framework for retrieval-augmented AML compliance agents**, introducing an **Audit-Failure Rate** metric ($P(\text{correct} \land \text{groundedness} < \tau)$) to quantify answers that are factually correct yet unattributable to retrieved regulatory evidence.
- **Engineered a Two-Store Retrieval Architecture** separating citable regulatory guidelines (`kb_store` via FAISS `IndexFlatIP` + BM25 hybrid search) from structured transaction data (`txn_store` via DuckDB SQL), eliminating structural retrieval domination by near-duplicate transaction rows.
- **Constructed `AMLFaith` benchmark tooling** supporting 150 query candidates, claim-level NLI entailment scoring (`cross-encoder/nli-deberta-v3-base`), and 25+ unanswerable queries for measuring agent abstention accuracy.
- **Implemented a pure, deterministic AML risk engine** reading versioned `config/rules.yaml` parameters, verified via `pytest` and `hypothesis` determinism tests across 500x execution sweeps.
- **Developed a compliance realism suite** featuring OFAC SDN sanctions name fuzzy-matching (Jaro-Winkler), 5-part FinCEN SAR narrative drafting, an append-only hash-chained JSONL audit logger with cryptographic tamper verification, and alert lifecycle state machines.

---

## 2. Portfolio & LinkedIn Summary

> **Project: Explainable AML Monitoring RAG Platform & Faithfulness Benchmark**  
> 
> Anti-Money Laundering alerts require strict auditability. Standard LLMs suffer from hallucinations, while legacy rules generate high false positives. I developed a research RAG framework studying faithfulness and attribution in financial compliance.  
> 
> **Key Technical Highlights:**
> - **Two-Store Architecture**: Regulatory KB (`IndexFlatIP` + BM25 hybrid) separated from structured transaction queries (DuckDB SQL).
> - **Pure Risk Engine**: Isolated deterministic scoring based on versioned `config/rules.yaml` rules.
> - **Faithfulness Harness**: NLI cross-encoder claim entailment and Audit-Failure Rate evaluation with 95% bootstrap confidence intervals.
> - **Compliance Features**: Sanctions screening, FinCEN SAR drafting, append-only hash-chained audit logging, and alert state machines.
