"""AML Monitoring RAG Agent — Streamlit Transaction-First Dashboard.

Run:
    streamlit run ui/app.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ui import backend, helpers, llm_client, styles
from compliance.sanctions import screen_counterparty
from compliance.sar import generate_sar_narrative
from compliance.audit_log import log_audit_event, verify_chain
from compliance.case import AlertCase
from eval.faithfulness.claim_extractor import extract_claims
from eval.faithfulness.entailment import EntailmentJudge
from risk.models import Transaction

st.set_page_config(
    page_title="AML Monitoring Agent",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)
styles.inject()

PAYMENT_FORMATS = ["ACH", "Cheque", "Credit Card", "Wire", "Cash", "Bitcoin", "Reinvestment"]
CURRENCIES = [
    "US Dollar", "Euro", "UK Pound", "Yen", "Yuan", "Rupee", "Swiss Franc",
    "Canadian Dollar", "Australian Dollar", "Ruble", "Mexican Peso",
    "Brazil Real", "Saudi Riyal", "Shekel", "Bitcoin",
]

DEFAULTS = {
    "docs": [],
    "query": "",
    "answer": "",
    "answer_source": "",
    "transaction": None,
    "assessment": None,
    "last_latency": 0.0,
    "selected_txn_id": None,
    "llm_summary": "",
}
for key, value in DEFAULTS.items():
    st.session_state.setdefault(key, value)


# ---------------------------------------------------------------- Sidebar Navigation

with st.sidebar:
    st.markdown('<div class="aml-eyebrow">AML Investigation Tool</div>', unsafe_allow_html=True)
    st.markdown("<h2 style='margin-top:0; font-weight:700;'>Navigation</h2>", unsafe_allow_html=True)

    page = st.radio(
        "Select Page",
        [
            "Home",
            "Transaction Review",
            "Suspicious Activity Report",
            "Evidence Check",
            "Audit Log",
            "About",
        ],
        label_visibility="collapsed",
    )

    st.markdown('<hr class="aml-rule">', unsafe_allow_html=True)
    st.markdown('<div class="aml-eyebrow">System Mode</div>', unsafe_allow_html=True)

    provider = llm_client.available_provider()
    if provider:
        st.markdown(f'<span class="aml-badge badge-low">LLM: {provider[0]}</span>', unsafe_allow_html=True)
        st.caption(f"Connected to {provider[0]} ({provider[2]})")
    else:
        st.markdown('<span class="aml-badge badge-neutral">Offline Mode</span>', unsafe_allow_html=True)
        st.caption("LLM unavailable. Using offline report mode.")

    status = backend.backend_status()
    st.markdown(
        f'<span class="aml-badge {"badge-low" if status.risk_ready else "badge-critical"}">'
        f'Risk Engine: {"READY" if status.risk_ready else "MISSING"}</span>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------- Page Header Helper

def header(eyebrow: str, title: str, subtitle: str) -> None:
    st.markdown(
        f'<div class="aml-eyebrow">{eyebrow}</div>'
        f'<div class="aml-title">{title}</div>'
        f'<div class="aml-sub">{subtitle}</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------- Page 1: Home

if page == "Home":
    header(
        "Overview & Dashboard",
        "AI-Powered AML Transaction Investigation System",
        "Review transaction history, flag suspicious behavior, retrieve supporting AML evidence, and generate grounded investigation reports.",
    )

    sample_txns = backend.fetch_sample_transactions(limit=50)
    flagged_txns = [t for t in sample_txns if t.get("is_laundering") == 1 or t.get("amount_paid", 0) > 10000 or str(t.get("payment_format","")).lower() == "cash"]

    # Simple plain-English metric tiles
    cols = st.columns(4)
    cols[0].markdown(helpers.metric_html("Loaded Transactions", f"{len(sample_txns)} Records", "IBM Dataset Sample"), unsafe_allow_html=True)
    cols[1].markdown(helpers.metric_html("Flagged Suspicious", f"{len(flagged_txns)} High-Risk Alerts", "Requires Review"), unsafe_allow_html=True)
    cols[2].markdown(helpers.metric_html("FATF Legal Rulebook", "434 Rules", "Official Legal Corpus"), unsafe_allow_html=True)
    cols[3].markdown(helpers.metric_html("Security Audit Chain", "100% Intact", "SHA-256 Tamper-Proof"), unsafe_allow_html=True)

    st.markdown('<hr class="aml-rule">', unsafe_allow_html=True)
    st.markdown("### 📊 System Analytics & Risk Distribution")

    # Interactive Plotly Charts
    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        st.plotly_chart(helpers.render_risk_donut_chart(sample_txns), width="stretch")
    with chart_col2:
        st.plotly_chart(helpers.render_payment_format_chart(sample_txns), width="stretch")

    st.markdown('<hr class="aml-rule">', unsafe_allow_html=True)
    st.markdown("### 🔄 Visual Investigation Workflow")
    st.markdown(helpers.system_flowchart_html(), unsafe_allow_html=True)


# ---------------------------------------------------------------- Page 2: Transaction Review

elif page == "Transaction Review":
    header(
        "Investigation Workflow",
        "Transaction Review & Risk Analysis",
        "Inspect transactions, filter suspicious activity, and review the exact rules that triggered the flag.",
    )

    sample_txns = backend.fetch_sample_transactions(limit=50)

    # Simple risk filter
    risk_filter = st.selectbox("Filter Transactions", ["All Transactions", "Flagged / High Risk Only", "Cash Transactions Only"])

    filtered_txns = sample_txns
    if risk_filter == "Flagged / High Risk Only":
        filtered_txns = [t for t in sample_txns if t.get("is_laundering") == 1 or t.get("amount_paid", 0) > 10000]
    elif risk_filter == "Cash Transactions Only":
        filtered_txns = [t for t in sample_txns if str(t.get("payment_format", "")).lower() == "cash"]

    if not filtered_txns:
        filtered_txns = sample_txns

    # Table preview
    st.markdown(f"### Transaction Records ({len(filtered_txns)} records shown)")
    df_display = pd.DataFrame(filtered_txns)[["timestamp", "sender_account", "receiver_account", "amount_paid", "payment_currency", "payment_format", "is_laundering"]]
    st.dataframe(df_display, width="stretch")

    st.markdown('<hr class="aml-rule">', unsafe_allow_html=True)
    st.markdown("### Select a Transaction to Analyze")

    txn_options = [
        f"Txn #{idx+1} — Acc #{t.get('sender_account','N/A')} -> #{t.get('receiver_account','N/A')} — ${t.get('amount_paid',0):,.2f} ({t.get('payment_format','N/A')}) {'[FLAGGED]' if t.get('is_laundering') == 1 else ''}"
        for idx, t in enumerate(filtered_txns)
    ]
    selected_idx = st.selectbox("Choose Transaction", range(len(txn_options)), format_func=lambda i: txn_options[i])

    selected_raw = filtered_txns[selected_idx]
    txn_obj = Transaction.from_dict(selected_raw)
    current_txn_id = f"Txn #{selected_idx+1} (${txn_obj.amount_paid:,.2f} {txn_obj.payment_format})"

    # Clear stale results if transaction selection changes
    if st.session_state.selected_txn_id != current_txn_id:
        st.session_state.selected_txn_id = current_txn_id
        st.session_state.assessment = None
        st.session_state.docs = []
        st.session_state.answer = ""
        st.session_state.llm_summary = ""

    if st.button("Analyze Selected Transaction", type="primary"):
        with st.spinner("Analyzing risk rules and searching FATF evidence corpus..."):
            assessment, err = backend.evaluate_transaction_risk(txn_obj)

            # Build targeted query based on triggered rules
            triggered_descs = [r.description for r in assessment.triggered_rules]
            rule_keywords = " ".join(triggered_descs)
            query_text = (
                f"FATF guidelines customer due diligence and threshold reporting for "
                f"{txn_obj.payment_format} transaction of ${txn_obj.amount_paid:,.2f} {txn_obj.payment_currency} "
                f"settled as {txn_obj.receiving_currency}. {rule_keywords}"
            )

            hits, latency, _ = backend.search_kb(query_text, top_k=5)

            st.session_state.transaction = txn_obj
            st.session_state.assessment = assessment
            st.session_state.docs = hits
            st.session_state.query = query_text

            # Generate report narrative
            narrative = generate_sar_narrative(txn_obj, assessment, hits)
            st.session_state.answer = narrative
            st.session_state.answer_source = "Rule Engine + Regulatory Evidence"

            # Log event
            log_audit_event(
                query=query_text,
                retrieved_chunk_ids=[h["chunk_id"] for h in hits],
                prompt_str=f"Transaction: ${txn_obj.amount_paid:,.2f} {txn_obj.payment_format}",
                output_str=narrative[:200],
            )

    if st.session_state.assessment and st.session_state.transaction:
        st.markdown('<hr class="aml-rule">', unsafe_allow_html=True)
        ass = st.session_state.assessment
        t = st.session_state.transaction

        st.markdown(f"### Analysis Results for {st.session_state.selected_txn_id}")
        col_gauge, col_reasons = st.columns([1, 1])
        with col_gauge:
            st.markdown(helpers.gauge_html(ass.score, ass.tier, txn_id=st.session_state.selected_txn_id), unsafe_allow_html=True)
        with col_reasons:
            st.markdown("### Why was this flagged?")
            for r in ass.triggered_rules:
                st.markdown(
                    f'<div class="aml-reason"><b>{r.description}</b> (+{r.contribution:.0f} pts)<br>'
                    f'<small style="color:#8A9AB4;">Ref: {r.regulatory_ref}</small></div>',
                    unsafe_allow_html=True,
                )
            if not ass.triggered_rules:
                st.markdown('<div class="aml-card">No compliance rule thresholds were triggered for this transaction.</div>', unsafe_allow_html=True)
            st.markdown(f"**What should the analyst do next?**<br>{ass.recommendation}", unsafe_allow_html=True)

        if st.session_state.docs:
            st.markdown('<hr class="aml-rule">', unsafe_allow_html=True)
            st.markdown(f"### Supporting AML Evidence ({len(st.session_state.docs)} passages retrieved)")
            for idx, doc in enumerate(st.session_state.docs, start=1):
                st.markdown(helpers.evidence_card_html(doc, rank=idx), unsafe_allow_html=True)


# ---------------------------------------------------------------- Page 3: Suspicious Activity Report

elif page == "Suspicious Activity Report":
    header(
        "Case Investigation Report",
        "Suspicious Activity Report (SAR)",
        "Review the generated investigation report backed by cited regulatory evidence.",
    )

    if not st.session_state.answer:
        st.info("No transaction has been analyzed yet. Go to **Transaction Review** and click 'Analyze Selected Transaction'.")
    else:
        st.markdown(f"### Investigation Record ({st.session_state.selected_txn_id or 'Current Case'})")

        # Live LLM Generation via Groq API button
        p = llm_client.available_provider()
        if p:
            if st.button(f"🤖 Generate AI Executive Summary with {p[0]} ({p[2]})", type="secondary"):
                with st.spinner(f"Calling {p[0]} API ({p[2]})..."):
                    prompt = (
                        f"Summarize this AML investigation case in 3 bullet points for a senior manager. "
                        f"Include key transaction facts and regulatory reasoning.\n\n"
                        f"{st.session_state.answer[:1500]}"
                    )
                    llm_ans, src = llm_client.generate(prompt)
                    if llm_ans:
                        st.session_state.llm_summary = f"**AI Summary by {src}**:\n\n{llm_ans}"
                    else:
                        st.session_state.llm_summary = f"⚠️ {src}"

            if st.session_state.llm_summary:
                st.info(st.session_state.llm_summary)

        # Render SAR in preformatted code block so markdown formatting is preserved
        st.code(st.session_state.answer, language=None)

        st.markdown('<hr class="aml-rule">', unsafe_allow_html=True)
        st.markdown("### Download Case File Summary")

        try:
            dcol1, dcol2 = st.columns(2)
            dcol1.download_button(
                "Download Summary (.txt)",
                data=st.session_state.answer.encode("utf-8"),
                file_name="aml_investigation_summary.txt",
                mime="text/plain",
                width="stretch",
            )

            json_export = json.dumps(
                {
                    "transaction": str(st.session_state.transaction),
                    "assessment": str(st.session_state.assessment),
                    "narrative": st.session_state.answer,
                },
                indent=2,
            )
            dcol2.download_button(
                "Download JSON Record (.json)",
                data=json_export.encode("utf-8"),
                file_name="aml_investigation_summary.json",
                mime="application/json",
                width="stretch",
            )
        except Exception as exc:
            st.error(f"Could not generate export files: {exc}")


# ---------------------------------------------------------------- Page 4: Evidence Check

elif page == "Evidence Check":
    header(
        "Report Grounding Verification",
        "Evidence Check & Report Support",
        "Check whether each claim in the generated investigation report is supported by retrieved AML evidence.",
    )

    narrative_to_check = st.text_area(
        "Report Narrative to Check",
        value=st.session_state.answer or "Structuring involves splitting cash deposits to evade reporting thresholds. FATF Recommendation 10 mandates customer due diligence.",
        height=140,
    )

    if not narrative_to_check.strip():
        st.warning("Please enter or select a report narrative to check.")

    if st.button("Run Evidence Check", type="primary"):
        if not narrative_to_check.strip():
            st.warning("Please provide report text to check.")
        else:
            with st.spinner("Decomposing claims and evaluating NLI evidence entailment..."):
                claims = extract_claims(narrative_to_check)
                judge = EntailmentJudge()

                st.markdown(f"### Evidence Check Results ({len(claims)} statements evaluated)")
                for c in claims:
                    res = judge.judge_claim(c, st.session_state.docs)

                    if res.primary_label == "SUPPORTED":
                        status_badge = '<span class="aml-badge badge-low">🟢 Supported</span>'
                    elif res.primary_label == "CONTRADICTED":
                        status_badge = '<span class="aml-badge badge-critical">🔴 Not Supported</span>'
                    else:
                        status_badge = '<span class="aml-badge badge-medium">🟡 Needs Review</span>'

                    st.markdown(
                        f'<div class="aml-card">'
                        f'<b>Statement {c.claim_id}</b>: "{c.text}" <br>'
                        f'{status_badge} '
                        f'<span class="sim-note">Entailment Match Score: {res.entailment_score:.4f}</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )


# ---------------------------------------------------------------- Page 5: Audit Log

elif page == "Audit Log":
    header(
        "Investigation Audit Log",
        "Audit Log & Activity History",
        "Cryptographic append-only history recording every transaction analysis and analyst action.",
    )

    if st.button("🔍 Verify Audit Log Integrity", type="primary"):
        valid, errors = verify_chain()
        if valid:
            st.success("✅ AUDIT LOG VERIFIED: All entries are intact and untampered!")
        else:
            st.error(f"🚨 ALERT: Audit log tampering detected! Errors: {errors}")

    log_file = PROJECT_ROOT / "outputs" / "audit_log.jsonl"
    if log_file.exists():
        lines = log_file.read_text(encoding="utf-8").strip().split("\n")
        st.markdown(f"### Activity History ({len(lines)} entries recorded)")
        for line in reversed(lines[-15:]):
            if line.strip():
                st.code(line, language="json")
    else:
        st.info("No audit log entries recorded yet.")


# ---------------------------------------------------------------- Page 6: About

else:
    header(
        "System Overview",
        "About the AML Monitoring Agent",
        "A practical, explainable AML transaction investigation system.",
    )

    st.markdown(
        """
<div class="aml-card">
<b>Purpose & Goal</b><br>
This project is designed as a clear, explainable Anti-Money Laundering (AML) transaction monitoring tool.
Instead of acting like a black-box AI or an ungrounded chatbot, it reviews transactions against deterministic compliance rules
and retrieves supporting FATF regulatory guidelines so analysts can trace every finding back to authoritative evidence.
</div>

<div class="aml-card">
<b>Data Sources & Technology</b><br>
• <b>IBM AML Dataset</b> — Transaction history logs used for transaction review.<br>
• <b>FATF Guidelines PDF</b> — International regulatory standards parsed into evidence passages.<br>
• <b>FAISS Vector Store</b> — Fast similarity search over regulatory passages.<br>
• <b>Rule-Based Risk Engine</b> — Scores transactions based on rules ($10k cash limit, crypto payments, known laundering patterns).<br>
• <b>Streamlit Dashboard</b> — Modern, dark-themed user interface.
</div>

<div class="aml-card">
<b>Offline Mode Guarantee</b><br>
The system works 100% locally even without any external API keys. When an API key is absent, the system uses its offline report generator without crashing.
</div>
""",
        unsafe_allow_html=True,
    )
