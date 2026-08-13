# Explainable Anti-Money Laundering (AML) Monitoring Agent

This repository implements an AI-assisted AML transaction monitoring and review system. It combines a **deterministic, rule-based risk-scoring engine**, a **two-store retrieval system** for regulatory evidence (FATF guidelines + AML typologies) and structured transaction data, a **compliance layer** (sanctions screening, SAR narrative drafting, hash-chained audit logging, case lifecycle tracking), a **faithfulness/evaluation harness** for checking whether generated statements are actually grounded in retrieved evidence, and a **Streamlit dashboard** that ties these pieces together for an analyst.

According to the project's own documentation (`AGENTS.md`, `PAPER.md`), the intended contribution of this repository is primarily **research**: a benchmark and set of metrics for measuring *faithfulness* and *attribution* in retrieval-augmented AML agents, not a production compliance product. This README reflects that framing and documents only what is present in the code.

> **Note on project maturity**: this repository contains two generations of code — an active **two-store architecture** (`retrieval/`, `risk/`, `compliance/`, `eval/`, `ui/`) and an earlier **single-store prototype** (`src/`, `main.py`, `chat.py`, `evaluation.py`, and several root-level `test_*.py` scripts). Both are described below, clearly separated, because both are present and importable in the codebase today.

---

## 1. Project Overview

**Anti-Money Laundering (AML)** refers to the laws, regulations, and procedures financial institutions use to detect and prevent criminals from disguising illegally obtained funds as legitimate income. Banks and payment providers are required to monitor transactions, flag suspicious activity, and — when warranted — file a **Suspicious Activity Report (SAR)** with regulators.

**What this project does:**
- Takes a transaction record (amount, payment method, currencies, sender/receiver accounts) and scores it against a versioned set of compliance rules (e.g. large cash transactions, cryptocurrency settlement, known laundering-pattern labels).
- Retrieves supporting regulatory evidence — passages from the FATF Recommendations and AML typology notes — that are relevant to why a transaction was flagged.
- Drafts a structured investigation report / SAR narrative that cites the retrieved evidence, with any field it cannot determine from the data explicitly marked `[ANALYST INPUT REQUIRED]` rather than guessed.
- Provides tooling to check whether the individual sentences in a generated report are actually supported by the retrieved evidence ("faithfulness" checking), rather than trusting the output blindly.
- Logs every analysis event to an append-only, SHA-256 hash-chained audit log so that tampering can be detected.

**What problem it addresses:** Large language models can produce fluent, plausible-sounding compliance narratives, but a narrative that is fluent and even factually correct is not usable in a regulated setting if it can't be traced back to authoritative evidence — an analyst cannot file a SAR based on an unattributable AI claim. This project's stated research problem (see `PAPER.md`) is measuring and reducing that gap, using an **Audit-Failure Rate** metric defined as the probability that an answer is correct but its grounding score falls below a threshold.

**Who could use something like this:** compliance analysts and AML investigators as a decision-support/drafting aid, and researchers studying retrieval-augmented generation (RAG) faithfulness in regulated domains.

**Why explainability and evidence matter here:** every risk score in this system is produced by a deterministic, auditable rule engine (not a black-box model), and every regulatory claim in a generated report is meant to be traceable to a specific retrieved passage. This is what separates the design from a generic chatbot wrapped around a transaction dataset.

---

## 2. Repository Structure

