"""Faithfulness Measurement Harness Package."""

from eval.faithfulness.claim_extractor import extract_claims, AtomicClaim
from eval.faithfulness.entailment import EntailmentJudge, ClaimEntailmentResult
from eval.faithfulness.metrics import bootstrap_ci, compute_retrieval_metrics, compute_audit_failure_rate
from eval.faithfulness.runner import run_evaluation

__all__ = [
    "extract_claims",
    "AtomicClaim",
    "EntailmentJudge",
    "ClaimEntailmentResult",
    "bootstrap_ci",
    "compute_retrieval_metrics",
    "compute_audit_failure_rate",
    "run_evaluation",
]
