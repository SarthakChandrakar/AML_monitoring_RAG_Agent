"""Structured Transaction Query Store (txn_store) powered by DuckDB.

Provides fast relational predicate querying over amount, currency, format, and accounts.
Transactions are structured facts, NOT embedded as citable text chunks.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import duckdb
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEV_SUBSET_CSV = PROJECT_ROOT / "Data" / "dev_subset.csv"
RAW_TRANS_CSV = PROJECT_ROOT / "Data" / "HI-Small_Trans.csv"


class TxnStore:
    def __init__(self, csv_path: Path | str | None = None):
        self.con = duckdb.connect(database=":memory:")
        
        path = Path(csv_path) if csv_path else None
        if not path or not path.exists():
            if DEV_SUBSET_CSV.exists():
                path = DEV_SUBSET_CSV
            elif RAW_TRANS_CSV.exists():
                path = RAW_TRANS_CSV

        if path and path.exists():
            df = pd.read_csv(path)
            # Rename columns for clean SQL querying
            df = df.rename(columns={
                "Amount Paid": "amount_paid",
                "Payment Format": "payment_format",
                "Payment Currency": "payment_currency",
                "Receiving Currency": "receiving_currency",
                "Amount Received": "amount_received",
                "Is Laundering": "is_laundering",
                "From Bank": "from_bank",
                "Account": "sender_account",
                "To Bank": "to_bank",
                "Account.1": "receiver_account",
                "Timestamp": "timestamp"
            })
            self.con.register("transactions", df)
        else:
            # Create dummy table if no CSV exists
            self.con.execute("""
                CREATE TABLE transactions (
                    timestamp VARCHAR, from_bank INT, sender_account VARCHAR,
                    to_bank INT, receiver_account VARCHAR, amount_paid DOUBLE,
                    payment_currency VARCHAR, amount_received DOUBLE,
                    receiving_currency VARCHAR, payment_format VARCHAR, is_laundering INT
                )
            """)

    def query_transactions(
        self,
        min_amount: float | None = None,
        payment_format: str | None = None,
        currency: str | None = None,
        is_laundering: int | None = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        clauses = ["1=1"]
        params = []

        if min_amount is not None:
            clauses.append("amount_paid >= ?")
            params.append(min_amount)
        if payment_format:
            clauses.append("LOWER(payment_format) = LOWER(?)")
            params.append(payment_format)
        if currency:
            clauses.append("(LOWER(payment_currency) = LOWER(?) OR LOWER(receiving_currency) = LOWER(?))")
            params.extend([currency, currency])
        if is_laundering is not None:
            clauses.append("is_laundering = ?")
            params.append(is_laundering)

        where_str = " AND ".join(clauses)
        query = f"SELECT * FROM transactions WHERE {where_str} LIMIT {limit}"
        
        rel = self.con.execute(query, params)
        cols = [desc[0] for desc in rel.description]
        rows = rel.fetchall()

        return [dict(zip(cols, row)) for row in rows]

    def count_transactions() -> int:
        res = self.con.execute("SELECT COUNT(*) FROM transactions").fetchone()
        return res[0] if res else 0
