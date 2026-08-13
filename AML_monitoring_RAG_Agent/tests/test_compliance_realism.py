"""Unit tests for Compliance Realism Layer (sanctions, SAR narrative, audit chain, state machine)."""

import os
import pytest
from pathlib import Path
from compliance.sanctions import screen_counterparty
from compliance.sar import generate_sar_narrative
from compliance.audit_log import log_audit_event, verify_chain
from compliance.case import AlertCase
from risk.models import Transaction, RiskAssessment, TriggeredRule


def test_sanctions_screening():
    res = screen_counterparty("AL-ZARQAWI FINANCIAL", threshold=0.75)
    assert res.is_match is True
    assert res.matched_entity["entity_id"] == "SDN-101"

    res_clean = screen_counterparty("JOHN SMITH CONSULTING", threshold=0.85)
    assert res_clean.is_match is False


def test_sar_narrative_generation():
    txn = Transaction(amount_paid=25000.0, payment_format="Cash", payment_currency="USD", receiving_currency="Bitcoin")
    assessment = RiskAssessment(
        score=85.0,
        raw_score=85.0,
        tier="HIGH",
        triggered_rules=[TriggeredRule("RULE-001", "Large amount", 25.0, "FATF Rec 10")],
    )
    
    sar_text = generate_sar_narrative(txn, assessment)
    assert "FINCEN SUSPICIOUS ACTIVITY REPORT (SAR) NARRATIVE" in sar_text
    assert "25,000.00 USD" in sar_text
    assert "[ANALYST INPUT REQUIRED]" in sar_text  # Missing fields rendered correctly


def test_audit_log_tamper_detection(tmp_path):
    test_log = tmp_path / "test_audit.jsonl"
    
    # Log 2 events
    log_audit_event("Query 1", ["c1"], "p1", "o1", log_path=test_log)
    log_audit_event("Query 2", ["c2"], "p2", "o2", log_path=test_log)

    valid, errors = verify_chain(test_log)
    assert valid is True
    assert len(errors) == 0

    # Simulate Tampering: Modify text in file
    content = test_log.read_text(encoding="utf-8")
    tampered_content = content.replace("Query 1", "TAMPERED Query 1")
    test_log.write_text(tampered_content, encoding="utf-8")

    # Verify tampering detected!
    valid_tampered, errors_tampered = verify_chain(test_log)
    assert valid_tampered is False
    assert len(errors_tampered) > 0


def test_case_state_machine():
    case = AlertCase(case_id="CASE-001", transaction_id="TX-99")
    assert case.current_state == "NEW"

    # Valid transition NEW -> TRIAGED
    ok, msg = case.transition_to("TRIAGED", "ANALYST-1", "Initial triage")
    assert ok is True
    assert case.current_state == "TRIAGED"

    # Invalid transition TRIAGED -> SAR_FILED (Must go to ESCALATED first!)
    ok_bad, msg_bad = case.transition_to("SAR_FILED", "ANALYST-1", "Direct SAR")
    assert ok_bad is False
    assert "Invalid transition" in msg_bad
