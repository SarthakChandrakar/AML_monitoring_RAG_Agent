# MODEL_CARD.md — Compliance RAG Model Specification (SR 11-7)

## 1. Intended Use & Target Application
The **AML Monitoring RAG Agent** is designed as a first-line decision support system for financial crime compliance analysts. It performs dense vector similarity retrieval over regulatory recommendations (FATF guidelines, AML typologies) and applies deterministic compliance rule scoring to transactional data.

## 2. Out-of-Scope Uses
- **Autonomous Filing**: The model MUST NOT autonomously file Suspicious Activity Reports (SARs) or execute legal freezes without human compliance officer authorization.
- **Sole Source Determination**: The model output is an investigative draft and does not replace statutory audit trails.

## 3. Training & Knowledge Data Sources
1. **FATF Recommendations PDF**: International anti-money laundering guidelines published by the Financial Action Task Force.
2. **AML Typology Knowledge Base**: Curated JSON rules defining structuring, smurfing, and trade-based money laundering indicators.
3. **Synthetic IBM AML Dataset**: Transaction records generated via IBM AMLSim.

> **CRITICAL BOUNDARY NOTICE**: The IBM AML dataset consists of synthetic transaction logs. All money laundering labels (`Is Laundering = 1`) are generator-defined rules within the simulation. This bounds the external validity of empirical classification scores to synthetic network topologies.

## 4. Known Failure Modes
- **Single-Pass Bi-Encoder Retrieval**: Bi-encoder similarity search may occasionally rank passage chunks containing keyword matches over deeper contextual nuances.
- **Abstention Threshold Dependence**: If a regulatory query is not covered by ingested knowledge sources, the agent relies on explicit abstention prompts to state "insufficient evidence".

## 5. Validation Evidence & Reproducibility
- Evaluation benchmarks are computed by `eval/faithfulness/runner.py` and saved to `results/`.
- All metric outputs report sample size $n$, 95% bootstrap confidence intervals, and random seeds.
