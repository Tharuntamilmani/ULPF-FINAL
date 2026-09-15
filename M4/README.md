# ULPF Module M4 — Enrichment + Provenance + Integrity

Module M4 is a standalone, production-grade security component in the Universal Log Processing Framework (ULPF).
It is responsible for:
1. **Contextual & Semantic Enrichment** (Assets, GeoIP, ASN, Threat Intelligence, Custom Rules)
2. **Deterministic Provenance Tracking** (Lineage, confidence scoring, auditability)
3. **Cryptographic Integrity** (Deterministic RFC 8785 canonicalization & SHA-256 integrity verification)

M4 operates independently of modules M1–M3, M5, and M6, enforcing explicit contracts, tenant boundaries, and failure isolation.
