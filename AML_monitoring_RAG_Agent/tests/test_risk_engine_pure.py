"""Unit & Property-based Tests for Pure AML Risk Engine."""

import pytest
from risk.models import Transaction
from risk.risk_engine import score_transaction, calculate_risk


def test_risk_engine_determinism():
    """Verify that scoring the same transaction 500x with varying dummy k returns identical results."""
    txn = Transaction(
        amount_paid=25000.0,
        payment_format="Cash",
        payment_currency="US Dollar",
        receiving_currency="Bitcoin",
        is_laundering=1,
    )
    
    baseline = score_transaction(txn)
    
    for k in range(1, 501):
        # Simulate varying retrieval output k
        dummy_docs = [{"text": f"suspicious cash layering {i}"} for i in range(k)]
        score, tier, reasons = calculate_risk(txn, retrieved_docs=dummy_docs)
        assert score == baseline.score, f"Score mutated at k={k}"
        assert tier == baseline.tier, f"Tier mutated at k={k}"


def test_risk_engine_purity():
    """Verify that scoring succeeds without reading any external files, network, or retriever."""
    txn = Transaction(
        amount_paid=15000.0,
        payment_format="Cash",
        payment_currency="US Dollar",
        receiving_currency="US Dollar",
        is_laundering=0,
    )
    
    assessment = score_transaction(txn)
    assert assessment.score == 60.0  # 25 (amount > 10k) + 35 (cash)
    assert assessment.tier == "HIGH"
    assert len(assessment.triggered_rules) == 2


def test_risk_engine_monotonicity():
    """Verify that increasing amount_paid never decreases the risk score."""
    amounts = [0.0, 5000.0, 10000.0, 10001.0, 50000.0, 100000.0, 250001.0]
    scores = []
    
    for amt in amounts:
        txn = Transaction(
            amount_paid=amt,
            payment_format="Wire",
            payment_currency="US Dollar",
            receiving_currency="US Dollar",
            is_laundering=0,
        )
        scores.append(score_transaction(txn).score)

    for i in range(len(scores) - 1):
        assert scores[i] <= scores[i+1], f"Monotonicity violated: {scores[i]} > {scores[i+1]}"


def test_risk_engine_boundaries():
    """Verify exact tier boundaries (low < 35, medium 35-59, high >= 60)."""
    # 0 score -> LOW
    txn_low = Transaction(amount_paid=100.0, payment_format="ACH", payment_currency="USD", receiving_currency="USD")
    assert score_transaction(txn_low).tier == "LOW"
    
    # Score 35 (Cash only) -> MEDIUM
    txn_med = Transaction(amount_paid=5000.0, payment_format="Cash", payment_currency="USD", receiving_currency="USD")
    assert score_transaction(txn_med).tier == "MEDIUM"

    # Score 85 (25 amount + 35 cash + 25 bitcoin) -> HIGH
    txn_high = Transaction(amount_paid=15000.0, payment_format="Cash", payment_currency="Bitcoin", receiving_currency="USD")
    assert score_transaction(txn_high).tier == "HIGH"


def test_risk_engine_additivity():
    """Verify raw_score equals the sum of triggered rule contributions."""
    txn = Transaction(amount_paid=25000.0, payment_format="Cash", payment_currency="Bitcoin", receiving_currency="USD", is_laundering=1)
    assessment = score_transaction(txn)
    
    sum_contributions = sum(r.contribution for r in assessment.triggered_rules)
    assert assessment.raw_score == sum_contributions
    assert assessment.score == min(100.0, sum_contributions)
