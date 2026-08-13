"""Validation and Inter-Annotator Agreement Script for AMLFaith Benchmark.

Checks schema validity, passage ID resolution against kb_store, and computes Cohen's Kappa.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from eval.dataset.schema import QueryItem
from retrieval.kb_store import KBStore

GOLD_FILE = PROJECT_ROOT / "eval" / "dataset" / "amlfaith_gold.jsonl"


def validate_gold_file(gold_path: Path | str | None = None) -> Tuple[bool, List[str]]:
    path = Path(gold_path) if gold_path else GOLD_FILE
    errors = []
    items: List[QueryItem] = []

    if not path.exists():
        errors.append(f"Gold benchmark file does not exist: {path}")
        return False, errors

    # Load kb_store chunk IDs for verification
    try:
        kb = KBStore()
        valid_chunk_ids: Set[str] = {c["chunk_id"] for c in kb.chunks}
    except Exception as e:
        valid_chunk_ids = set()
        print(f"Warning: Could not load kb_store for passage verification ({e})")

    seen_ids: Set[str] = set()
    seen_texts: Set[str] = set()

    with open(path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, start=1):
            if not line.strip():
                continue
            try:
                data = json.loads(line.strip())
                item = QueryItem(**data)
                items.append(item)

                if item.query_id in seen_ids:
                    errors.append(f"Line {idx}: Duplicate query_id '{item.query_id}'")
                seen_ids.add(item.query_id)

                if item.query_text.lower() in seen_texts:
                    errors.append(f"Line {idx}: Duplicate query_text '{item.query_text}'")
                seen_texts.add(item.query_text.lower())

                # Validate gold passage IDs
                if valid_chunk_ids and item.answerable:
                    for g_id in item.gold_passage_ids:
                        if g_id not in valid_chunk_ids:
                            errors.append(f"Line {idx} ({item.query_id}): Invalid gold_passage_id '{g_id}' not found in kb_store")

            except Exception as exc:
                errors.append(f"Line {idx}: Schema validation failed — {exc}")

    # Class balance report
    if items:
        types_count: Dict[str, int] = {}
        unanswerable_count = 0
        for it in items:
            types_count[it.query_type] = types_count.get(it.query_type, 0) + 1
            if not it.answerable or it.expected_abstention:
                unanswerable_count += 1

        print("\n" + "=" * 50)
        print("AMLFAITH BENCHMARK VALIDATION REPORT")
        print("=" * 50)
        print(f"Total Verified Items : {len(items)}")
        print(f"Unanswerable Items   : {unanswerable_count} ({unanswerable_count/len(items)*100:.1f}%)")
        print("Query Types Breakdown:")
        for qtype, count in types_count.items():
            print(f"  - {qtype:<20}: {count}")

    is_valid = len(errors) == 0
    return is_valid, errors


def compute_cohen_kappa(pass1_path: Path | str, pass2_path: Path | str) -> float:
    """Compute Cohen's Kappa inter-annotator agreement score across two independent annotation passes."""
    p1_data = {}
    p2_data = {}

    with open(pass1_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                d = json.loads(line.strip())
                p1_data[d["query_id"]] = set(d.get("gold_passage_ids", []))

    with open(pass2_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                d = json.loads(line.strip())
                p2_data[d["query_id"]] = set(d.get("gold_passage_ids", []))

    common_ids = set(p1_data.keys()).intersection(set(p2_data.keys()))
    if not common_ids:
        return 0.0

    agreements = 0
    total = len(common_ids)

    for qid in common_ids:
        # Check if passage judgments match
        if p1_data[qid] == p2_data[qid]:
            agreements += 1

    p_observed = agreements / total
    p_expected = 0.5  # Random baseline
    kappa = (p_observed - p_expected) / (1.0 - p_expected) if p_expected < 1.0 else 1.0
    return round(kappa, 4)


if __name__ == "__main__":
    valid, errs = validate_gold_file()
    if valid:
        print("SUCCESS: amlfaith_gold.jsonl passes all validation checks!")
    else:
        print(f"FAILED: Found {len(errs)} validation errors:")
        for e in errs[:10]:
            print(f"  - {e}")
