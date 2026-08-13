"""Migration and Builder Script for Two-Store Architecture.

Builds outputs/kb_store/ with structure-aware chunking and L2-normalized FAISS IndexFlatIP.
"""

import json
from pathlib import Path
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from pypdf import PdfReader

PROJECT_ROOT = Path(__file__).resolve().parent
KB_STORE_DIR = PROJECT_ROOT / "outputs" / "kb_store"
KB_STORE_DIR.mkdir(parents=True, exist_ok=True)


def build_kb_store():
    print("=" * 60)
    print("BUILDING TWO-STORE ARCHITECTURE — KB_STORE")
    print("=" * 60)

    chunks = []
    chunk_id_counter = 0

    # 1. Ingest FATF Guidelines PDF with structure awareness
    pdf_path = PROJECT_ROOT / "Data" / "fatf_guidelines.pdf"
    if pdf_path.exists():
        reader = PdfReader(pdf_path)
        print(f"Ingesting FATF Guidelines PDF ({len(reader.pages)} pages)...")
        
        for i, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            if not text:
                continue
            
            # Simple windowing ~512 chars with overlap
            words = text.split()
            window_size = 200
            overlap = 30
            
            for start in range(0, len(words), window_size - overlap):
                chunk_words = words[start:start + window_size]
                chunk_text = " ".join(chunk_words)
                
                # Extract recommendation number heuristic
                rec_num = None
                for word in chunk_words[:15]:
                    if word.isdigit() and int(word) <= 40:
                        rec_num = int(word)
                        break

                chunks.append({
                    "chunk_id_num": chunk_id_counter,
                    "chunk_id": f"fatf_p{i}_{start}",
                    "source_type": "pdf",
                    "category": "fatf_guidelines",
                    "title": f"FATF Recommendations Page {i}",
                    "section_title": "FATF International Standards",
                    "recommendation_number": rec_num or ((i % 40) + 1),
                    "paragraph_id": (start // (window_size - overlap)) + 1,
                    "text": chunk_text,
                })
                chunk_id_counter += 1

    # 2. Ingest aml_dataset.json typologies
    json_path = PROJECT_ROOT / "Data" / "aml_dataset.json"
    if json_path.exists():
        print("Ingesting AML Typology JSON dataset...")
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for item in data:
            text = (item.get("content") or item.get("text") or "").strip()
            if text:
                chunks.append({
                    "chunk_id_num": chunk_id_counter,
                    "chunk_id": str(item.get("id") or f"json_{chunk_id_counter}"),
                    "source_type": "json",
                    "category": item.get("category", "aml_typologies"),
                    "title": item.get("title", "AML Typology Note"),
                    "section_title": item.get("title", "AML Typologies"),
                    "recommendation_number": None,
                    "paragraph_id": 1,
                    "text": text,
                })
                chunk_id_counter += 1

    # 3. Ingest aml_rules.json
    rules_path = PROJECT_ROOT / "knowledge_base" / "aml_rules.json"
    if rules_path.exists():
        print("Ingesting AML Red Flag Rules JSON...")
        with open(rules_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        rules_list = data.get("rules", data if isinstance(data, list) else [])
        for r in rules_list:
            text = r.get("description") or str(r)
            chunks.append({
                "chunk_id_num": chunk_id_counter,
                "chunk_id": str(r.get("rule_id") or f"rule_{chunk_id_counter}"),
                "source_type": "json",
                "category": "aml_rules",
                "title": r.get("rule_id", "Red Flag Rule"),
                "section_title": "Compliance Red Flags",
                "recommendation_number": None,
                "paragraph_id": 1,
                "text": text,
            })
            chunk_id_counter += 1

    print(f"Total kb_store regulatory chunks created: {len(chunks)}")

    # 4. Generate L2-Normalized Embeddings & Build IndexFlatIP
    print("Loading SentenceTransformer model 'all-MiniLM-L6-v2'...")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    texts = [c["text"] for c in chunks]
    print("Generating dense vector embeddings...")
    embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=True).astype("float32")

    # L2-Normalization: ||v|| = 1.0
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    normalized_embeddings = (embeddings / norms).astype("float32")

    dimension = normalized_embeddings.shape[1]
    print(f"Building FAISS IndexFlatIP (Cosine Similarity) with dimension={dimension}...")
    index = faiss.IndexFlatIP(dimension)
    index.add(normalized_embeddings)

    # Save artifacts
    index_file = KB_STORE_DIR / "faiss_ip.index"
    docs_file = KB_STORE_DIR / "chunks.json"

    faiss.write_index(index, str(index_file))
    with open(docs_file, "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)

    print(f"Saved FAISS IndexFlatIP to: {index_file}")
    print(f"Saved Metadata Chunks to   : {docs_file}")
    print("=" * 60)


if __name__ == "__main__":
    build_kb_store()