```
Project_28/
├── retrieval/              # Active two-store retrieval layer
│   ├── kb_store.py           # Regulatory evidence store (FAISS IndexFlatIP + BM25 hybrid)
│   └── txn_store.py          # Structured transaction store (DuckDB SQL)
├── risk/                   # Active deterministic risk engine
│   ├── risk_engine.py        # Pure scoring function, reads config/rules.yaml
│   └── models.py             # Transaction / RiskAssessment / RuleSet dataclasses
├── compliance/              # Active compliance layer
│   ├── sanctions.py           # Fuzzy name screening against a bundled sample list
│   ├── sar.py                  # FinCEN-style 5-part SAR narrative generator
│   ├── audit_log.py            # SHA-256 hash-chained append-only audit log
│   ├── case.py                  # Alert lifecycle state machine
│   └── feedback.py              # Analyst disposition / precision tracking
├── eval/                    # Active faithfulness evaluation harness
│   ├── faithfulness/           # Claim extraction, NLI entailment judge, metrics + bootstrap CIs
│   ├── dataset/                 # Benchmark schema, seeding, and annotation tooling
│   └── experiments/              # Evidence-ablation and index-poisoning experiments
├── ui/                      # Active Streamlit dashboard
│   ├── app.py, backend.py, llm_client.py, helpers.py, styles.py
├── config/rules.yaml        # Versioned risk-scoring rules and tier thresholds
├── knowledge_base/aml_rules.json  # Additional red-flag rule text ingested into kb_store
├── Data/                    # Input data (see Data section below)
├── tests/                   # Active pytest suite (risk engine, retrieval, compliance, faithfulness)
├── docs/                    # Design docs: architecture, model card, threat model, reproduction guide
├── outputs/, results/       # Generated artifacts (indices, logs, evaluation run outputs)
│
├── src/                     # Earlier/legacy single-store prototype
│   ├── retriever.py, vector_store.py   # Single FAISS IndexFlatL2 store
│   ├── rag_agent.py, prompt_builder.py, groq_llm.py
│   ├── risk_engine.py         # Thin adapter forwarding to risk/risk_engine.py
│   └── explanation_generator.py, preprocessing.py, text_converter.py, document_loader.py
├── main.py, chat.py, evaluation.py, build_corpus.py, build_vector_db.py  # Legacy entry points
├── build_two_stores.py       # Active build script for kb_store
└── test.py, test_explanation_generator.py, test_groq_apikey.py,
    test_multiple_querries.py, test_retriever.py, test_risk_engine.py     # Ad-hoc manual scripts (not pytest suites)
```

---

## 3. Active System: How It Works

### 3.1 Two-store retrieval

The core design decision documented in `docs/RETRIEVAL_DESIGN.md` is to **not** put regulatory text and raw transaction rows in the same vector index, because templated transaction rows dominate nearest-neighbor search and crowd out actual regulatory evidence. Instead:

- **`kb_store`** (`retrieval/kb_store.py`) — citable regulatory evidence.
  - Source data: the FATF guidelines PDF (`Data/fatf_guidelines.pdf`), an AML typology JSON file (`Data/aml_dataset.json`), and a red-flag rules JSON (`knowledge_base/aml_rules.json`).
  - Built by `build_two_stores.py`, which windows the PDF into ~200-word chunks with overlap, embeds chunks with `sentence-transformers` (`all-MiniLM-L6-v2`, 384-dim), L2-normalizes the embeddings, and indexes them with FAISS `IndexFlatIP` (cosine similarity).
  - Also supports BM25 sparse search (`rank_bm25`) and a hybrid mode that fuses dense + sparse rankings with Reciprocal Rank Fusion (RRF).
  - Each result carries a human-readable citation string (e.g. `"FATF Recommendation 10"` or `"AML Typology: <section>"`).
