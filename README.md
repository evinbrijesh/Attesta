# Attesta

> **Attested. Verified. Sealed.**
>
> Tamper-evident chain-of-custody ledger, AI forensic log auditor, and BSA Section 63(4) electronic evidence pipeline.

---

## Why Attesta?

Under India's **Bharatiya Sakshya Adhiniyam (BSA), Section 63(4)** (effective 1 July 2024, upheld by the Supreme Court in *Pune Bar Association v. Union of India*, May 2026), electronic evidence submitted in court requires a mandatory two-part statutory certificate:
- **Part A (Custodian's Declaration):** Discloses the file's origin and cryptographic **hash value**.
- **Part B (Expert's Certification):** Certifies technical integrity and custody continuity.

Today, advocates, police cyber cells, and forensic labs prepare these manually in Word/Excel—leading to missing hashes, timezone conflicts, broken custody chains, and excluded evidence.

**Attesta** automates this end-to-end while keeping cryptography strictly deterministic:
1. **Deterministic Intake & Hashing:** Computes `SHA-256` + `BLAKE3` at intake (idempotent by content hash).
2. **Immutable Hash-Chained Custody Log:** Every handoff is `Ed25519`-signed and linked to the previous event hash (`SQLite` append-only triggers).
3. **AI Audit Agent *(Code hashes & signs; LLM only parses, flags, and drafts)*:** Parses messy acquisition logs, flags custody gaps or UTC/IST conflicts, and drafts grounded Part A/B narratives citing verified event IDs and hashes.
4. **Human Expert Sign-Off & Section 63(4) PDF:** Exports the statutory certificate + tamper-evident `.zip` bundle.
5. **Zero-Trust Offline Verifier (`attesta-verify`):** Standalone open-source CLI that verifies any exported `.zip` bundle offline without trusting any server.

> **Disclaimer:** Attesta prepares the Section 63(4) certificate and cryptographic audit bundle for human expert review and sign-off. It does not replace legal counsel or judicial admissibility determinations.

---

## Documentation

- [Product Requirements Document (PRD)](docs/PRD.md) — Problem statement, dual-mode UX (`📱 Field Mobile` ⇄ `🖥️ Expert Desktop`), sponsor integrations, and evaluation benchmarks.
- [Technical Architecture](docs/ARCHITECTURE.md) — Cryptographic model, append-only SQLite triggers, `attesta-bundle-v1` format, and API endpoints.
- [Roadmap](docs/ROADMAP.md) — 10-day Hackathon Sprint (Nov 26 – Dec 6, 2026) and post-hackathon production roadmap.

---

## Repository Structure

```text
attesta/
├── apps/
│   └── api/             # FastAPI backend: crypto, append-only SQLite ledger, forensics, bundle export, tests
├── packages/
│   └── verify-coc/      # Standalone offline CLI verifier (`attesta-verify`)
├── fixtures/
│   └── logs/            # 5 synthetic forensic log formats (dd, ewfacquire, Autopsy, ExifTool, officer notes)
├── docs/                # PRD, Architecture, and Roadmap
└── .env.example
```

---

## Quickstart & Verification

```bash
# 1. Run Backend API & Core Tests (25/25 passing, incl. 100 byte-flip tamper & forensics tests)
cd apps/api
uv sync
uv run pytest -v

# 2. Start API Server
uv run uvicorn app.main:app --reload   # http://localhost:8000/api/health

# 3. Verify an Exported Bundle Offline
cd ../../packages/verify-coc
uv sync
uv run attesta-verify path/to/bundle.zip
```
