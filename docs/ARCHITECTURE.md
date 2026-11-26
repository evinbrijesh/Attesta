# Attesta — Technical Architecture

## 1. Design Principle: Deterministic Core, Constrained AI

Legal evidence systems cannot rely on probabilistic LLM outputs for integrity guarantees. Attesta enforces a strict separation of concerns:

- **Deterministic Layer (Python / Cryptography / SQLite):** All file hashing, canonical JSON serialization, hash-chaining, `Ed25519` signing, database immutability, and offline verification are 100% deterministic code.
- **AI Agent Layer (Ollama / Gemini Flash + Pydantic v2):** Strictly scoped to *reading* messy logs, *flagging* anomalies, and *drafting* human-readable Section 63(4) text grounded in verified event/hash citations.

---

## 2. End-to-End System Architecture

```mermaid
flowchart TD
    subgraph INTAKE ["📱 Field Mobile / Desktop Intake"]
        U[Custodian / Officer] -->|"1. Client WebCrypto SHA-256"| W[React PWA]
        W -->|"2. Multipart Upload"| API[FastAPI Backend]
    end

    subgraph CORE ["🔒 Deterministic Custody Core"]
        API -->|"3. SHA-256 + BLAKE3 (Idempotent)"| V[(Evidence Vault)]
        API -->|"4. Append-Only + Ed25519 Sign"| DB[(SQLite WAL + Triggers)]
    end

    subgraph AGENT ["🤖 AI Forensic Audit Agent"]
        DB --> P[Log Parser: 5 Formats]
        P --> A[Anomaly Auditor: Gaps / UTC-IST / Hash]
        OLO[Olostep: BSA S.63 Reference] --> D[Grounded Part A/B Drafter]
        A --> D
    end

    subgraph APPROVAL ["⚡ Automation & Human-in-the-Loop"]
        D -->|"Optional Webhook"| N8N["n8n Workflow (Telegram Alert)"]
        D -->|"Desktop Preview"| EXP[Human Expert Sign-Off]
    end

    subgraph EXPORT ["📦 Court-Ready Output & Zero-Trust Verify"]
        EXP -->|"Generate"| PDF[Section 63(4) Part A + B PDF]
        EXP -->|"Export"| ZIP[Tamper-Evident .zip Bundle]
        ZIP --> CLI["attesta-verify (Offline CLI)"]
    end
```

---

## 3. Cryptographic & Data Model

### 3.1 Dual Hashing at Intake
Every ingested file is hashed using two independent algorithms:
- **`SHA-256`**: Required standard for BSA Section 63(4) Part A disclosure.
- **`BLAKE3`**: High-throughput modern hash for fast verification of large video/disk files.

Idempotency is enforced at the database level via `UNIQUE(case_id, sha256, blake3)` on `evidence_assets`.

### 3.2 Append-Only Hash Chain (`custody_events`)
Each custody event $E_n$ (starting at `seq = 0` for `INGEST`) computes:

$$\text{event\_hash}_n = \text{SHA-256}\big(\text{prev\_hash}_n \;\|\; \text{":"} \;\|\; \text{canonical\_json}(\text{payload}_n)\big)$$

where $\text{prev\_hash}_0 = \text{"0"}^{64}$ (`GENESIS_HASH`) and $\text{prev\_hash}_n = \text{event\_hash}_{n-1}$ for $n > 0$.

Each `event_hash` is signed with an `Ed25519` private key, storing `(signer_public_key, signature)` alongside the event.

### 3.3 Database-Enforced Immutability
SQLite runs in `WAL` mode with `BEFORE UPDATE` and `BEFORE DELETE` triggers on `custody_events` that execute `RAISE(ABORT, ...)`—guaranteeing append-only semantics even against accidental application-level mutations.

---

## 4. Offline Bundle Format (`attesta-bundle-v1`)

Exported `.zip` archives are self-contained and require **zero network access or server trust** to verify:

```text
<asset_id>_bundle.zip
├── evidence/<filename>      # Raw original evidence bytes
├── custody_log.jsonl        # Ordered JSONL of all custody_events
├── manifest.json            # Case metadata, asset digests, head_event_hash
├── certificate_s63.pdf      # (Optional; added when signed via /sign-s63, Day 7) BSA S.63(4) PDF
└── sha256sums.txt           # SHA-256 checksums of all bundle entries
```

The standalone `attesta-verify` CLI (`packages/verify-coc`) checks:
1. Presence of all required bundle files.
2. `SHA-256` and `BLAKE3` of `evidence/<filename>` against `manifest.json`.
3. Every entry in `sha256sums.txt`.
4. Strict `seq` continuity (`0, 1, ..., N-1`) and `prev_hash` linkage from `GENESIS_HASH`.
5. Recomputed `event_hash` for every event payload.
6. Valid `Ed25519` signature on every event.
7. Tail `event_hash == manifest.head_event_hash`.

---

## 5. API Endpoints

| Method | Path | Purpose | Status |
|---|---|---|---|
| `GET` | `/api/health` | Liveness check | Implemented |
| `GET` | `/api/cases` | List all cases | Implemented |
| `POST` | `/api/cases` | Create a new case | Implemented |
| `GET` | `/api/cases/{case_id}/assets` | List sealed evidence assets for a case | Implemented |
| `POST` | `/api/cases/{case_id}/ingest` | Idempotent evidence upload + `INGEST` event | Implemented |
| `GET` | `/api/assets/{asset_id}/events` | List ordered hash-chained custody events | Implemented |
| `POST` | `/api/assets/{asset_id}/handoff` | Append `Ed25519`-signed custody handoff | Implemented |
| `GET` | `/api/assets/{asset_id}/verify` | Full chain & disk integrity check | Implemented |
| `GET` | `/api/assets/{asset_id}/bundle` | Export verified `.zip` bundle (embeds signed PDF) | Implemented |
| `GET` | `/api/assets/{asset_id}/forensics` | EXIF metadata & TRACE advisory flags (`advisory_only: true`) | Implemented |
| `POST` | `/api/assets/{asset_id}/audit` | Run AI log parser, anomaly audit & Part A/B draft (+ n8n) | Implemented |
| `GET` | `/api/legal/section63` | BSA Section 63(4) reference (Olostep live + local cache) | Implemented |
| `POST` | `/api/assets/{asset_id}/sign-s63` | Human expert sign-off & Section 63(4) PDF generation | Implemented |
| `GET` | `/api/assets/{asset_id}/certificate.pdf` | Download signed Section 63(4) Part A + B PDF | Implemented |

---

## 6. Runtime Ports & Deployment Topology

- **Docker Compose (`docker-compose.yml`, run from repo root):**
  - `web` (`nginx:1.27-alpine`): Exposed on host **`http://localhost:5174`** (`5174:80`); serves the built Vite SPA and proxies `/api/` to `http://api:8000/api/` (`client_max_body_size 100M`).
  - `api` (`python:3.13-slim` + `uv`): Exposed on host **`http://localhost:8001`** (`8001:8000`); persists SQLite & evidence files to the `attesta_data` volume (`/app/data`).
- **Local Dev Mode:** Vite dev server runs on **`http://localhost:5173`** (`apps/web/vite.config.ts`) and proxies `/api` to Uvicorn on **`http://127.0.0.1:8000`**.
