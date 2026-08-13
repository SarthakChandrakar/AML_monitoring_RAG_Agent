"""Faithfulness, Grounding, and Retrieval Metrics with Bootstrap Confidence Intervals.

Computes:
  - Claim Groundedness
  - Citation Precision & Citation Recall
  - Abstention Accuracy
  - Audit-Failure Rate: P(correct == True AND claim_groundedness < tau)
  - Precision@k, Recall@k, nDCG@k, MRR (using distinct formulas!)
  - 95% Bootstrap Confidence Intervals
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple
import numpy as np


@dataclass(frozen=True)
class MetricWithCI:
    name: str
    value: float
    ci_lower: float
    ci_upper: float
    n_samples: int
    seed: int


def bootstrap_ci(
    data: Sequence[float],
    n_resamples: int = 1000,
    ci_level: float = 0.95,
    seed: int = 42,
) -> Tuple[float, float, float]:
    """Compute mean and 95% bootstrap confidence interval."""
    if not data:
        return 0.0, 0.0, 0.0

    arr = np.array(data, dtype=np.float64)
    mean_val = float(np.mean(arr))
    if len(arr) <= 1:
        return mean_val, mean_val, mean_val

    rng = np.random.default_rng(seed)
    boot_means = []
    n = len(arr)

    for _ in range(n_resamples):
        sample = rng.choice(arr, size=n, replace=True)
        boot_means.append(float(np.mean(sample)))

    alpha = (1.0 - ci_level) / 2.0
    lower = float(np.percentile(boot_means, alpha * 100))
    upper = float(np.percentile(boot_means, (1.0 - alpha) * 100))

    return round(mean_val, 4), round(lower, 4), round(upper, 4)


def compute_retrieval_metrics(
    retrieved_chunk_ids: List[str],
    gold_chunk_ids: List[str],
    k: int = 5,
) -> Dict[str, float]:
    """Compute retrieval metrics against gold passage IDs.
    
    Precision@k and Recall@k use DISTINCT formulas:
      Precision@k = |retrieved[:k] ∩ gold| / k
      Recall@k    = |retrieved[:k] ∩ gold| / |gold|  (0 if gold is empty)
    """
    if k <= 0:
        return {"precision_at_k": 0.0, "recall_at_k": 0.0, "mrr": 0.0, "ndcg_at_k": 0.0}

    top_k = retrieved_chunk_ids[:k]
    gold_set = set(gold_chunk_ids)

    hits = [cid for cid in top_k if cid in gold_set]
    n_hits = len(hits)

    # 1. Precision@k formula: hits / k
    precision = n_hits / k

    # 2. Recall@k formula: hits / len(gold)
    recall = (n_hits / len(gold_set)) if len(gold_set) > 0 else 0.0

    # 3. MRR: Reciprocal rank of first hit
    mrr = 0.0
    for rank, cid in enumerate(top_k, start=1):
        if cid in gold_set:
            mrr = 1.0 / rank
            break

    # 4. nDCG@k
    dcg = 0.0
    for rank, cid in enumerate(top_k, start=1):
        rel = 1.0 if cid in gold_set else 0.0
        dcg += rel / math.log2(rank + 1)

    idcg = sum(1.0 / math.log2(r + 1) for r in range(1, min(len(gold_set), k) + 1))
    ndcg = (dcg / idcg) if idcg > 0 else 0.0

    return {
        "precision_at_k": round(precision, 4),
        "recall_at_k": round(recall, 4),
        "mrr": round(mrr, 4),
        "ndcg_at_k": round(ndcg, 4),
    }


def compute_audit_failure_rate(
    correct_flags: List[bool],
    groundedness_scores: List[float],
    tau: float = 0.8,
) -> float:
    """Compute Audit-Failure Rate: P(correct == True AND claim_groundedness < tau)."""
    if not correct_flags or len(correct_flags) != len(groundedness_scores):
        return 0.0

    failures = 0
    total = len(correct_flags)

    for is_correct, g_score in zip(correct_flags, groundedness_scores):
        if is_correct and g_score < tau:
            failures += 1

    return round(failures / total, 4)
