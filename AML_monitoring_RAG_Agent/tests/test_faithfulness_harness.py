"""Unit tests for Faithfulness Measurement Harness (claim extraction, metrics, CIs, Audit-Failure Rate)."""

import pytest
from eval.faithfulness.claim_extractor import extract_claims
from eval.faithfulness.metrics import (
    bootstrap_ci,
    compute_audit_failure_rate,
    compute_retrieval_metrics,
)


def test_claim_extractor():
    text = "Structuring involves splitting cash deposits [E1]. FATF Recommendation 10 mandates CDD [E2]."
    claims = extract_claims(text)
    assert len(claims) == 2
    assert "Structuring" in claims[0].text
    assert claims[0].citations == ["E1"]
    assert claims[1].citations == ["E2"]


def test_retrieval_metrics_formula_distinctness():
    """ASSERT that Precision@k and Recall@k use DISTINCT formulas."""
    retrieved = ["doc1", "doc2", "doc3", "doc4", "doc5"]
    gold = ["doc1", "doc2", "doc-extra-1", "doc-extra-2", "doc-extra-3", "doc-extra-4", "doc-extra-5", "doc-extra-6", "doc-extra-7", "doc-extra-8"]
    
    # retrieved[:5] has 2 hits ("doc1", "doc2")
    # k = 5, len(gold) = 10
    metrics = compute_retrieval_metrics(retrieved, gold, k=5)
    
    # Precision@5 = 2 / 5 = 0.4000
    assert metrics["precision_at_k"] == 0.4000
    
    # Recall@5 = 2 / 10 = 0.2000
    assert metrics["recall_at_k"] == 0.2000
    
    # Verify formulas are DISTINCT and NOT equal by coincidence!
    assert metrics["precision_at_k"] != metrics["recall_at_k"]


def test_audit_failure_rate_fixture():
    """Verify Audit-Failure Rate calculation on synthetic fixture with hand-computed value."""
    # 5 queries: 4 correct, 1 incorrect
    # Groundedness scores: [0.90, 0.70, 0.95, 0.50, 0.40]
    # For tau = 0.8:
    # Item 1: correct=True, g=0.90 >= 0.8 -> No failure
    # Item 2: correct=True, g=0.70 < 0.8 -> FAILURE 1
    # Item 3: correct=True, g=0.95 >= 0.8 -> No failure
    # Item 4: correct=True, g=0.50 < 0.8 -> FAILURE 2
    # Item 5: correct=False, g=0.40 -> Not counted (only correct answers that lack grounding cause audit failure)
    
    correct_flags = [True, True, True, True, False]
    groundedness = [0.90, 0.70, 0.95, 0.50, 0.40]
    
    rate = compute_audit_failure_rate(correct_flags, groundedness, tau=0.8)
    # 2 failures / 5 total = 0.4000
    assert rate == 0.4000


def test_bootstrap_ci():
    data = [0.8, 0.85, 0.9, 0.75, 0.88, 0.92]
    mean, lower, upper = bootstrap_ci(data, seed=42)
    assert lower <= mean <= upper
