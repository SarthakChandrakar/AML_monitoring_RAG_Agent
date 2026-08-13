"""Shared helpers for the AML dashboard: evidence cards, risk score gauges, metric cards, charts, and report exporters."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import plotly.graph_objects as go
import plotly.express as px

PROJECT_ROOT = Path(__file__).resolve().parents[1]

RISK_COLORS = {
    "LOW": "#2FBF71",
    "MEDIUM": "#E8B931",
    "HIGH": "#FF7A45",
    "CRITICAL": "#FF3B5C",
    "UNKNOWN": "#8A9AB4",
}


def _get_val(t: Any, key: str, default: Any = None) -> Any:
    """Safely extract field value whether t is a dict or a dataclass object."""
    if isinstance(t, dict):
        return t.get(key, default)
    return getattr(t, key, default)


def evidence_card_html(doc: Dict[str, Any], rank: int = 1) -> str:
    """Render a clean, readable evidence card with source citation and Cosine Similarity."""
    cosine_val = doc.get("cosine_similarity", doc.get("score", 0.0))
    if cosine_val > 1.0 or cosine_val < -1.0:
        cosine_val = max(0.0, 1.0 - (cosine_val / 4.0))

    citation = doc.get("citation_string") or f"{doc.get('source_type', '').upper()} ({doc.get('category', '')})"
    excerpt_text = doc.get("text", "").strip()

    return f"""
<div class="aml-evidence">
  <div class="head">
    <span class="rank">Passage {rank}</span>
    <span class="aml-badge badge-accent">{citation}</span>
    <span class="aml-badge badge-neutral">{doc.get('category', 'general')}</span>
    <span class="sim-note" style="margin-left:auto;">
      Cosine Similarity Score: <b>{cosine_val:.4f}</b>
    </span>
  </div>
  <div class="excerpt">{excerpt_text[:500]}</div>
</div>
"""


def gauge_html(score: float, level: str, txn_id: str = "") -> str:
    """Render a simple, clear radial risk score gauge with transaction identity."""
    pct = max(0, min(100, round(float(score))))
    color = RISK_COLORS.get(str(level).upper(), RISK_COLORS["UNKNOWN"])
    deg = pct * 3.6
    txn_label = f"For Transaction {txn_id}" if txn_id else "Deterministic Assessment"
    return f"""
<div class="aml-gauge-wrap">
  <div class="aml-gauge" style="background: conic-gradient({color} 0deg {deg}deg, #223049 {deg}deg 360deg);">
    <div class="inner">
      <div class="score" style="color:{color}">{pct}</div>
      <div class="of">/ 100</div>
    </div>
  </div>
  <div>
    <div class="aml-eyebrow">Transaction Risk Rating</div>
    <div style="margin-bottom: 0.4rem;"><span class="aml-badge" style="color:{color}; border-color:{color}; font-weight:700;">{level} RISK</span></div>
    <div style="font-size: 0.82rem; color: #8A9AB4;">{txn_label}</div>
  </div>
</div>
"""


def metric_html(label: str, value: Any, note: str = "") -> str:
    """Render a clean metric card."""
    note_html = f'<div class="note">{note}</div>' if note else ""
    return f"""
<div class="aml-metric">
  <div class="label">{label}</div>
  <div class="value">{value}</div>
  {note_html}
</div>
"""


def system_flowchart_html() -> str:
    """Render a visual 5-step interactive process diagram for the Homepage."""
    return """
