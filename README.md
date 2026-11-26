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
1. **Deterministic Intake & Hashing:** Computes `SHA-256` + `BLAKE3` at intake (plus client-side WebCrypto `SHA-256` on mobile before upload).
2. **Immutable Hash-Chained Custody Log:** Every handoff is `Ed25519`-signed and linked to the previous event hash (`SQLite` append-only triggers).
3. **AI Audit Agent *(Code hashes & signs; LLM only parses, flags, and drafts)*:** Parses 5 forensic log formats, flags custody gaps or UTC/IST conflicts, and drafts grounded Part A/B narratives citing verified event IDs and hashes.
4. **Human Expert Sign-Off & Section 63(4) PDF:** Exports the statutory certificate + tamper-evident `.zip` bundle.
5. **Zero-Trust Offline Verifier (`attesta-verify`):** Standalone open-source CLI that verifies any exported `.zip` bundle offline without trusting any server.

> **Disclaimer:** Attesta prepares the Section 63(4) certificate and cryptographic audit bundle for human expert review and sign-off. It does not replace legal counsel or judicial admissibility determinations.

---

## Measured Benchmarks

| Metric | Observed Result | Source |
|---|---|---|
| Single-byte-flip tamper detection | **100 / 100 caught (100.0%)** | [docs/BENCHMARKS.md](docs/BENCHMARKS.md) |
| Synthetic chain-break detection | **50 / 50 caught (100.0%)** | [docs/BENCHMARKS.md](docs/BENCHMARKS.md) |
| Clean-chain false-flag rate | **0 / 50 (0.0%)** | [docs/BENCHMARKS.md](docs/BENCHMARKS.md) |
| Ingest idempotency | **20 / 20 hits (100.0%)** | [docs/BENCHMARKS.md](docs/BENCHMARKS.md) |
| Forensic log parse accuracy | **5 / 5 formats (100.0%)** | [docs/BENCHMARKS.md](docs/BENCHMARKS.md) |
| End-to-end deterministic latency | **88.81 ms** | [docs/BENCHMARKS.md](docs/BENCHMARKS.md) |

---

## Documentation

- [Product Requirements Document (PRD)](docs/PRD.md)
- [Technical Architecture](docs/ARCHITECTURE.md)
- [Benchmarks Report](docs/BENCHMARKS.md)
- [Roadmap](docs/ROADMAP.md)

---

## Repository Structure

```text
attesta/
├── apps/
│   ├── api/             # FastAPI backend: crypto, SQLite ledger, forensics, AI agent, S.63 PDF, tests
│   └── web/             # React + Vite + Tailwind PWA (Field Mobile ⇄ Expert Desktop)
├── packages/
│   └── verify-coc/      # Standalone offline CLI verifier (`attesta-verify`)
├── fixtures/
│   └── logs/            # 5 synthetic forensic log formats (dd, ewfacquire, Autopsy, ExifTool, officer notes)
├── docs/                # PRD, Architecture, Benchmarks, and Roadmap
├── docker-compose.yml
└── .env.example
```

---

## Quickstart

### Option 1: Docker (1 Command, from repo root)
```bash
cp .env.example .env   # optional: add GEMINI_API_KEY, OLOSTEP_API_KEY, N8N_WEBHOOK_URL
docker compose up --build
# Web PWA: http://localhost:5174  |  API: http://localhost:8001/api/health
```

### Option 2: Local Dev & Tests
```bash
# 1. Run Backend API & Core Tests (31/31 passing)
cd apps/api
uv sync
uv run pytest -v
uv run uvicorn app.main:app --reload   # http://localhost:8000/api/health

# 2. Start Adaptive Mobile + Desktop PWA (in a second terminal)
cd apps/web
npm install
npm run dev                            # http://localhost:5173

# 3. Verify an Exported Bundle Offline
cd packages/verify-coc
uv sync
uv run attesta-verify path/to/bundle.zip
```
