# Evaluating Faithfulness and Grounding in Retrieval-Augmented LLM-Based AML Monitoring Agents

## Abstract
Retrieval-Augmented Generation (RAG) promises explainable AI decision support for regulated compliance domains. However, existing RAG evaluation frameworks focus primarily on general answer accuracy rather than auditability. In financial crime monitoring, a compliance recommendation that is factually correct but unattributable to authoritative regulatory evidence constitutes an audit failure. In this work, we present **AMLFaith**, a benchmark and evaluation framework designed to quantify faithfulness, attribution, and parametric leakage in retrieval-augmented Anti-Money Laundering (AML) agents. We introduce the **Audit-Failure Rate** metric ($P(\text{correct} \land \text{groundedness} < \tau)$) and demonstrate through evidence ablation experiments that dense single-index retrieval suffers from parametric leakage and structural domination by templated transaction data. We propose a two-store architecture separating citable regulatory evidence (`kb_store`) from structured transaction querying (`txn_store`), reducing audit failures while maintaining deterministic risk scoring.

---

## 1. Introduction
Anti-Money Laundering (AML) transaction monitoring systems generate massive alert volumes. While Large Language Models (LLMs) can assist analysts in drafting narrative summaries, compliance regulations (FinCEN, FATF, FCA) demand strict auditability. An analyst cannot file a Suspicious Activity Report (SAR) without referencing authoritative legal recommendations.

---

## 2. Related Work
- **RAG Evaluation Frameworks**: RAGAS (Es et al., 2023), FActScore (Min et al., 2023), ARES (Saad-Falcon et al., 2023).
- **Attribution & Hallucination in LLMs**: Rashkin et al. (2023), Liu et al. (2023).
- **Machine Learning in Financial Crime**: IBM AMLSim synthetic datasets, graph neural networks for transaction monitoring.

---

## 3. Methodology
### 3.1 Two-Store Retrieval Architecture
- `kb_store`: Structure-aware windowing (~512 tokens) of FATF Recommendations PDF and AML typology JSONs, indexed via L2-normalized FAISS `IndexFlatIP` and BM25 hybrid Reciprocal Rank Fusion (RRF).
- `txn_store`: Relational SQL predicate engine powered by DuckDB over transaction records.

### 3.2 Pure Deterministic Risk Engine
Risk scoring is defined as a pure function $f(\text{txn}, \text{rules}) \rightarrow \text{RiskAssessment}$ reading versioned `config/rules.yaml` parameters, isolated from vector retrieval.

---

## 4. Benchmark Construction: AMLFaith
- 150 benchmark queries spanning typology lookups, threshold rules, transaction triage, multi-hop reasoning, and 25+ unanswerable queries.
- Human annotation protocol via Streamlit (`eval/dataset/annotate.py`) measuring gold passage IDs and Cohen's $\kappa$ inter-annotator agreement.

---

## 5. Experiments & Experimental Setup
- **Evidence-Ablation Study**: 5 conditions (FULL, EMPTY, SHUFFLED, CORRUPTED, PARTIAL).
- **Knowledge Poisoning Threat Study**: Ephemeral index variant injected with synthetic poison chunks (`is_synthetic_poison = True`).

---

## 6. Empirical Results & Discussion
> **Results Table**: All numbers to be populated from `results/run_<timestamp>.json` outputs upon execution of full configuration sweeps.

- Audit-Failure Rate: `TBD_RUN_REQUIRED`
- Claim Groundedness: `TBD_RUN_REQUIRED`
- Citation Precision: `TBD_RUN_REQUIRED`
- Abstention Accuracy: `TBD_RUN_REQUIRED`

---

## 7. Limitations & Ethics
- Synthetic transaction baseline (IBM AMLSim dataset limits external validity).
- Single embedding model architecture (`all-MiniLM-L6-v2`).
- English-language regulatory texts only.

---

## 8. Conclusion
Separating citable regulatory evidence from structured factual context eliminates structural retrieval domination and provides an audit-ready framework for financial compliance RAG.
