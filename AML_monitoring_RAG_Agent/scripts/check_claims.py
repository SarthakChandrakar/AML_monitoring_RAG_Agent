"""CI Verification Script: Fails build if documentation contains unbacked quantitative claims."""

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCS_TO_CHECK = [PROJECT_ROOT / "README.md", PROJECT_ROOT / "PAPER.md"]
RESULTS_DIR = PROJECT_ROOT / "results"


def check_claims():
    print("=" * 60)
    print("CI CLAIM VERIFICATION CHECK")
    print("=" * 60)

    # 1. Collect all valid metrics from results/
    valid_numbers = set()
    if RESULTS_DIR.exists():
        for res_file in RESULTS_DIR.glob("*.json"):
            text = res_file.read_text(encoding="utf-8")
            nums = re.findall(r"\b0\.\d{3,4}\b", text)
            valid_numbers.update(nums)

    print(f"Discovered {len(valid_numbers)} validated metric numbers in results/")

    unbacked_claims = []
    # Metric pattern e.g., Precision@5 = 0.9521 or Faithfulness: 0.95
    metric_pattern = re.compile(r"(?:Precision|Recall|Faithfulness|Groundedness|MRR|Hit Rate)\s*[@:]?\s*(?:=\s*)?(0\.\d{3,4})", re.IGNORECASE)

    for doc_path in DOCS_TO_CHECK:
        if not doc_path.exists():
            continue
        content = doc_path.read_text(encoding="utf-8")
        matches = metric_pattern.findall(content)
        for num in matches:
            if num not in valid_numbers:
                unbacked_claims.append((doc_path.name, num))

    if unbacked_claims:
        print(f"\nFAILED: Discovered {len(unbacked_claims)} unbacked quantitative metrics in docs:")
        for doc, num in unbacked_claims:
            print(f"  - {doc}: Unbacked metric value '{num}' not found in results/")
        print("\nFix: Every metric in documentation must cite a file in results/ or be written as TBD_RUN_REQUIRED.")
        sys.exit(1)
    else:
        print("SUCCESS: All quantitative metrics in documentation are backed by results/ artifacts!")
        print("=" * 60)


if __name__ == "__main__":
    check_claims()
