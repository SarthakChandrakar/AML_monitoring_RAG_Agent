"""Adapter layer connecting the Streamlit UI to retrieval/, risk/, and compliance/ backend modules."""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

import streamlit as st

from ui.helpers import PROJECT_ROOT

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from retrieval.kb_store import KBStore
from retrieval.txn_store import TxnStore
from risk.models import Transaction, RiskAssessment
from risk.risk_engine import score_transaction


@dataclass
class BackendStatus:
    kb_store_ready: bool = False
    txn_store_ready: bool = False
    risk_ready: bool = False
    errors: list[str] = field(default_factory=list)


@st.cache_resource(show_spinner=False)
def get_kb_store() -> KBStore:
    return KBStore()


@st.cache_resource(show_spinner=False)
def get_txn_store() -> TxnStore:
    return TxnStore()


def search_kb(query: str, top_k: int = 5, mode: str = "hybrid") -> Tuple[List[Dict[str, Any]], float, str | None]:
    """Search regulatory AML evidence passages. Returns (chunks, latency_ms, error)."""
    try:
        kb = get_kb_store()
        t0 = time.perf_counter()
        if mode == "dense":
            hits = kb.search_dense(query, top_k=top_k)
        elif mode == "sparse":
            hits = kb.search_sparse(query, top_k=top_k)
        else:
            hits = kb.search_hybrid(query, top_k=top_k)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        return hits, round(elapsed_ms, 2), None
    except Exception as exc:
        return [], 0.0, f"{type(exc).__name__}: {exc}"


def evaluate_transaction_risk(transaction: Dict[str, Any] | Transaction) -> Tuple[RiskAssessment, str | None]:
    """Pure rule-based risk evaluation (strictly isolated from vector retrieval)."""
    try:
        if not isinstance(transaction, Transaction):
            txn = Transaction.from_dict(transaction)
        else:
            txn = transaction
        assessment = score_transaction(txn)
        return assessment, None
    except Exception as exc:
        return score_transaction(Transaction(0.0, "None", "USD", "USD")), f"{type(exc).__name__}: {exc}"


def fetch_sample_transactions(limit: int = 25) -> List[Dict[str, Any]]:
    """Fetch structured transaction records from DuckDB txn_store."""
    try:
        store = get_txn_store()
        return store.query_transactions(limit=limit)
    except Exception:
        # Fallback sample transactions if DuckDB query fails
        return [
            {
                "timestamp": "2026/08/01 09:30",
                "sender_account": "100234",
                "receiver_account": "884120",
                "amount_paid": 25000.0,
                "payment_currency": "US Dollar",
                "receiving_currency": "Bitcoin",
                "payment_format": "Cash",
                "is_laundering": 1,
            },
            {
                "timestamp": "2026/08/01 10:15",
                "sender_account": "200456",
                "receiver_account": "771239",
                "amount_paid": 8500.0,
                "payment_currency": "US Dollar",
                "receiving_currency": "US Dollar",
                "payment_format": "ACH",
                "is_laundering": 0,
            },
            {
                "timestamp": "2026/08/01 11:00",
                "sender_account": "300789",
                "receiver_account": "993411",
                "amount_paid": 12500.0,
                "payment_currency": "US Dollar",
                "receiving_currency": "Euro",
                "payment_format": "Cash",
                "is_laundering": 1,
            },
        ]


def backend_status() -> BackendStatus:
    status = BackendStatus()
    try:
        get_kb_store()
        status.kb_store_ready = True
    except Exception as e:
        status.errors.append(f"kb_store: {e}")

    try:
        get_txn_store()
        status.txn_store_ready = True
    except Exception as e:
        status.errors.append(f"txn_store: {e}")

    try:
        score_transaction(Transaction(100.0, "ACH", "USD", "USD"))
        status.risk_ready = True
    except Exception as e:
        status.errors.append(f"risk_engine: {e}")

    return status
