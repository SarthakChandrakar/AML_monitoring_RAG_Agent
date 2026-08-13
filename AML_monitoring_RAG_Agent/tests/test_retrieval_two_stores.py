"""Unit tests for Two-Store Retrieval Architecture (kb_store & txn_store)."""

import pytest
from retrieval.kb_store import KBStore
from retrieval.txn_store import TxnStore


def test_kb_store_dense_search():
    kb = KBStore()
    results = kb.search_dense("FATF recommendations on customer due diligence", top_k=5)
    assert len(results) > 0
    first = results[0]
    assert "cosine_similarity" in first
    assert 0.0 <= first["cosine_similarity"] <= 1.0
    assert "citation_string" in first
    assert first["source_type"] in ["pdf", "json"]


def test_kb_store_hybrid_rrf_search():
    kb = KBStore()
    results = kb.search_hybrid("structuring cash deposits threshold", top_k=5)
    assert len(results) > 0
    assert "rrf_score" in results[0]
    assert "citation_string" in results[0]


def test_txn_store_predicate_query():
    txn_store = TxnStore()
    results = txn_store.query_transactions(min_amount=10000.0, payment_format="Cash", limit=5)
    assert isinstance(results, list)
    for r in results:
        assert r["amount_paid"] >= 10000.0
        assert r["payment_format"].lower() == "cash"
