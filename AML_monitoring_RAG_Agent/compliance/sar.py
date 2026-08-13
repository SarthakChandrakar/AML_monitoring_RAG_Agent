"""FinCEN 5-Part Suspicious Activity Report (SAR) Narrative Generator.

Populates Who/What/When/Where/Why strictly from structured transaction records
and cited regulatory evidence. Unsupported fields render as [ANALYST INPUT REQUIRED].
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from risk.models import Transaction, RiskAssessment


def derive_activity_type(txn: Transaction, risk_assessment: RiskAssessment | None = None) -> str:
    """Dynamically derive suspicious activity type based on triggered rules rather than hardcoded string."""
    activities = []
    if txn.is_laundering == 1:
        activities.append("Known Suspicious Laundering Pattern")
    if txn.payment_format.strip().lower() == "cash":
        activities.append("Physical Currency Transaction (CTR Threshold)")
    if txn.payment_currency.strip().lower() == "bitcoin" or txn.receiving_currency.strip().lower() == "bitcoin":
        activities.append("Virtual Asset / Cryptocurrency Settlement")
    if txn.amount_paid > 250000.0:
        activities.append("Ultra-High Value Capital Transfer")
    elif txn.amount_paid > 10000.0:
        activities.append("Large Value Transfer (> $10,000)")

    if activities:
        return " / ".join(activities)
    return "Routine Compliance Review"


def generate_sar_narrative(
    transaction: Transaction | Dict[str, Any],
    risk_assessment: RiskAssessment | None = None,
    evidence_chunks: List[Dict[str, Any]] | None = None,
    analyst_id: str = "ANALYST-OFFICER-01",
) -> str:
    if isinstance(transaction, dict):
        txn = Transaction.from_dict(transaction)
    else:
        txn = transaction

    evidence_chunks = evidence_chunks or []
    reasons = risk_assessment.reasons if risk_assessment else []

    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Extract sender, receiver, timestamp with fallbacks
    s_acc = txn.sender_account
    r_acc = txn.receiver_account
    t_time = txn.timestamp

    who_sender = f"Account #{s_acc}" if (s_acc and str(s_acc).strip() not in ("", "None", "NoneType")) else "[ANALYST INPUT REQUIRED]"
    who_receiver = f"Account #{r_acc}" if (r_acc and str(r_acc).strip() not in ("", "None", "NoneType")) else "[ANALYST INPUT REQUIRED]"
    tx_time = str(t_time).strip() if (t_time and str(t_time).strip() not in ("", "None", "NoneType")) else "[ANALYST INPUT REQUIRED]"

    fmt = txn.payment_format if txn.payment_format else "[ANALYST INPUT REQUIRED]"
    pay_curr = txn.payment_currency if txn.payment_currency else "[ANALYST INPUT REQUIRED]"
    rec_curr = txn.receiving_currency if txn.receiving_currency else "[ANALYST INPUT REQUIRED]"

    activity_type = derive_activity_type(txn, risk_assessment)
    tier = risk_assessment.tier if risk_assessment else "UNKNOWN"
    score = risk_assessment.score if risk_assessment else 0.0

    # Header title based on tier
    if tier in ("HIGH", "CRITICAL"):
        doc_header = "FINCEN SUSPICIOUS ACTIVITY REPORT (SAR) NARRATIVE"
        doc_status = "DRAFT — MANDATORY ESCALATION TO SENIOR COMPLIANCE OFFICER"
    elif tier == "MEDIUM":
        doc_header = "ENHANCED DUE DILIGENCE (EDD) COMPLIANCE MEMORANDUM"
        doc_status = "PENDING ANALYST ENHANCED DUE DILIGENCE AUDIT"
    else:
        doc_header = "TRANSACTION INVESTIGATION MEMO (NO SAR FILING REQUIRED)"
        doc_status = "CLOSED — ROUTINE RECORD RETENTION ONLY"

    # Format cited evidence
    citations_str = ""
    if evidence_chunks:
        citations = []
        for c in evidence_chunks[:5]:
            cit = c.get("citation_string") or f"{c.get('source_type', '').upper()} ({c.get('category', '')})"
            citations.append(f"  - [{cit}]: {c.get('text', '').strip()[:200]}…")
        citations_str = "\n".join(citations)
    else:
        citations_str = "  - [ANALYST INPUT REQUIRED: No regulatory passages cited]"

    # Format triggers
    triggers_str = ""
    if reasons:
        triggers_str = "\n".join(f"  - {r}" for r in reasons)
    else:
        triggers_str = "  - [NO RULE VIOLATIONS TRIGGERED: Transaction within routine thresholds]"

    narrative = f"""
================================================================================
{doc_header}
================================================================================
Filing Date       : {stamp}
Analyst Officer ID: {analyst_id}
Status            : {doc_status}
================================================================================

1. SUBJECT INFORMATION (WHO)
--------------------------------------------------------------------------------
Primary Subject Account   : {who_sender}
Beneficial Counterparty   : {who_receiver}
Customer Tax ID / SSN     : [ANALYST INPUT REQUIRED]
Customer Occupation / KYC : [ANALYST INPUT REQUIRED]

2. SUSPICIOUS ACTIVITY SUMMARY (WHAT)
--------------------------------------------------------------------------------
Activity Type             : {activity_type}
Transaction Amount        : ${txn.amount_paid:,.2f} {pay_curr}
Settlement Instrument     : {fmt} (Settled as {rec_curr})
Risk Rating               : {tier} RISK (Score: {score:.0f}/100)
Triggered Compliance Rules:
{triggers_str}

3. TIMELINE & CHRONOLOGY (WHEN)
--------------------------------------------------------------------------------
Transaction Date/Time     : {tx_time}
Alert Detection Timestamp : {stamp}

4. INSTITUTION & LOCATION (WHERE)
--------------------------------------------------------------------------------
Originating Account       : {who_sender}
Destination Account       : {who_receiver}
Geographic Jurisdiction   : [ANALYST INPUT REQUIRED]

5. TYPOLOGY & REGULATORY BASIS (WHY)
--------------------------------------------------------------------------------
The transaction activity described above has been evaluated against FATF guidelines
and internal AML typologies. Grounded regulatory evidence cited:

{citations_str}

Disposition Recommendation: {risk_assessment.recommendation if risk_assessment else '[ANALYST INPUT REQUIRED]'}
================================================================================
    """.strip()

    return narrative
