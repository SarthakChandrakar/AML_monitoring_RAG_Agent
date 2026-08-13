"""Streamlit Human Annotation Tool for AMLFaith Benchmark.

Run: streamlit run eval/dataset/annotate.py
"""

import json
import sys
from pathlib import Path
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from retrieval.kb_store import KBStore

CANDIDATES_FILE = PROJECT_ROOT / "eval" / "dataset" / "candidates.jsonl"
GOLD_FILE = PROJECT_ROOT / "eval" / "dataset" / "amlfaith_gold.jsonl"

st.set_page_config(page_title="AMLFaith Annotation Tool", page_icon="🏷️", layout="wide")

st.title("🏷️ AMLFaith Gold Benchmark Annotation Tool")
st.caption("Human annotation workspace for ground-truth relevance, reference answers, and abstention judgments.")


@st.cache_resource
def load_kb():
    try:
        return KBStore()
    except Exception as e:
        st.error(f"Failed to load kb_store: {e}")
        return None


kb = load_kb()


def load_candidates():
    if not CANDIDATES_FILE.exists():
        return []
    items = []
    with open(CANDIDATES_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                items.append(json.loads(line.strip()))
    return items


candidates = load_candidates()

if not candidates:
    st.warning("No candidate queries found. Run `python eval/dataset/seed_candidates.py` first.")
    st.stop()

# Sidebar Query Selection
query_ids = [c["query_id"] for c in candidates]
selected_id = st.sidebar.selectbox("Select Candidate Query", query_ids)

item = next(c for c in candidates if c["query_id"] == selected_id)

st.subheader(f"Query ID: {item['query_id']}")

col1, col2 = st.columns(2)
query_text = col1.text_area("Query Text", item["query_text"])
query_type = col2.selectbox(
    "Query Type",
    ["typology_lookup", "threshold_rule", "transaction_triage", "multi_hop", "unanswerable"],
    index=["typology_lookup", "threshold_rule", "transaction_triage", "multi_hop", "unanswerable"].index(
        item.get("query_type", "typology_lookup")
    ),
)

col3, col4 = st.columns(2)
difficulty = col3.selectbox("Difficulty", ["easy", "medium", "hard"], index=["easy", "medium", "hard"].index(item.get("difficulty", "medium")))
answerable = col4.checkbox("Answerable from Corpus?", item.get("answerable", True))
expected_abstention = col4.checkbox("Expected Abstention?", item.get("expected_abstention", False))

reference_answer = st.text_area("Reference Gold Answer", item.get("reference_answer", ""))
notes = st.text_input("Annotator Notes", item.get("notes", ""))

st.markdown("---")
st.subheader("🔍 Ground-Truth Passage Selection (kb_store)")

gold_passage_ids = set(item.get("gold_passage_ids", []))

if kb and query_text:
    search_hits = kb.search_hybrid(query_text, top_k=8)
    st.markdown(f"**Top Search Candidates ({len(search_hits)} retrieved)**:")

    selected_passages = []
    for hit in search_hits:
        cid = hit["chunk_id"]
        is_checked = cid in gold_passage_ids
        checked = st.checkbox(
            f"[{hit['citation_string']}] (Score: {hit.get('rrf_score', 0):.4f}) — {hit['text'][:140]}…",
            value=is_checked,
            key=f"chk_{item['query_id']}_{cid}",
        )
        if checked:
            selected_passages.append(cid)
else:
        st.info("Enter query text to search kb_store for relevant gold passage candidates.")
        selected_passages = list(gold_passage_ids)

if st.button("💾 Save Gold Annotation", type="primary"):
    item["query_text"] = query_text
    item["query_type"] = query_type
    item["difficulty"] = difficulty
    item["gold_passage_ids"] = selected_passages
    item["reference_answer"] = reference_answer
    item["answerable"] = answerable
    item["expected_abstention"] = expected_abstention
    item["status"] = "VERIFIED"
    item["notes"] = notes

    # Save to gold file
    GOLD_FILE.parent.mkdir(parents=True, exist_ok=True)
    existing = {}
    if GOLD_FILE.exists():
        with open(GOLD_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    obj = json.loads(line.strip())
                    existing[obj["query_id"]] = obj

    existing[item["query_id"]] = item

    with open(GOLD_FILE, "w", encoding="utf-8") as f:
        for obj in sorted(existing.values(), key=lambda x: x["query_id"]):
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")

    st.success(f"Saved {item['query_id']} to {GOLD_FILE.name}!")
