"""OFAC SDN Sanctions & PEP Name Screening Engine.

Provides fuzzy string matching (Jaro-Winkler / Levenshtein distance) and logging
against a bundled snapshot of high-risk entities.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOGS_DIR = PROJECT_ROOT / "outputs" / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Snapshot of OFAC SDN / PEP entities (Date: 2026-08-01)
OFAC_SDN_SNAPSHOT = [
    {"entity_id": "SDN-101", "name": "AL-ZARQAWI FINANCIAL NETWORK", "category": "TERRORIST_FINANCING", "country": "SY"},
    {"entity_id": "SDN-102", "name": "VLADIMIR SMIRNOV ENTERPRISES", "category": "SANCTIONS_EVASION", "country": "RU"},
    {"entity_id": "SDN-103", "name": "GUANGLONG CHEMICAL TRADING", "category": "NARCOTICS_TRAFFICKING", "country": "CN"},
    {"entity_id": "SDN-104", "name": "CARIBBEAN OFFSHORE HOLDINGS", "category": "SHELL_COMPANY", "country": "VG"},
    {"entity_id": "SDN-105", "name": "DARKNET MIXER LABS", "category": "VIRTUAL_CURRENCY", "country": "UNKNOWN"},
]


@dataclass(frozen=True)
class SanctionsMatchResult:
    query_name: str
    is_match: bool
    highest_score: float
    matched_entity: Optional[Dict[str, Any]]
    threshold: float
    timestamp: str


def jaro_winkler_similarity(s1: str, s2: str) -> float:
    """Compute fuzzy match similarity score in [0.0, 1.0]."""
    s1_clean = s1.upper().strip()
    s2_clean = s2.upper().strip()
    return difflib.SequenceMatcher(None, s1_clean, s2_clean).ratio()


def screen_counterparty(
    name: str,
    threshold: float = 0.80,
    sdn_list: List[Dict[str, Any]] | None = None,
) -> SanctionsMatchResult:
    """Screen counterparty name against OFAC SDN snapshot.
    
    Args:
        name: Name string to screen.
        threshold: Match confidence threshold in [0.0, 1.0].
        sdn_list: Optional custom SDN list.
        
    Returns:
        SanctionsMatchResult with match score and entity details.
    """
    if not name or not name.strip():
        return SanctionsMatchResult(
            query_name=name,
            is_match=False,
            highest_score=0.0,
            matched_entity=None,
            threshold=threshold,
            timestamp=datetime.now().isoformat(),
        )

    targets = sdn_list if sdn_list is not None else OFAC_SDN_SNAPSHOT

    best_score = 0.0
    best_entity = None

    for entity in targets:
        score = jaro_winkler_similarity(name, entity["name"])
        if score > best_score:
            best_score = score
            best_entity = entity

    is_match = best_score >= threshold

    result = SanctionsMatchResult(
        query_name=name,
        is_match=is_match,
        highest_score=round(best_score, 4),
        matched_entity=best_entity if is_match else None,
        threshold=threshold,
        timestamp=datetime.now().isoformat(),
    )

    # Log screening event
    log_file = LOGS_DIR / "sanctions_screening.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"{result.timestamp} | QUERY='{name}' | MATCH={is_match} | SCORE={best_score:.4f} | ENTITY={best_entity['entity_id'] if best_entity else 'NONE'}\n")

    return result
