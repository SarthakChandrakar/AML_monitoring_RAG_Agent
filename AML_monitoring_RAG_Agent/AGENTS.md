# AGENTS.md — AML RAG Faithfulness Study

## Project intent
This repository is a RESEARCH ARTIFACT studying faithfulness and grounding in retrieval-augmented AML monitoring agents. The dashboard is apparatus, not the contribution. The contribution is the benchmark, the metrics, and the findings.

## Absolute rules
1. NEVER write, guess, hardcode, or "example" any evaluation metric value. Metrics exist only as code that computes them from a real run. If you need a number for a doc, write `TBD_RUN_REQUIRED` and stop.
2. NEVER claim a capability in docs that is not covered by a passing test.
3. NEVER add self-assessment scores, readiness ratings, or marketing adjectives ("production-ready", "enterprise-grade", "publication-quality") to any file.
4. The risk engine is a PURE FUNCTION of a transaction record. It must not read retrieved documents, global state, wall-clock time, or randomness.
5. Every metric reported must carry: n, a 95% bootstrap CI, and the seed used.
6. If evidence is insufficient to implement correctly, open a question in the plan Artifact rather than inventing an approach.

## Architecture invariants
- Two retrieval stores: `kb_store` (regulatory, citable) and `txn_store` (structured, queryable). They must NOT share an index.
- Embeddings are L2-normalized; FAISS uses IndexFlatIP. Any L2 variant exists only behind an explicit ablation flag.
- All UI-facing similarity values are cosine in [0,1], higher = more similar. Raw distances must never be surfaced with the word "similarity".
- Thresholds and rule weights live in `config/rules.yaml`, never in code.

## Code standards
- Python 3.10+, type hints on all public functions, docstrings with Args/Returns.
- pytest for all new logic; property-based tests (hypothesis) for the risk engine.
- Determinism: `set_seeds(seed)` called at every entry point; seed logged to output.
- No new dependency without justification in the plan Artifact.

## Directory ownership (avoid parallel-agent collisions)
- `retrieval/` → retrieval agents only
- `risk/` → risk-engine agent only
- `eval/` → evaluation agents only
- `ui/` → UI agent only
- `compliance/` → compliance layer agent only
- `docs/`, `README.md` → docs agent only

Agents must not edit files outside their assigned directory. Cross-cutting changes require a shared-interface proposal in the plan Artifact first.

## Definition of done
A task is done when: tests pass, `make lint` is clean, the walkthrough Artifact shows the feature running on real data, and no claim in the diff is unbacked.
