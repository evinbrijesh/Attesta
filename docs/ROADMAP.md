# Attesta — Build Roadmap (Hackathon & Post-Hackathon)

## Part 1: 10-Day Hackathon Sprint (Nov 26 – Dec 6, 2026)

| Dates | Milestone | Deliverables & Done Criteria | Status |
|---|---|---|---|
| **Nov 26 (Day 1)** | **Core Crypto, Ledger & Offline CLI** | Public SSH repo, SQLite WAL append-only schema + triggers, `SHA-256`/`BLAKE3`, `Ed25519` signing, `.zip` bundle export, `attesta-verify` CLI, **20/20 `pytest` tests passing** (incl. 100 byte-flip tests). | **DONE** |
| **Nov 27 (Day 2)** | **Metadata & TRACE Forensics Module** | EXIF/file metadata extractor (`Pillow`), advisory image-forensics flags (`MISSING_EXIF`, `EDITING_SOFTWARE_TAG`, `HIGH_ELA_RESIDUAL`, `advisory_only: true`), `/api/assets/{asset_id}/forensics`, 5 synthetic forensic log fixtures (`dd`, `ewfacquire`, Autopsy, ExifTool, officer notes), **25/25 `pytest` tests passing**, **n8n + Telegram** live webhook verified. | **DONE** |
| **Nov 28–29 (Days 3–4)** | **Adaptive Mobile + Desktop PWA (`apps/web`)** | React + Vite + Tailwind PWA with auto-detect + 1-click `📱 Field Mobile` ⇄ `🖥️ Expert Desktop` switcher, client-side WebCrypto `SHA-256` before upload, QR handoff generator, custody timeline UI, TRACE advisory panel, `tsc -b && vite build` passing. | **DONE** |
| **Nov 30–Dec 1 (Days 5–6)** | **AI Forensic Audit Agent + Sponsors** | Pydantic-validated agent (`agent.py`: Gemini/Ollama/deterministic fallback) parsing 5 log formats (`dd`, `ewfacquire`, Autopsy, ExifTool, officer notes), flagging custody gaps & UTC/IST conflicts, drafting citation-grounded Part A/B text; **Olostep** BSA S.63 legal reference (`sponsors.py`); **n8n** live Telegram webhook; **28/28 `pytest` tests passing**. | **DONE** |
| **Dec 2 (Day 7)** | **Section 63(4) PDF & Expert Sign-Off** | Pure-Python ReportLab renderer (`pdf_s63.py`) for official **BSA Section 63(4) Part A & Part B**, `/sign-s63` + `/certificate.pdf` endpoints, human expert sign-off UI, signed PDF embedded in `.zip` bundle, **30/30 `pytest` tests passing**. | **DONE** |
| **Dec 3 (Day 8)** | **Benchmark Suite & Keploy Reliability** | Automated 5-benchmark suite (`scripts/run_benchmarks.py` + `docs/BENCHMARKS.md`: 100/100 byte-flip tamper, 50/50 chain-break detection, 0/50 false flags, 20/20 idempotency, 5/5 log formats, 88.81ms E2E), **31/31 `pytest` tests passing**. | **DONE** |
| **Dec 4 (Day 9)** | **Docker, Deploy & Feature Freeze** | `docker-compose.yml` (API + Web), clean setup instructions, live hosted demo, feature freeze. | Next |
| **Dec 5 (Day 10)** | **Demo Video, Pitch Deck & Bitsbee Tree** | 2-minute live demo video (showing Mobile Field Intake → AI Audit → Bitsbee Ops / Desktop Part B Sign-Off → `attesta-verify` offline CLI), pitch deck, **Bitsbee Tree** QR hub, Olostep social post. | Planned |
| **Dec 6** | **Submit Early** | Final submission on Homingo Hack Days dashboard before deadline. | Planned |

---

## Part 2: Post-Hackathon Production Roadmap

### v1.1 — Legal & Cryptographic Hardening (Weeks 1–2)
- **RFC 3161 Trusted Timestamping (TSA):** Anchor `head_event_hash` to an external TSA so timestamps are independently provable against backdating.
- **Hardware/Passkey Signing (WebAuthn):** Allow custodians and experts to sign Part A / Part B using device passkeys or Aadhaar eSign-compatible workflows.
- **Native Mobile Capture Wrapper:** Package the Field Mobile PWA / Flutter module for offline-first seizure at crime scenes with zero connectivity.

### v2.0 — Firm & Cyber-Cell Operations (Weeks 3–6)
- **Multi-Tenant Workspaces & RBAC:** Separate vaults for Police Cyber Cells, FSL Labs, and Law Firms with role-scoped keys.
- **Forensic Tool Importers:** Direct XML/JSON parsers for Cellebrite UFED, Magnet AXIOM, and FTK Imager acquisition reports.
- **WORM Cloud Archival:** Optional S3 Object Lock / immutable storage backend for multi-GB video/disk images (keeping local-first hash verification).

### v3.0 — Institutional Adoption & Demand Validation
- **Pre-Code/Early-Pilot Validation:** Run structured interviews with 25 Indian cyber-law advocates, DFIR consultants, and forensic lab analysts; onboard 2–3 pilot partners on anonymized/synthetic cases before commercial rollout.
