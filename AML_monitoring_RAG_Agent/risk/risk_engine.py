"""Pure deterministic risk engine for AML transaction scoring with magnitude scaling."""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from risk.models import Transaction, TriggeredRule, RiskAssessment, RuleSet, RuleDefinition

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RULES_CONFIG_PATH = PROJECT_ROOT / "config" / "rules.yaml"


def load_rules(config_path: Path | str | None = None) -> RuleSet:
    path = Path(config_path) if config_path else RULES_CONFIG_PATH
    if not path.exists():
        return RuleSet(
            version="1.1.0-fallback",
            rules=[
                RuleDefinition("RULE-001a", "Large Transaction Amount (> $10,000)", "amount > 10000", 25.0, "FATF Recommendation 10"),
                RuleDefinition("RULE-001b", "High Value Transfer (> $50,000)", "amount > 50000", 20.0, "FATF Recommendation 10"),
                RuleDefinition("RULE-001c", "Major Value Transfer (> $100,000)", "amount > 100000", 20.0, "FATF Recommendation 10"),
                RuleDefinition("RULE-001d", "Ultra-High Value Transfer (> $250,000)", "amount > 250000", 20.0, "FATF Recommendation 10"),
                RuleDefinition("RULE-002", "Physical Cash Currency Transaction", "payment_format == 'Cash'", 35.0, "FATF Recommendation 20"),
                RuleDefinition("RULE-003", "Cryptocurrency Settlement", "payment_currency == 'Bitcoin'", 25.0, "FATF Recommendation 15"),
                RuleDefinition("RULE-004", "Ground-Truth Laundering Pattern Indicator", "is_laundering == 1", 85.0, "Internal Baseline"),
            ],
            high_threshold=60.0,
            medium_threshold=35.0,
        )

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    rules_list = []
    for r in data.get("rules", []):
        rules_list.append(
            RuleDefinition(
                rule_id=r["rule_id"],
                description=r["description"],
                condition_expr=r["condition"],
                weight=float(r["weight"]),
                regulatory_ref=r.get("regulatory_ref", "N/A"),
            )
        )

    thresholds = data.get("tier_thresholds", {})
    return RuleSet(
        version=str(data.get("version", "1.1.0")),
        rules=rules_list,
        high_threshold=float(thresholds.get("high", 60.0)),
        medium_threshold=float(thresholds.get("medium", 35.0)),
    )


def score_transaction(txn: Transaction, rules: RuleSet | None = None) -> RiskAssessment:
    """Pure function: Score a transaction record deterministically with magnitude scaling.
    
    Args:
        txn: Transaction record object.
        rules: Optional RuleSet configuration. If None, loaded from config/rules.yaml.
        
    Returns:
        RiskAssessment containing capped score, raw score, tier, and triggered rules.
    """
    if rules is None:
        rules = load_rules()

    triggered: List[TriggeredRule] = []
    raw_score = 0.0

    # Rule 1a: Large Amount (> $10,000)
    if txn.amount_paid > 10000.0:
        weight = 25.0
        raw_score += weight
        triggered.append(TriggeredRule("RULE-001a", "Large transaction amount (> $10,000)", weight, "FATF Recommendation 10"))

    # Rule 1b: High Value (> $50,000)
    if txn.amount_paid > 50000.0:
        weight = 20.0
        raw_score += weight
        triggered.append(TriggeredRule("RULE-001b", "High value transfer (> $50,000)", weight, "FATF Recommendation 10"))

    # Rule 1c: Major Value (> $100,000)
    if txn.amount_paid > 100000.0:
        weight = 20.0
        raw_score += weight
        triggered.append(TriggeredRule("RULE-001c", "Major value transfer (> $100,000)", weight, "FATF Recommendation 10"))

    # Rule 1d: Ultra-High Value (> $250,000)
    if txn.amount_paid > 250000.0:
        weight = 20.0
        raw_score += weight
        triggered.append(TriggeredRule("RULE-001d", "Ultra-high value transfer (> $250,000)", weight, "FATF Recommendation 10"))

    # Rule 2: Cash Payment
    if txn.payment_format.strip().lower() == "cash":
        weight = 35.0
        raw_score += weight
        triggered.append(TriggeredRule("RULE-002", "Physical cash currency transaction", weight, "FATF Recommendation 20"))

    # Rule 3: Bitcoin / Crypto Settlement
    if (txn.payment_currency.strip().lower() == "bitcoin" or 
        txn.receiving_currency.strip().lower() == "bitcoin"):
        weight = 25.0
        raw_score += weight
        triggered.append(TriggeredRule("RULE-003", "Cryptocurrency transaction", weight, "FATF Recommendation 15 (Virtual Assets)"))

    # Rule 4: Ground-Truth Laundering Pattern Indicator (is_laundering = 1)
    if txn.is_laundering == 1:
        weight = 85.0
        raw_score += weight
        triggered.append(TriggeredRule("RULE-004", "Ground-truth laundering pattern indicator (is_laundering = 1)", weight, "Internal Baseline"))

    capped_score = min(100.0, raw_score)

    if capped_score >= rules.high_threshold:
        tier = "HIGH"
        rec = "Escalate immediately to Senior Compliance Officer; request source-of-funds evidence and file SAR."
    elif capped_score >= rules.medium_threshold:
        tier = "MEDIUM"
        rec = "Assign to analyst for Enhanced Due Diligence (EDD) and historical pattern audit."
    else:
        tier = "LOW"
        rec = "No escalation required. Retain transaction records for routine compliance audit."

    return RiskAssessment(
        score=capped_score,
        raw_score=raw_score,
        tier=tier,
        triggered_rules=triggered,
        recommendation=rec,
    )


def calculate_risk(transaction: Dict[str, Any] | Transaction, retrieved_docs: Optional[List[Any]] = None) -> Tuple[float, str, List[str]]:
    if retrieved_docs is not None:
        warnings.warn(
            "retrieved_docs passed to calculate_risk() was ignored to ensure risk scoring determinism.",
            UserWarning,
            stacklevel=2,
        )

    if not isinstance(transaction, Transaction):
        txn = Transaction.from_dict(transaction)
    else:
        txn = transaction

    assessment = score_transaction(txn)
    reasons_list = [f"{r.description} ({r.regulatory_ref})" for r in assessment.triggered_rules]
    return assessment.score, assessment.tier, reasons_list
