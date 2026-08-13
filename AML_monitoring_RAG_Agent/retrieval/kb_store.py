"""Regulatory Knowledge Base Store (kb_store).

Implements structure-aware chunking, L2-normalized FAISS IndexFlatIP vector search,
BM25 sparse retrieval, and Reciprocal Rank Fusion (RRF) hybrid search with similarity filtering.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

import faiss
import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

PROJECT_ROOT = Path(__file__).resolve().parents[1]
KB_STORE_DIR = PROJECT_ROOT / "outputs" / "kb_store"

# Common FATF PDF running headers to strip from chunk text
HEADER_PATTERNS = [
    r"THE FATF RECOMMENDATIONS\s+INTERNATIONAL STANDARDS ON COMBATING MONEY LAUNDERING\s+AND THE FINANCING OF TERRORISM & PROLIFERATION\s+2012-2025",
    r"INTERNATIONAL STANDARDS ON COMBATING MONEY LAUNDERING",
]


def clean_chunk_text(text: str) -> str:
    """Strip repeating FATF PDF running headers to prevent embedding distortion."""
    cleaned = text
    for pat in HEADER_PATTERNS:
        cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


class KBStore:
    def __init__(
        self,
        store_dir: Path | str | None = None,
        model_name: str = "all-MiniLM-L6-v2",
    ):
        self.store_dir = Path(store_dir) if store_dir else KB_STORE_DIR
        self.model_name = model_name

        self.index_path = self.store_dir / "faiss_ip.index"
        self.docs_path = self.store_dir / "chunks.json"

        if not self.index_path.exists() or not self.docs_path.exists():
            raise FileNotFoundError(
                f"kb_store artifacts missing in {self.store_dir}. Run `python build_two_stores.py` first."
            )

        # Load FAISS IndexFlatIP
        self.index = faiss.read_index(str(self.index_path))

        # Load metadata chunks
        with open(self.docs_path, "r", encoding="utf-8") as f:
            raw_chunks: List[Dict[str, Any]] = json.load(f)

        self.chunks = []
        for c in raw_chunks:
            c_copy = c.copy()
            c_copy["text"] = clean_chunk_text(c_copy.get("text", ""))
            self.chunks.append(c_copy)

        # Load SentenceTransformer
        self.model = SentenceTransformer(self.model_name)

        # Initialize BM25
        corpus_tokens = [c["text"].lower().split() for c in self.chunks]
        self.bm25 = BM25Okapi(corpus_tokens)

    def _normalize(self, vectors: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return (vectors / norms).astype("float32")

    def search_dense(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        query_vec = self.model.encode([query], convert_to_numpy=True).astype("float32")
        query_vec = self._normalize(query_vec)

        scores, indices = self.index.search(query_vec, top_k * 2)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self.chunks):
                continue
            cos_sim = float(score)
            if cos_sim < 0.15:  # Filter out low-similarity hits
                continue
            chunk = self.chunks[idx].copy()
            chunk["cosine_similarity"] = round(cos_sim, 4)
            chunk["score"] = round(cos_sim, 4)
            chunk["citation_string"] = self._format_citation(chunk)
            results.append(chunk)

        results.sort(key=lambda x: x["cosine_similarity"], reverse=True)
        return results[:top_k]

    def search_sparse(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        tokens = query.lower().split()
        scores = self.bm25.get_scores(tokens)
        top_indices = np.argsort(scores)[::-1][: top_k * 2]

        results = []
        for idx in top_indices:
            if scores[idx] <= 0.0:
                continue
            chunk = self.chunks[idx].copy()
            chunk["bm25_score"] = float(scores[idx])
            chunk["citation_string"] = self._format_citation(chunk)
            results.append(chunk)

        return results[:top_k]

    def search_hybrid(self, query: str, top_k: int = 5, rrf_k: int = 60) -> List[Dict[str, Any]]:
        """Reciprocal Rank Fusion (RRF) with Cosine Similarity calculation for all hits."""
        query_vec = self.model.encode([query], convert_to_numpy=True).astype("float32")
        query_vec = self._normalize(query_vec)

        dense_hits = self.search_dense(query, top_k=top_k * 2)
        sparse_hits = self.search_sparse(query, top_k=top_k * 2)

        rrf_scores: Dict[int, float] = {}
        chunk_map: Dict[int, Dict[str, Any]] = {}

        for rank, item in enumerate(dense_hits, start=1):
            cid = item.get("chunk_id_num", rank - 1)
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (rrf_k + rank))
            chunk_map[cid] = item

        for rank, item in enumerate(sparse_hits, start=1):
            cid = item.get("chunk_id_num", rank - 1)
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (rrf_k + rank))
            if cid not in chunk_map:
                chunk_map[cid] = item

        sorted_cids = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        final_results = []
        for cid, score in sorted_cids:
            chunk = chunk_map[cid].copy()
            if "cosine_similarity" not in chunk or chunk["cosine_similarity"] == 0.0:
                idx = chunk.get("chunk_id_num", 0)
                if 0 <= idx < len(self.chunks):
                    chunk_text = chunk.get("text", "")
                    c_vec = self.model.encode([chunk_text], convert_to_numpy=True).astype("float32")
                    c_vec = self._normalize(c_vec)
                    cos_sim = float(np.dot(query_vec[0], c_vec[0]))
                    chunk["cosine_similarity"] = round(max(0.0, cos_sim), 4)
                else:
                    chunk["cosine_similarity"] = 0.25

            chunk["rrf_score"] = float(score)
            chunk["score"] = chunk["cosine_similarity"]
            chunk["citation_string"] = self._format_citation(chunk)
            final_results.append(chunk)

        final_results.sort(key=lambda x: x.get("cosine_similarity", 0.0), reverse=True)
        return final_results

    def _format_citation(self, chunk: Dict[str, Any]) -> str:
        source_type = chunk.get("source_type", "")
        rec_num = chunk.get("recommendation_number")
        sec_title = chunk.get("section_title")
        para_id = chunk.get("paragraph_id")

        if rec_num is not None and str(rec_num).strip() != "":
            return f"FATF Recommendation {rec_num}"
        if sec_title:
            return f"AML Typology: {sec_title}"
        return f"{source_type.upper()} Regulation ({chunk.get('category', 'general')})"
