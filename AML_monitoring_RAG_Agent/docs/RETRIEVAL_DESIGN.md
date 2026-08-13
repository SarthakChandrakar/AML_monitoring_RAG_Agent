# RETRIEVAL_DESIGN.md — Two-Store Architecture Specification

## Executive Rationale: Isolation of Citable Evidence vs. Factual Context

In retrieval-augmented AML intelligence systems, combining raw transaction records and regulatory policy documents into a single vector database is a fundamental architectural error.

### Why Single-Index Retrieval Fails:
1. **Structural Domination**: Transaction documents are near-identical templated strings (e.g., `Transaction Time: ... Sender Bank: ... Amount Paid: ...`). When embedded, thousands of transaction rows form tight clusters in vector space.
2. **Regulatory Exclusion**: Dense similarity queries return top-$k$ nearest neighbors consisting entirely of irrelevant transaction rows (e.g., another random transaction for $25,000), crowding out legitimate compliance evidence from FATF Recommendations and AML typology guides.
3. **Pseudo-Evidence Fallacy**: A random transaction record from a dataset is *not* legal evidence for a compliance assessment. Only regulatory recommendations, statutory thresholds, and documented typologies constitute citable evidence.

---

## Architectural Solution: Two-Store System

```
                         [User Query / Alert]
                                  │
                  ┌───────────────┴───────────────┐
                  ▼                               ▼
       ┌────────────────────┐          ┌────────────────────┐
       │   Regulatory KB    │          │ Transaction Store  │
       │   (`kb_store`)     │          │   (`txn_store`)    │
       ├────────────────────┤          ├────────────────────┤
       │ - FATF PDF         │          │ - IBM AML Dataset  │
       │ - AML Typologies   │          │ - DuckDB / SQL     │
       │ - Rule Definitions │          │ - Predicate Filter │
       ├────────────────────┤          ├────────────────────┤
       │ Vector (IndexIP) + │          │ Amount, Currency,  │
       │ BM25 Hybrid (RRF)  │          │ Counterparty, Time │
       └────────────────────┘          └────────────────────┘
                  │                               │
                  ▼                               ▼
           Citable Evidence               Factual Context
                  └───────────────┬───────────────┘
                                  ▼
                     [Grounded Analyst Narrative]
```

### 1. `kb_store` (Citable Regulatory Evidence)
- **Sources**: FATF Recommendations PDF, `aml_dataset.json` typologies, `knowledge_base/aml_rules.json`.
- **Chunking**: Structure-aware windowing (~512 tokens with 15% overlap) preserving `section_title`, `recommendation_number`, and `paragraph_id` metadata.
- **Citation Labeling**: Every chunk renders human-readable citation strings such as `"FATF Recommendation 10, ¶5"` or `"Typology: Trade-Based Laundering §2"`.
- **Vector Space**: Embeddings normalized ($||v|| = 1.0$) with FAISS `IndexFlatIP` (Cosine Similarity in $[0, 1]$).
- **Hybrid Search**: Reciprocal Rank Fusion (RRF) combining dense FAISS cosine search and sparse BM25 (`rank_bm25`).

### 2. `txn_store` (Structured Query Engine)
- **Engine**: DuckDB in-memory relational SQL engine over `dev_subset.csv` / `HI-Small_Trans.csv`.
- **Interface**: Structured SQL predicates over `Amount Paid`, `Payment Format`, `Payment Currency`, `Receiving Currency`, `Account`, and `Timestamp`.
- **No Vector Embeddings**: Transactions are structured facts, not unstructured text to be embedded.
