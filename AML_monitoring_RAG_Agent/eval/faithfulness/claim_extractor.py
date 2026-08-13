"""Claim Extractor Module for Faithfulness Measurement Harness.

Decomposes narrative answers into atomic claims with citation tags.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class AtomicClaim:
    claim_id: int
    text: str
    citations: List[str]  # e.g., ["E1", "E2"]


def extract_claims(narrative: str) -> List[AtomicClaim]:
    """Decompose narrative answer into atomic claims, retaining citation tags."""
    if not narrative or not narrative.strip():
        return []

    # Clean headers and code blocks
    lines = narrative.strip().split("\n")
    cleaned_sentences: List[str] = []

    for line in lines:
        line = line.strip()
        if not line or line.startswith("=") or line.startswith("#") or line.startswith("-"):
            continue
        # Split line into sentences
        sentences = re.split(r"(?<=[.!?])\s+", line)
        for s in sentences:
            s_clean = s.strip()
            if len(s_clean) > 8:
                cleaned_sentences.append(s_clean)

    claims: List[AtomicClaim] = []
    for idx, stmt in enumerate(cleaned_sentences, start=1):
        # Extract citation markers like [E1], [E2], [FATF Recommendation 10]
        cite_matches = re.findall(r"\[([E\d,\s]+|FATF[^\]]+|Typology[^\]]+)\]", stmt)
        citations = []
        for match in cite_matches:
            for c in match.split(","):
                c_clean = c.strip()
                if c_clean:
                    citations.append(c_clean)

        claims.append(AtomicClaim(claim_id=idx, text=stmt, citations=citations))

    return claims
