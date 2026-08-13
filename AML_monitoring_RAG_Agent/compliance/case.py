"""Alert Lifecycle State Machine.

Enforces valid compliance workflow transitions:
NEW -> TRIAGED -> ESCALATED -> {SAR_FILED, CLOSED_FALSE_POSITIVE, CLOSED_NO_ACTION}.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Literal, Optional, Tuple

from compliance.audit_log import log_audit_event

CaseState = Literal[
    "NEW",
    "TRIAGED",
    "ESCALATED",
    "SAR_FILED",
    "CLOSED_FALSE_POSITIVE",
    "CLOSED_NO_ACTION",
]

ALLOWED_TRANSITIONS = {
    "NEW": ["TRIAGED", "CLOSED_NO_ACTION"],
    "TRIAGED": ["ESCALATED", "CLOSED_FALSE_POSITIVE", "CLOSED_NO_ACTION"],
    "ESCALATED": ["SAR_FILED", "CLOSED_FALSE_POSITIVE", "CLOSED_NO_ACTION"],
    "SAR_FILED": [],
    "CLOSED_FALSE_POSITIVE": [],
    "CLOSED_NO_ACTION": [],
}


@dataclass
class AlertCase:
    case_id: str
    transaction_id: str
    current_state: CaseState = "NEW"
    assigned_analyst: str = "ANALYST-OFFICER-01"
    history: List[Tuple[str, str, str]] = None

    def __post_init__(self):
        if self.history is None:
            self.history = [(datetime.now().isoformat(), "NEW", "Case initialized.")]

    def transition_to(
        self,
        new_state: CaseState,
        analyst_id: str,
        reason: str,
    ) -> Tuple[bool, str]:
        """Transition case state if valid, and log transition to audit chain."""
        allowed = ALLOWED_TRANSITIONS.get(self.current_state, [])
        if new_state not in allowed:
            err = f"Invalid transition: Cannot move case {self.case_id} from {self.current_state} to {new_state}. Allowed: {allowed}"
            return False, err

        prev = self.current_state
        self.current_state = new_state
        self.assigned_analyst = analyst_id
        timestamp = datetime.now().isoformat()
        
        self.history.append((timestamp, new_state, reason))

        # Log transition event to cryptographic audit log
        log_audit_event(
            query=f"Case Transition {self.case_id}: {prev} -> {new_state}",
            retrieved_chunk_ids=[],
            prompt_str=f"Transition reason: {reason}",
            output_str=f"State: {new_state}",
            analyst_id=analyst_id,
            action_taken=f"TRANSITION_{prev}_TO_{new_state}",
        )

        return True, f"Successfully transitioned case {self.case_id} to {new_state}."