<div style="display: flex; gap: 0.8rem; flex-wrap: wrap; margin: 1rem 0;">
  <div style="flex: 1; min-width: 170px; background: #111A2B; border: 1px solid #223049; border-top: 4px solid #4C8DFF; border-radius: 8px; padding: 0.9rem;">
    <div style="font-size: 1.2rem; margin-bottom: 0.3rem;">📥 Step 1</div>
    <div style="font-weight: 700; color: #FFFFFF; font-size: 0.95rem; margin-bottom: 0.2rem;">Load Transaction</div>
    <div style="font-size: 0.80rem; color: #8A9AB4;">Reads transaction amount, cash, wire, or crypto format.</div>
  </div>
  <div style="flex: 1; min-width: 170px; background: #111A2B; border: 1px solid #223049; border-top: 4px solid #FF7A45; border-radius: 8px; padding: 0.9rem;">
    <div style="font-size: 1.2rem; margin-bottom: 0.3rem;">⚙️ Step 2</div>
    <div style="font-weight: 700; color: #FFFFFF; font-size: 0.95rem; margin-bottom: 0.2rem;">Rule Risk Engine</div>
    <div style="font-size: 0.80rem; color: #8A9AB4;">Calculates 0–100 risk rating (Low, Medium, High).</div>
  </div>
  <div style="flex: 1; min-width: 170px; background: #111A2B; border: 1px solid #223049; border-top: 4px solid #E8B931; border-radius: 8px; padding: 0.9rem;">
    <div style="font-size: 1.2rem; margin-bottom: 0.3rem;">🔍 Step 3</div>
    <div style="font-weight: 700; color: #FFFFFF; font-size: 0.95rem; margin-bottom: 0.2rem;">FATF Legal Search</div>
    <div style="font-size: 0.80rem; color: #8A9AB4;">Vector search retrieves exact matching legal rules.</div>
  </div>
  <div style="flex: 1; min-width: 170px; background: #111A2B; border: 1px solid #223049; border-top: 4px solid #2FBF71; border-radius: 8px; padding: 0.9rem;">
    <div style="font-size: 1.2rem; margin-bottom: 0.3rem;">📄 Step 4</div>
    <div style="font-weight: 700; color: #FFFFFF; font-size: 0.95rem; margin-bottom: 0.2rem;">SAR Report Writer</div>
    <div style="font-size: 0.80rem; color: #8A9AB4;">Drafts FinCEN Suspicious Activity Report with citations.</div>
  </div>
  <div style="flex: 1; min-width: 170px; background: #111A2B; border: 1px solid #223049; border-top: 4px solid #9D4EDD; border-radius: 8px; padding: 0.9rem;">
    <div style="font-size: 1.2rem; margin-bottom: 0.3rem;">🔒 Step 5</div>
    <div style="font-weight: 700; color: #FFFFFF; font-size: 0.95rem; margin-bottom: 0.2rem;">Security Audit Log</div>
    <div style="font-size: 0.80rem; color: #8A9AB4;">Saves immutable SHA-256 digital fingerprint.</div>
  </div>
</div>
"""


def render_risk_donut_chart(transactions: List[Any]) -> go.Figure:
    """Render a clean Plotly Donut Chart showing transaction risk breakdown."""
    high_count = 0
    medium_count = 0
    low_count = 0

    for t in transactions:
        is_laun = _get_val(t, "is_laundering", 0)
        amt = float(_get_val(t, "amount_paid", 0.0) or 0.0)
        fmt = str(_get_val(t, "payment_format", "")).lower()

        if is_laun == 1 or amt > 50000 or (fmt == "cash" and amt > 10000):
            high_count += 1
        elif fmt == "cash" or amt > 10000:
            medium_count += 1
        else:
            low_count += 1

    labels = ["High Risk / Flagged", "Medium Risk (EDD)", "Low Risk (Routine)"]
    values = [high_count, medium_count, low_count]
    colors = ["#FF7A45", "#E8B931", "#2FBF71"]

    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.55,
                marker=dict(colors=colors, line=dict(color="#111A2B", width=2)),
                textinfo="label+percent",
                hoverinfo="label+value+percent",
            )
        ]
    )

    fig.update_layout(
        title=dict(text="Transaction Risk Category Breakdown", font=dict(color="#E6EDF7", size=15)),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=True,
        legend=dict(font=dict(color="#8A9AB4"), orientation="h", y=-0.1),
        margin=dict(l=20, r=20, t=40, b=20),
        height=260,
    )
    return fig


def render_payment_format_chart(transactions: List[Any]) -> go.Figure:
    """Render a clean Plotly Bar Chart showing transaction breakdown by payment format."""
    counts: Dict[str, int] = {}
    for t in transactions:
        fmt_raw = _get_val(t, "payment_format", "Other")
        fmt = str(fmt_raw if fmt_raw else "Other").capitalize()
        counts[fmt] = counts.get(fmt, 0) + 1

    formats = list(counts.keys())
    values = list(counts.values())

    fig = go.Figure(
        data=[
            go.Bar(
                x=formats,
                y=values,
                marker=dict(color="#4C8DFF", line=dict(color="#111A2B", width=1)),
                text=values,
                textposition="auto",
            )
        ]
    )

    fig.update_layout(
        title=dict(text="Volume by Payment Instrument", font=dict(color="#E6EDF7", size=15)),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(tickfont=dict(color="#8A9AB4"), title="Payment Format"),
        yaxis=dict(tickfont=dict(color="#8A9AB4"), title="Number of Transactions"),
        margin=dict(l=20, r=20, t=40, b=20),
        height=260,
    )
    return fig
