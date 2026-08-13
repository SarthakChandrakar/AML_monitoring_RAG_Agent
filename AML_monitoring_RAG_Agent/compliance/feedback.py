"""Analyst Feedback Dispositions & Alert Precision Tracking."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FEEDBACK_FILE = PROJECT_ROOT / "outputs" / "analyst_feedback.jsonl"
FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)


def record_disposition(
    case_id: str,
    disposition: str,  # "TRUE_POSITIVE" or "FALSE_POSITIVE"
    analyst_id: str,
    notes: str = "",
) -> Dict[str, Any]:
    entry = {
        "timestamp": datetime.now().isoformat(),
        "case_id": case_id,
        "disposition": disposition.upper(),
        "analyst_id": analyst_id,
        "notes": notes,
    }

    with open(FEEDBACK_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return entry


def compute_alert_precision() -> Dict[str, float]:
    """Compute overall alert precision (TP / (TP + FP))."""
    if not FEEDBACK_FILE.exists() or FEEDBACK_FILE.stat().st_size == 0:
        return {"total_feedback": 0, "true_positives": 0, "false_positives": 0, "precision": 0.0}

    tp = 0
    fp = 0

    with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    d = json.loads(line.strip())
                    disp = d.get("disposition", "")
                    if disp == "TRUE_POSITIVE":
                        tp += 1
                    elif disp == "FALSE_POSITIVE":
                        fp += 1
                except Exception:
                    continue

    total = tp + fp
    precision = (tp / total) if total > 0 else 0.0

    return {
        "total_feedback": total,
        "true_positives": tp,
        "false_positives": fp,
        "precision": round(precision, 4),
    }
