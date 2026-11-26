# Attesta — Product Requirements Document (PRD)

**Product:** Attesta (*"Attested. Verified. Sealed."*)  
**Track:** Homingo Hackathon · Edition 01 — **Automation** (Bring Your Own Problem)  
**Target Jurisdiction:** India — **Bharatiya Sakshya Adhiniyam (BSA), 2023 · Section 63(4)**  
**Status:** Days 1–9 Complete (`31/31` `pytest` tests passing; Docker & UI ready) · Building toward Dec 6, 2026 submission  

---

## 1. Problem Statement

Under India's **Bharatiya Sakshya Adhiniyam (BSA), Section 63** (effective 1 July 2024, replacing Section 65B of the Indian Evidence Act, and upheld by the Supreme Court of India in *Pune Bar Association v. Union of India*, May 2026), any secondary electronic record submitted in court—CCTV footage, phone videos, WhatsApp chats, call recordings, emails, or PDFs—must be accompanied by a statutory **Section 63(4) Certificate** containing:

1. **Part A (Custodian's Declaration):** Signed by the person in lawful control of the device/record, disclosing the record's origin and mandatory **cryptographic hash value** (e.g., `SHA-256`).
2. **Part B (Expert's Certification):** Signed by a technical or forensic expert certifying the extraction process, hash continuity, and integrity of the record.

### What Is Broken Today
- **Manual Word/Excel Workflows:** Advocates, police cyber cells, and private forensic labs still compute hashes manually and fill Part A/Part B certificates by hand.
- **Hash Destruction at Intake:** Field evidence is routinely shared via WhatsApp or email before hashing, which re-encodes media and invalidates the original cryptographic fingerprint.
- **Broken Chain of Custody:** Mutable Excel/Notion custody logs lack cryptographic tamper-evidence, suffer from UTC vs. IST timestamp conflicts, and miss intermediate handoffs—causing evidence to be challenged or excluded during cross-examination.

---

## 2. Product Vision

**Attesta** is an automated, tamper-evident electronic evidence pipeline that:
1. Captures and fingerprints digital evidence at intake (`SHA-256` + `BLAKE3`, including client-side browser hashing on mobile before upload).
2. Records every custody transfer in an **append-only, hash-chained, Ed25519-signed ledger**.
3. Uses a constrained **AI Audit Agent** to parse messy forensic acquisition logs, flag custody gaps/timestamp conflicts/hash mismatches, and draft grounded Part A & Part B narratives citing verified event IDs and hashes.
4. Generates the **Section 63(4) Certificate (Part A + Part B) PDF** for **human expert review and sign-off**.
5. Exports a self-contained `.zip` bundle verifiable **completely offline** via an open-source CLI (`attesta-verify`).

> **Core Guardrail:** Attesta *prepares* the Section 63(4) certificate and cryptographic audit bundle for human expert review and sign-off. It does not claim legal admissibility on its own, and the AI agent **never** computes hashes, modifies custody records, or signs certificates.

---

## 3. Target Users & Buyers

| Role | Context | Primary Mode |
|---|---|---|
| **Field Custodian (Part A)** | Police cyber cell IO, victim/complainant, corporate IT admin, shop owner | **📱 Field Mobile PWA** (on-device SHA-256, upload, QR handoff, Part A sign-off) |
| **Forensic Expert / Advocate (Part B)** | Independent DFIR examiner, FSL analyst, litigation advocate | **🖥️ Expert Desktop** (AI log audit, anomaly resolution, Part B review & sign-off, PDF/bundle export) |
| **Verifier / Opposing Counsel / Court** | Opposing expert or auditor verifying submitted evidence | **Offline CLI (`attesta-verify`)** — zero server trust required |

---

## 4. Functional Scope (Hackathon v1)

### 4.1 Deterministic Core (Implemented — Day 1)
- **Idempotent Evidence Intake:** Dual hashing (`SHA-256` + `BLAKE3`) deduplicated by `(case_id, sha256, blake3)`.
- **Append-Only Custody Ledger:** SQLite WAL-mode with `BEFORE UPDATE` and `BEFORE DELETE` triggers blocking any mutation of `custody_events`.
- **Hash-Chained & Signed Events:** Each event binds `prev_hash` + canonical JSON payload into `event_hash` and signs with `Ed25519`.
- **Tamper-Evident Bundle & Offline CLI:** Exports `evidence/`, `custody_log.jsonl`, `manifest.json`, optional signed `certificate_s63.pdf`, and `sha256sums.txt` in a `.zip` verified offline by `attesta-verify`.

### 4.2 Adaptive Mobile + Desktop UI (Implemented — Days 3–4, Polished Day 9)
- **Auto-detect + 1-Click View Switcher (`Field Mobile` ⇄ `Expert Desktop`):**
  - Mobile view: Case creation/selection, evidence intake with client-side WebCrypto `SHA-256` before upload, Part A custodian/location/context capture, QR code handoff token, and post-seal custody handoff logging.
  - Desktop view: Editorial Forensic Dossier workspace with case/asset browser, Ed25519 custody timeline, TRACE advisory metadata panel, AI log audit trigger, side-by-side Part A + Part B Section 63(4) preview/editor, human expert sign-off & PDF download, and `.zip` export.

### 4.3 AI Audit Agent, TRACE & Section 63(4) PDF (Implemented — Days 2, 5–7)
- **Log Parser:** Extracts structured acquisition metadata from 5 formats (`dd` logs, `ewfacquire`, Autopsy summaries, ExifTool JSON dumps, and free-text officer notes).
- **Deterministic + LLM Anomaly Auditor:** Flags chronological inversions, custody gaps (> 2h), UTC vs. IST timezone mismatches, RTC clock skew, WhatsApp re-encoding risk, and hash discrepancies (`Gemini` / `Ollama` / deterministic grounded fallback).
- **Grounded Section 63(4) Drafter & PDF Generator:** Produces Part A & Part B technical descriptions citing `[event:evt_...]` or `[hash:...]` identifiers, and renders an official Section 63(4) PDF (`ReportLab`) upon human sign-off.
- **Advisory Media Forensics (TRACE):** Extracts EXIF/dimension metadata and ELA mean difference, flagging potential anomalies as *Advisory Only* (`advisory_only: true`; never auto-rejects evidence).

### 4.4 Sponsor Integrations
- **n8n (Implemented):** Optional webhook triggered on Part A audit (`PART_A_SUBMITTED`) and Part B sign-off (`PART_B_SIGNED`) when `N8N_WEBHOOK_URL` is configured.
- **Olostep (Implemented):** Legal reference grounding for the expert slide-over drawer (`GET /api/legal/section63`), supporting live scraping via `OLOSTEP_API_KEY` with a verified local cache fallback.
- **Bitsbee Tree (Planned — Day 10):** Public launch hub with QR code linking demo video, GitHub repo, live app, and `attesta-verify` CLI.
- **Bitsbee Ops & Keploy (Planned / Env Reserved):** `BITSBEE_OPS_WEBHOOK_URL` is reserved in `.env.example` (webhook dispatch not yet wired); Keploy API recording/replay is planned ahead of submission (API & offline verification currently covered by `31/31` `pytest` tests).

---

## 5. Non-Goals (Strict Scope Boundaries)
- **No disk imaging or mobile extraction:** Attesta ingests exported files and tool logs; it does not replace Cellebrite, Magnet AXIOM, or `ewfacquire`.
- **No autonomous AI signing:** Only a human custodian/expert signs Part A/Part B.
- **No real case data in demos/tests:** All hackathon fixtures, logs, and evidence files are strictly synthetic.

---

## 6. Measurable Evidence & Evaluation Benchmarks

Measured via [`apps/api/scripts/run_benchmarks.py`](../apps/api/scripts/run_benchmarks.py) and asserted in [`apps/api/tests/test_benchmarks.py`](../apps/api/tests/test_benchmarks.py) (full report in [`docs/BENCHMARKS.md`](BENCHMARKS.md)):
1. **End-to-End Deterministic Latency:** `88.81 ms` (`ingest` → `handoff` → `audit` → `Section 63(4) PDF` → `.zip` export → `attesta-verify`, excluding optional network LLM calls).
2. **Byte-Level Tamper Detection:** `100 / 100` single-byte flips caught offline by `attesta-verify` (`100.0%`).
3. **Chain-Break Detection & False-Flag Rate:** `50 / 50` synthetic chain breaks caught across 5 break modes (`100.0%`); `0 / 50` clean-chain false flags (`0.0%`).
4. **Idempotency:** `20 / 20` duplicate uploads returned existing `asset_id` with zero duplicate custody events (`100.0%`).
5. **Log Parse Accuracy:** `5 / 5` synthetic forensic log formats parsed cleanly (`100.0%`).
