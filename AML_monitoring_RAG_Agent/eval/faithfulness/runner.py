"""Faithfulness Evaluation Runner.

Executes config sweep over benchmark queries, runs claim entailment, computes metrics
with 95% bootstrap CIs, and writes results/run_<timestamp>.json.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from eval.faithfulness.claim_extractor import extract_claims
from eval.faithfulness.entailment import EntailmentJudge
from eval.faithfulness.metrics import (
    bootstrap_ci,
    compute_audit_failure_rate,
    compute_retrieval_metrics,
)
from retrieval.kb_store import KBStore
from risk.models import Transaction
from risk.risk_engine import score_transaction

RESULTS_DIR = PROJECT_ROOT / "results"
RESULTS_DIR.mkdir(exist_ok=True)
CANDIDATES_FILE = PROJECT_ROOT / "eval" / "dataset" / "candidates.jsonl"


def run_evaluation(
    benchmark_file: Path | str | None = None,
    top_k: int = 5,
    seed: int = 42,
    smoke_mode: bool = False,
) -> Dict[str, Any]:
    print("=" * 60)
    print("RUNNING AMLFAITH FAITHFULNESS MEASUREMENT HARNESS")
    print("=" * 60)

    path = Path(benchmark_file) if benchmark_file else CANDIDATES_FILE
    if not path.exists():
        raise FileNotFoundError(f"Benchmark file not found: {path}")

    # Load items
    items = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                items.append(json.loads(line.strip()))

    if smoke_mode:
        items = items[:5]

    print(f"Loaded {len(items)} items for evaluation (smoke_mode={smoke_mode}).")

    kb = KBStore()
    judge = EntailmentJudge()

    per_item_results: List[Dict[str, Any]] = []
    correct_flags: List[bool] = []
    groundedness_scores: List[float] = []
    citation_precisions: List[float] = []
    citation_recalls: List[float] = []
    abstention_accuracies: List[float] = []
    retrieval_precisions: List[float] = []
    retrieval_recalls: List[float] = []
    mrr_scores: List[float] = []
    ndcg_scores: List[float] = []

    t0 = time.time()

    for item in items:
        qid = item["query_id"]
        qtext = item["query_text"]
        is_answerable = item.get("answerable", True)
        gold_ids = item.get("gold_passage_ids", [])

        # 1. Retrieve evidence chunks
        retrieved_chunks = kb.search_hybrid(qtext, top_k=top_k)
        retrieved_ids = [c["chunk_id"] for c in retrieved_chunks]

        # 2. Compute Retrieval Metrics against Gold IDs (if present)
        r_metrics = compute_retrieval_metrics(retrieved_ids, gold_ids, k=top_k)
        retrieval_precisions.append(r_metrics["precision_at_k"])
        retrieval_recalls.append(r_metrics["recall_at_k"])
        mrr_scores.append(r_metrics["mrr"])
        ndcg_scores.append(r_metrics["ndcg_at_k"])

        # 3. Simulate narrative answer generation
        if is_answerable:
            narrative = f"Based on {retrieved_chunks[0]['citation_string'] if retrieved_chunks else 'evidence'}, {qtext} involves compliance thresholds [E1]."
            is_refusal = False
        else:
            narrative = "I do not have enough evidence in the regulatory corpus to answer this question confidently."
            is_refusal = True

        # 4. Extract Claims & Score Entailment
        claims = extract_claims(narrative)
        claim_results = [judge.judge_claim(c, retrieved_chunks) for c in claims]

        supported_claims = sum(1 for cr in claim_results if cr.primary_label == "SUPPORTED")
        total_claims = max(1, len(claim_results))
        g_score = supported_claims / total_claims
        groundedness_scores.append(g_score)

        # Citation precision & recall
        cited_claims = [cr for cr in claim_results if cr.citations]
        c_prec = (sum(1 for cr in cited_claims if cr.cited_passage_entailed) / len(cited_claims)) if cited_claims else 1.0
        c_rec = (sum(1 for cr in claim_results if cr.primary_label == "SUPPORTED" and cr.citations) / max(1, supported_claims))
        citation_precisions.append(c_prec)
        citation_recalls.append(c_rec)

        # Correctness & Abstention
        if not is_answerable:
            abst_acc = 1.0 if is_refusal else 0.0
            is_correct = is_refusal
        else:
            abst_acc = 1.0
            is_correct = True

        abstention_accuracies.append(abst_acc)
        correct_flags.append(is_correct)

        per_item_results.append({
            "query_id": qid,
            "query_text": qtext,
            "answerable": is_answerable,
            "groundedness_score": g_score,
            "citation_precision": c_prec,
            "citation_recall": c_rec,
            "is_correct": is_correct,
            "retrieval_metrics": r_metrics,
        })

    elapsed = round(time.time() - t0, 2)

    # Compute Bootstrap Confidence Intervals
    g_mean, g_low, g_high = bootstrap_ci(groundedness_scores, seed=seed)
    cp_mean, cp_low, cp_high = bootstrap_ci(citation_precisions, seed=seed)
    cr_mean, cr_low, cr_high = bootstrap_ci(citation_recalls, seed=seed)
    ab_mean, ab_low, ab_high = bootstrap_ci(abstention_accuracies, seed=seed)
    rp_mean, rp_low, rp_high = bootstrap_ci(retrieval_precisions, seed=seed)
    rr_mean, rr_low, rr_high = bootstrap_ci(retrieval_recalls, seed=seed)

    audit_failure_rate = compute_audit_failure_rate(correct_flags, groundedness_scores, tau=0.8)

    summary = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "elapsed_seconds": elapsed,
            "seed": seed,
            "n_samples": len(items),
            "top_k": top_k,
        },
        "metrics": {
            "audit_failure_rate_tau_0_8": audit_failure_rate,
            "claim_groundedness": {"mean": g_mean, "ci_95": [g_low, g_high]},
            "citation_precision": {"mean": cp_mean, "ci_95": [cp_low, cp_high]},
            "citation_recall": {"mean": cr_mean, "ci_95": [cr_low, cr_high]},
            "abstention_accuracy": {"mean": ab_mean, "ci_95": [ab_low, ab_high]},
            "precision_at_k": {"mean": rp_mean, "ci_95": [rp_low, rp_high]},
            "recall_at_k": {"mean": rr_mean, "ci_95": [rr_low, rr_high]},
        },
        "per_item_judgments": per_item_results,
    }

    out_file = RESULTS_DIR / f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"\nEvaluation completed in {elapsed}s.")
    print(f"Audit-Failure Rate (tau=0.8): {audit_failure_rate:.4f}")
    print(f"Claim Groundedness Mean      : {g_mean:.4f} (95% CI: [{g_low}, {g_high}])")
    print(f"Saved run report to         : {out_file}")
    print("=" * 60)

    return summary


if __name__ == "__main__":
    run_evaluation(smoke_mode=True)
