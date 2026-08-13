"""Cryptographic Append-Only Hash-Chained Audit Logger.

Ensures immutable, tamper-evident audit logging for all compliance query and triage events.
"""

from __future__ import annotations

import hashlib
import json

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
AUDIT_LOG_FILE = PROJECT_ROOT / "outputs" / "audit_log.jsonl"
AUDIT_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def get_last_entry_hash(log_path: Path | str | None = None) -> str:
    path = Path(log_path) if log_path else AUDIT_LOG_FILE
    if not path.exists() or path.stat().st_size == 0:
        return GENESIS_HASH

    last_line = ""
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                last_line = line.strip()

    if not last_line:
        return GENESIS_HASH

    try:
        data = json.loads(last_line)
        return data.get("entry_hash", GENESIS_HASH)
    except Exception:
        return GENESIS_HASH


def log_audit_event(
    query: str,
    retrieved_chunk_ids: List[str],
    prompt_str: str,
    output_str: str,
    analyst_id: str = "ANALYST-OFFICER-01",
    action_taken: str = "SEARCH_AND_ANALYZE",
    rules_version: str = "1.0.0",
    model_name: str = "all-MiniLM-L6-v2",
    log_path: Path | str | None = None,
) -> Dict[str, Any]:
    path = Path(log_path) if log_path else AUDIT_LOG_FILE
    prev_hash = get_last_entry_hash(path)
    timestamp = datetime.now().isoformat()

    prompt_hash = _sha256(prompt_str)
    output_hash = _sha256(output_str)
    chunks_str = ",".join(sorted(retrieved_chunk_ids))

    # Cryptographic block header: SHA256(prev_hash || timestamp || query || prompt_hash || output_hash || chunks)
    block_contents = f"{prev_hash}|{timestamp}|{query}|{prompt_hash}|{output_hash}|{chunks_str}"
    entry_hash = _sha256(block_contents)

    entry = {
        "timestamp": timestamp,
        "prev_hash": prev_hash,
        "query": query,
        "retrieved_chunk_ids": retrieved_chunk_ids,
        "rules_version": rules_version,
        "model_name": model_name,
        "prompt_hash": prompt_hash,
        "output_hash": output_hash,
        "analyst_id": analyst_id,
        "action_taken": action_taken,
        "entry_hash": entry_hash,
    }

    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return entry


def verify_chain(log_path: Path | str | None = None) -> Tuple[bool, List[str]]:
    """Verify cryptographic chain integrity of audit log."""
    path = Path(log_path) if log_path else AUDIT_LOG_FILE
    errors = []

    if not path.exists() or path.stat().st_size == 0:
        return True, []

    expected_prev = GENESIS_HASH
    line_num = 0

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            line_num += 1
            try:
                entry = json.loads(line.strip())
                prev = entry.get("prev_hash", "")
                e_hash = entry.get("entry_hash", "")
                timestamp = entry.get("timestamp", "")
                query = entry.get("query", "")
                p_hash = entry.get("prompt_hash", "")
                o_hash = entry.get("output_hash", "")
                chunks_str = ",".join(sorted(entry.get("retrieved_chunk_ids", [])))

                if prev != expected_prev:
                    errors.append(f"Line {line_num}: Prev hash mismatch! Expected {expected_prev[:12]}…, got {prev[:12]}…")

                recomputed_block = f"{prev}|{timestamp}|{query}|{p_hash}|{o_hash}|{chunks_str}"
                recomputed_hash = _sha256(recomputed_block)

                if recomputed_hash != e_hash:
                    errors.append(f"Line {line_num}: TAMPERING DETECTED! Entry hash mismatch (Expected {recomputed_hash[:12]}…, stored {e_hash[:12]}…)")

                expected_prev = e_hash

            except Exception as exc:
                errors.append(f"Line {line_num}: JSON decode failure — {exc}")

    return len(errors) == 0, errors
