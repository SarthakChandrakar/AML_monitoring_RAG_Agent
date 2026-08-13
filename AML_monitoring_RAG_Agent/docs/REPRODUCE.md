# REPRODUCE.md — End-to-End Reproduction Guide

This document provides exact shell commands to reproduce all data pipelines, two-store vector indices, benchmark evaluation runs, and unit tests from a clean machine.

---

## 1. Environment & Setup

```bash
# 1. Clone repository and set up venv
git clone https://github.com/your-username/aml-monitoring-rag-agent.git
cd aml-monitoring-rag-agent

python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt
```

---

## 2. Step-by-Step Reproduction Workflow

| Step | Command | Expected Wall-Clock Runtime | Description |
| :--- | :--- | :--- | :--- |
| **1. Unit Tests** | `pytest tests/` | **~10 seconds** | Verifies risk engine purity, two-store retrieval, compliance layer, and metrics formulas. |
| **2. Build KB Index** | `python build_two_stores.py` | **~45 seconds** | Ingests FATF PDF and typologies into `kb_store` with L2-normalized FAISS `IndexFlatIP`. |
| **3. Seed Benchmark** | `python eval/dataset/seed_candidates.py` | **~2 seconds** | Generates 35 benchmark query candidates into `eval/dataset/candidates.jsonl`. |
| **4. Smoke Eval** | `python eval/faithfulness/runner.py` | **~15 seconds** | Executes faithfulness harness smoke run and outputs `results/run_<timestamp>.json`. |
| **5. Ablation Study** | `python eval/experiments/ablation_leakage.py` | **~10 seconds** | Evaluates model stability under FULL, EMPTY, SHUFFLED, CORRUPTED, and PARTIAL context. |
| **6. Threat Experiment**| `python eval/experiments/poisoned_index.py` | **~10 seconds** | Measures supply-chain risk and verifies production `kb_store` safety assertion. |
| **7. Launch UI** | `streamlit run ui/app.py` | **<2 seconds** | Starts dark-theme dashboard on `http://localhost:8501`. |

---

## 3. Docker Reproduction

```bash
docker-compose up --build
```
Open `http://localhost:8501` to view the running dashboard.
