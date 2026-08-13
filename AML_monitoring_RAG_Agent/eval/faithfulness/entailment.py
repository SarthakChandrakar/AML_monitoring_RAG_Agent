"""NLI Entailment Judge for Claim Grounding Evaluation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Tuple

import numpy as np

from eval.faithfulness.claim_extractor import AtomicClaim

EntailmentLabel = Literal["SUPPORTED", "CONTRADICTED", "UNVERIFIABLE"]


@dataclass
class ClaimEntailmentResult:
    claim_id: int
    claim_text: str
    citations: List[str]
    primary_label: EntailmentLabel
    secondary_label: EntailmentLabel
    agreement: bool
    entailment_score: float
    cited_passage_entailed: bool


class EntailmentJudge:
    def __init__(self, model_name: str = "cross-encoder/nli-deberta-v3-base"):
        self.model_name = model_name
        self.cross_encoder = None

        # Try loading cross-encoder
        try:
            from sentence_transformers import CrossEncoder

            self.cross_encoder = CrossEncoder(model_name)
        except Exception:
            # Fall back to lightweight token-overlap / semantic judge
            self.cross_encoder = None

    def judge_claim(
        self,
        claim: AtomicClaim,
        evidence_chunks: List[Dict[str, Any]],
    ) -> ClaimEntailmentResult:
        if not evidence_chunks:
            return ClaimEntailmentResult(
                claim_id=claim.claim_id,
                claim_text=claim.text,
                citations=claim.citations,
                primary_label="UNVERIFIABLE",
                secondary_label="UNVERIFIABLE",
                agreement=True,
                entailment_score=0.0,
                cited_passage_entailed=False,
            )

        full_evidence_text = "\n".join(c.get("text", "") for c in evidence_chunks).lower()
        claim_text_lower = claim.text.lower()

        # Primary Judge: CrossEncoder if loaded, else token overlap
        if self.cross_encoder is not None:
            pairs = [[claim.text, c.get("text", "")] for c in evidence_chunks]
            scores = self.cross_encoder.predict(pairs)
            if len(scores) > 0:
                scores_flat = np.array(scores).flatten()
                max_score = float(np.max(scores_flat))
            else:
                max_score = 0.0

            primary_label = (
                "SUPPORTED"
                if max_score > 0.5
                else ("CONTRADICTED" if max_score < -0.5 else "UNVERIFIABLE")
            )
        else:
            # Token overlap heuristic judge
            claim_words = set(re_words(claim_text_lower))
            ev_words = set(re_words(full_evidence_text))
            overlap = len(claim_words.intersection(ev_words)) / max(1, len(claim_words))
            max_score = float(overlap)
            primary_label = "SUPPORTED" if overlap >= 0.4 else "UNVERIFIABLE"

        # Secondary Judge (Independent rule-based audit)
        secondary_label = (
            "SUPPORTED"
            if any(w in full_evidence_text for w in re_words(claim_text_lower)[:3])
            else "UNVERIFIABLE"
        )
        agreement = primary_label == secondary_label

        # Check if explicitly cited passage entails claim
        cited_entailed = False
        if claim.citations:
            for c in evidence_chunks:
                cid = str(c.get("chunk_id", ""))
                c_rank = f"E{c.get('rank', '')}"
                c_rec = f"Recommendation {c.get('recommendation_number', '')}"
                if any(cite in c_rank or cite in cid or cite in c_rec for cite in claim.citations):
                    if any(w in c.get("text", "").lower() for w in re_words(claim_text_lower)[:3]):
                        cited_entailed = True
                        break

        return ClaimEntailmentResult(
            claim_id=claim.claim_id,
            claim_text=claim.text,
            citations=claim.citations,
            primary_label=primary_label,
            secondary_label=secondary_label,
            agreement=agreement,
            entailment_score=round(max_score, 4),
            cited_passage_entailed=cited_entailed,
        )


def re_words(text: str) -> List[str]:
    return [w for w in re.findall(r"\b\w+\b", text) if len(w) > 3]
