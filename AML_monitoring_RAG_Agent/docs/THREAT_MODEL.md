# THREAT_MODEL.md — Knowledge-Base Poisoning & Supply-Chain Risk

## 1. Threat Overview & Vector Space Vulnerabilities

In retrieval-augmented AML intelligence systems, **Knowledge-Base Poisoning** represents a high-severity supply-chain security vulnerability.

Adversaries or compromised data sources can inject fabricated regulatory recommendations or altered thresholds (e.g., introducing a fake "FATF Recommendation 41" imposing an unauthorized $2,500 crypto limit). Because vector retrievers (`IndexFlatIP`) match dense semantic text embeddings rather than verifying cryptographic provenance, an unmitigated RAG system will retrieve, cite, and act upon adversarial claims as authoritative.

---

## 2. Experimental Verification (`poisoned_index.py`)

Our experimental evaluation (`eval/experiments/poisoned_index.py`) confirms that when fabricated regulatory chunks are present in an unverified vector index:
- **Poison Citation Rate**: Dense vector search retrieves fabricated chunks at top ranks whenever queries match the semantic domain.
- **Safety Isolation**: To prevent production contamination, synthetic poison chunks are tagged with `is_synthetic_poison = true`, stored strictly in `eval/experiments/poison_data.json`, and guarded by build-time CI assertions that fail if any poison chunk enters `kb_store`.

---

## 3. Required Enterprise Mitigations

1. **Source Allowlisting & Provenance Verification**: Every document ingested into `kb_store` must originate from an authenticated cryptographic source hash (e.g., SHA-256 hash matching published FATF PDF checksums).
2. **Chunk Provenance Hashing**: Compute immutable cryptographic hashes ($h_i = \text{SHA256}(\text{chunk\_text} || \text{metadata})$) upon chunking. Verify hashes prior to vector retrieval.
3. **Cross-Source Corroboration Requirement**: High-stakes compliance actions (e.g., SAR filings or account freezes) require regulatory claims to be corroborated by at least two independent authoritative sources.