- **`txn_store`** (`retrieval/txn_store.py`) — structured transaction facts, queried with SQL via an in-memory **DuckDB** connection over `Data/dev_subset.csv` (falling back to `Data/HI-Small_Trans.csv` if the subset isn't present). Transactions are treated as queryable facts, not embedded as text.

### 3.2 Deterministic risk engine

`risk/risk_engine.py` implements `score_transaction()`, a pure function of a `Transaction` record and a `RuleSet` loaded from `config/rules.yaml` — it does not read retrieved documents, network state, or randomness. Rules currently implemented (from `config/rules.yaml`, version `1.1.0`):

| Rule ID | Condition | Weight | Regulatory reference |
|---|---|---|---|
| RULE-001a | Amount > $10,000 | 25 | FATF Recommendation 10 |
| RULE-001b | Amount > $50,000 | 20 | FATF Recommendation 10 |
| RULE-001c | Amount > $100,000 | 20 | FATF Recommendation 10 |
| RULE-001d | Amount > $250,000 | 20 | FATF Recommendation 10 |
| RULE-002 | Payment format is Cash | 35 | FATF Recommendation 20 |
| RULE-003 | Payment or receiving currency is Bitcoin | 25 | FATF Recommendation 15 |
| RULE-004 | `is_laundering == 1` (dataset ground-truth label) | 85 | Internal baseline |

Contributions are summed and capped at 100. Tiering (from `config/rules.yaml`): score ≥ 60 → **HIGH**, ≥ 35 → **MEDIUM**, otherwise **LOW**, each with a corresponding recommended action string. The engine's determinism, monotonicity, tier boundaries, and additivity are covered by `tests/test_risk_engine_pure.py`.

### 3.3 Compliance layer

- **`compliance/sanctions.py`** — screens a counterparty name against a small, hardcoded, dated (`2026-08-01`) sample snapshot of five fictitious high-risk entities using `difflib.SequenceMatcher` string similarity. This is **not** a live OFAC/sanctions feed — `LIMITATIONS.md` states explicitly that there is no live sanctions integration.
- **`compliance/sar.py`** — generates a 5-part (Who/What/When/Where/Why) SAR-style narrative from a `Transaction` and `RiskAssessment`, filling any field it cannot derive with the literal text `[ANALYST INPUT REQUIRED]` rather than fabricating a value.
- **`compliance/audit_log.py`** — appends JSONL entries to `outputs/audit_log.jsonl`, where each entry's hash incorporates the previous entry's hash (a SHA-256 hash chain), and `verify_chain()` can detect tampering by recomputing the chain.
- **`compliance/case.py`** — a case/alert state machine enforcing valid transitions: `NEW → TRIAGED → ESCALATED → {SAR_FILED, CLOSED_FALSE_POSITIVE, CLOSED_NO_ACTION}`.
- **`compliance/feedback.py`** — records analyst TRUE_POSITIVE/FALSE_POSITIVE dispositions and computes simple alert precision from them.

### 3.4 Faithfulness / evaluation harness

`eval/faithfulness/` implements:
- `claim_extractor.py` — splits a narrative into sentence-level "atomic claims" and extracts any `[E1]`/`[FATF ...]`-style citation markers.
- `entailment.py` — an `EntailmentJudge` that attempts to load a cross-encoder NLI model (`cross-encoder/nli-deberta-v3-base`) to score claim/evidence entailment; if that model can't be loaded, it falls back to a token-overlap heuristic. Labels claims `SUPPORTED`, `CONTRADICTED`, or `UNVERIFIABLE`.
- `metrics.py` — retrieval metrics (Precision@k, Recall@k — using distinct formulas, MRR, nDCG@k), an **Audit-Failure Rate** metric (`P(correct ∧ groundedness < τ)`), and bootstrap confidence intervals (1,000 resamples by default).

`eval/dataset/` defines a benchmark schema and annotation workflow ("AMLFaith") intended to reach 150 human-annotated queries; `eval/dataset/candidates.jsonl` currently contains seeded candidate queries with `status: "UNVERIFIED"` and empty `gold_passage_ids`/`reference_answer` fields — i.e., **the benchmark queries exist but have not yet been human-annotated**, per the file's own contents.

`eval/experiments/` contains an evidence-ablation script (`ablation_leakage.py`, testing FULL/EMPTY/SHUFFLED/CORRUPTED/PARTIAL evidence conditions) and a knowledge-base poisoning experiment (`poisoned_index.py`).

### 3.5 Streamlit dashboard

`ui/app.py` (also launchable via the top-level `app.py`) provides six pages: **Home**, **Transaction Review** (select and analyze a transaction, see triggered rules and retrieved evidence), **Suspicious Activity Report** (view/download the generated SAR narrative), **Evidence Check** (run the faithfulness judge against a report's claims), **Audit Log** (view and verify the hash chain), and **About**. `ui/backend.py` adapts the retrieval/risk modules for Streamlit's caching; `ui/llm_client.py` optionally calls Groq, Gemini, or OpenAI (in that priority order, based on which API key environment variable is set) to generate a narrative — the UI is explicitly designed to keep working with an offline/rule-based report if no LLM key is configured.

---

## 4. Legacy / Earlier-Stage Code

The following files predate the two-store redesign and are still present and importable, but are **not** what the Streamlit UI or the active tests exercise:

- **`src/retriever.py` + `src/vector_store.py`** — a single FAISS `IndexFlatL2` index built by `build_vector_db.py` over `outputs/documents.json`, mixing transaction text and regulatory text in one index (the pattern the two-store design in section 3.1 was built to avoid).
- **`src/rag_agent.py`** — attempts `from src.gemini_llm import ask_gemini`; **`src/gemini_llm.py` does not exist anywhere in this repository**. The import is wrapped in a `try/except ImportError`, so `AMLRAGAgent` falls back to returning `"Gemini API not available."` rather than crashing, but the Gemini code path itself is not implemented in `src/`.
- **`src/groq_llm.py`** — a standalone Groq call helper, separate from the Groq integration used in `ui/llm_client.py`.
- **`main.py`** — a data-preparation script (loads the raw transaction CSV, builds a stratified dev subset, and saves a sample document + class-distribution plot).
- **`chat.py`** — a command-line loop that retrieves evidence for a typed question using the legacy single-store retriever and prints the resulting prompt (it does not call an LLM).
- **`evaluation.py`** — a 5-query retrieval/groundedness benchmark against the legacy single-store retriever; its most recent output is saved at `outputs/evaluation_results.json` (see Section 6).
- **Root-level scripts** `test.py`, `test_explanation_generator.py`, `test_groq_apikey.py`, `test_multiple_querries.py`, `test_retriever.py`, `test_risk_engine.py` — these are manual smoke-test scripts (`print`-based, no `assert` statements, not collected by `pytest`), distinct from the real pytest suite in `tests/`.

---

## 5. Data

- **`Data/HI-Small_Trans.csv`** — the full transaction dataset. **This is a synthetic dataset generated by IBM's AMLSim simulator** (per `LIMITATIONS.md`); it is not real banking data, and its `Is Laundering` ground-truth labels are defined by the simulator's own generation rules, not by human investigators.
- **`Data/dev_subset.csv`** — a stratified subset (all laundering-labeled rows + a sampled set of normal rows) used by `txn_store` and the dashboard.
- **`Data/research_sample.csv`** — a random 50,000-row sample, produced by `main.py`.
- **`Data/aml_dataset.json`** — AML typology reference text ingested into `kb_store`.
- **`Data/fatf_guidelines.pdf`** — the FATF Recommendations PDF, the primary regulatory source ingested into `kb_store`.
- **`Data/HI-Small_Patterns.txt`** — present in the data directory; role not independently verified from code beyond its presence.
- **`knowledge_base/aml_rules.json`** — supplementary red-flag rule descriptions, also ingested into `kb_store`.

The raw dataset content itself is not reproduced here; see the code above for how each file is consumed.

---

## 6. Evaluation Status — What Has Actually Been Measured

This is an important distinction the project's own docs (`AGENTS.md`, `PAPER.md`, current `README.md`) are careful about, and this document preserves that distinction rather than inventing results:

- **`outputs/evaluation_results.json`** contains real output from a run of the *legacy* `evaluation.py` script against 5 hardcoded benchmark queries and the single-store retriever: `precision@5 = 0.48`, `recall@5 = 0.48`, `MRR = 0.8`, `hit_rate = 0.8`, average retrieval latency ≈ 46.7 ms, plus two heuristic (not NLI-judged) `groundedness` (0.1521) and `faithfulness` (0.95) scores. These numbers come from a 5-query smoke test on the legacy pipeline, not the AMLFaith benchmark.
- **`results/ablation_leakage_results.csv`** contains real output from the evidence-ablation experiment (`eval/experiments/ablation_leakage.py`) across FULL/EMPTY/SHUFFLED/CORRUPTED/PARTIAL conditions for 3 queries, recording passage counts and prompt lengths per condition.
- **The AMLFaith benchmark itself (150 target queries, human-annotated gold passages) has not been completed.** `eval/dataset/candidates.jsonl` currently holds seed candidates marked `"status": "UNVERIFIED"` with empty gold-passage and reference-answer fields.
- **The headline metrics from the project's own `README.md`/`PAPER.md`** (Audit-Failure Rate, Claim Groundedness, Citation Precision/Recall, Abstention Accuracy at scale) are explicitly recorded as `TBD_RUN_REQUIRED` in those files — i.e., the code to compute them exists (`eval/faithfulness/`), but a full benchmark run producing those numbers has not been completed/committed to this repo. This README does not fabricate values for them.

---

## 7. Setup

```bash
# 1. Install dependencies
pip install -r Requirements.txt
```

**Note:** `Requirements.txt` lists `streamlit`, `faiss-cpu`, `sentence-transformers`, `pandas`, `numpy`, `pypdf`, `plotly`, `fpdf2`, `matplotlib`, `seaborn`, `pillow`, `python-dotenv`, `groq`, `google-generativeai`, and `openai`. Several packages actually imported by the active code — `duckdb` (`retrieval/txn_store.py`), `rank_bm25` (`retrieval/kb_store.py`), `PyYAML` (`risk/risk_engine.py`), `pytest`/`hypothesis` (test suite) — are **not listed** in `Requirements.txt` and would need to be installed separately for the active system and tests to run.

## 8. Usage

```bash
# Build the active regulatory evidence index (kb_store)
python build_two_stores.py

# Launch the Streamlit dashboard
streamlit run ui/app.py
# or
streamlit run app.py

# Run the active pytest suite
pytest tests/

# Run the faithfulness evaluation harness
python eval/faithfulness/runner.py

# Run the evidence-ablation experiment
python eval/experiments/ablation_leakage.py
```

Optional: set one of `GROQ_API_KEY`, `GEMINI_API_KEY`, or `OPENAI_API_KEY` as an environment variable (or in a `.env` file) to enable LLM-generated narratives in the dashboard. Without any key set, the dashboard uses its rule-based/offline report generation path (`ui/llm_client.py`, `compliance/sar.py`).

Legacy pipeline (single-store, kept for reference):
```bash
python main.py            # builds data/dev_subset.csv, research_sample.csv
python build_vector_db.py # builds the legacy single-index FAISS store
python chat.py            # command-line retrieval loop (no LLM call)
python evaluation.py      # legacy 5-query benchmark
```

## 9. Docker

```bash
docker-compose up --build
```
Builds from the provided `Dockerfile` (`python:3.10-slim`) and runs `streamlit run ui/app.py` on port 8501.

## 10. Testing

The active pytest suite (`tests/`) covers:
- `test_risk_engine_pure.py` — determinism (500 repeated runs), monotonicity, tier boundaries, additivity of the risk engine.
- `test_retrieval_two_stores.py` — `kb_store` dense/hybrid search return shape and score ranges; `txn_store` SQL predicate filtering.
- `test_compliance_realism.py` — sanctions screening match/no-match, SAR narrative field population, audit-log tamper detection, case state-machine transition validity.
- `test_faithfulness_harness.py` — claim extraction, the distinctness of the Precision@k vs Recall@k formulas, a hand-computed Audit-Failure Rate fixture, and bootstrap CI bounds.

Run with:
```bash
pytest tests/
```

## 11. Documentation

- [`docs/RETRIEVAL_DESIGN.md`](docs/RETRIEVAL_DESIGN.md) — rationale for the two-store architecture.
- [`docs/REPRODUCE.md`](docs/REPRODUCE.md) — step-by-step reproduction commands and expected runtimes.
- [`docs/MODEL_CARD.md`](docs/MODEL_CARD.md), [`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md), [`docs/TECHNICAL_REPORT.md`](docs/TECHNICAL_REPORT.md), [`docs/CLAIMS_AUDIT.md`](docs/CLAIMS_AUDIT.md) — additional design and risk documentation (not independently re-verified here beyond their presence).
- [`LIMITATIONS.md`](LIMITATIONS.md) — the project's own stated limitations (synthetic data, single embedding model, English-only, no live sanctions feed, small/incomplete annotation pool, no human user study).
- [`PAPER.md`](PAPER.md) — an academic-paper-style writeup of the research framing, with results sections explicitly marked `TBD_RUN_REQUIRED`.
- [`AGENTS.md`](AGENTS.md) — contributor/agent rules for this repository, including an explicit prohibition on inventing metric values or unbacked capability claims.

## 12. Known Gaps / Things That Could Not Be Fully Verified

- No `LICENSE` file was found in the repository root; licensing terms could not be verified.
- `Data/HI-Small_Patterns.txt`'s exact role could not be confirmed from the code inspected.
- The full AMLFaith benchmark results, and the headline faithfulness/audit-failure metrics referenced in `PAPER.md`, have not been generated in this repository as of this writing (see Section 6).
- `docs/MODEL_CARD.md`, `docs/THREAT_MODEL.md`, `docs/TECHNICAL_REPORT.md`, and `docs/CLAIMS_AUDIT.md` exist but their contents were not cross-checked line-by-line against the code for this README.
