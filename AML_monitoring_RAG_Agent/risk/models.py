"""Domain models and data structures for the pure AML risk engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class Transaction:
    amount_paid: float
    payment_format: str
    payment_currency: str
    receiving_currency: str
    is_laundering: int = 0
    sender_account: Optional[str] = None
    receiver_account: Optional[str] = None
    timestamp: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Transaction:
        try:
            amount = float(data.get("Amount Paid", data.get("amount_paid", 0.0)))
        except (TypeError, ValueError):
            amount = 0.0

        try:
            is_laundering = int(data.get("Is Laundering", data.get("is_laundering", 0)))
        except (TypeError, ValueError):
            is_laundering = 0

        sender = (
            data.get("sender_account")
            or data.get("Account")
            or data.get("sender")
            or data.get("Sender Account")
        )
        receiver = (
            data.get("receiver_account")
            or data.get("Account.1")
            or data.get("receiver")
            or data.get("Receiver Account")
        )
        t_stamp = (
            data.get("timestamp")
            or data.get("Timestamp")
            or data.get("date")
            or data.get("Time")
        )

        return cls(
            amount_paid=amount,
            payment_format=str(data.get("Payment Format", data.get("payment_format", ""))),
            payment_currency=str(data.get("Payment Currency", data.get("payment_currency", ""))),
            receiving_currency=str(data.get("Receiving Currency", data.get("receiving_currency", ""))),
            is_laundering=is_laundering,
            sender_account=str(sender) if sender else None,
            receiver_account=str(receiver) if receiver else None,
            timestamp=str(t_stamp) if t_stamp else None,
        )


@dataclass(frozen=True)
class TriggeredRule:
    rule_id: str
    description: str
    contribution: float
    regulatory_ref: str


@dataclass(frozen=True)
class RiskAssessment:
    score: float
    raw_score: float
    tier: str
    triggered_rules: List[TriggeredRule] = field(default_factory=list)
    recommendation: str = ""

    @property
    def risk_score(self) -> float:
        return self.score

    @property
    def risk_level(self) -> str:
        return self.tier

    @property
    def reasons(self) -> List[str]:
        return [f"{r.description} ({r.regulatory_ref})" for r in self.triggered_rules]


@dataclass
class RuleDefinition:
    rule_id: str
    description: str
    condition_expr: str
    weight: float
    regulatory_ref: str


@dataclass
class RuleSet:
    version: str
    rules: List[RuleDefinition]
    high_threshold: float = 80.0
    medium_threshold: float = 50.0
