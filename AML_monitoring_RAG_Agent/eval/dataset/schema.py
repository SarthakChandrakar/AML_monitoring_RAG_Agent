"""Pydantic schema definition for AMLFaith benchmark items."""

from __future__ import annotations

from typing import List, Literal, Optional
from pydantic import BaseModel, Field


QueryType = Literal[
    "typology_lookup",
    "threshold_rule",
    "transaction_triage",
    "multi_hop",
    "unanswerable",
]

DifficultyLevel = Literal["easy", "medium", "hard"]


class QueryItem(BaseModel):
    query_id: str = Field(..., description="Unique identifier for the benchmark query")
    query_text: str = Field(..., description="The natural language question or prompt")
    query_type: QueryType = Field(..., description="Category of query")
    difficulty: DifficultyLevel = Field("medium", description="Perceived difficulty tier")
    gold_passage_ids: List[str] = Field(
        default_factory=list,
        description="IDs of ground-truth relevant regulatory chunks in kb_store",
    )
    reference_answer: str = Field(
        "", description="Human-authored reference gold answer"
    )
    answerable: bool = Field(
        True, description="True if query can be answered from regulatory corpus"
    )
    expected_abstention: bool = Field(
        False, description="True if agent should refuse to answer due to missing evidence"
    )
    status: Literal["UNVERIFIED", "VERIFIED", "REJECTED"] = Field(
        "UNVERIFIED", description="Annotation verification status"
    )
    notes: Optional[str] = Field(None, description="Annotator comments or context")
