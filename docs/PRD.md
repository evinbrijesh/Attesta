# Attesta — Product Requirements Document (PRD)

**Product:** Attesta (*"Attested. Verified. Sealed."*)  
**Track:** Homingo Hackathon · Edition 01 — **Automation** (Bring Your Own Problem)  
**Target Jurisdiction:** India — **Bharatiya Sakshya Adhiniyam (BSA), 2023 · Section 63(4)**  
**Status:** Day 1 Core Complete (`20/20` tests passing) · Building toward Dec 6, 2026 submission  

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
- **Tamper-Evident Bundle & Offline CLI:** Exports `evidence/`, `custody_log.jsonl`, `manifest.json`, `sha256sums.txt` in a `.zip` verified offline by `attesta-verify`.

### 4.2 Adaptive Mobile + Desktop UI (Day 2–3)
- **Auto-detect + 1-Click View Switcher (`📱 Field Mobile` ⇄ `🖥️ Expert Desktop`):**
  - Mobile view: Evidence intake with client-side WebCrypto `SHA-256` before upload, QR code handoff token, Part A custodian declaration form.
  - Desktop view: Case timeline, AI audit findings panel, TRACE advisory metadata drawer, side-by-side Part A + Part B Section 63(4) preview, human expert sign-off, and `.zip` download.

### 4.3 AI Audit Agent (Day 4–5)
- **Log Parser:** Extracts structured acquisition metadata from 5 formats (`dd` logs, `ewfacquire`, Autopsy/SleuthKit summaries, EXIF/media dumps, and free-text officer notes).
- **Deterministic + LLM Anomaly Auditor:** Flags missing handoffs, chronological inversions, UTC vs. IST timezone mismatches, and hash discrepancies.
- **Grounded Section 63(4) Drafter:** Produces Part A & Part B technical descriptions where every factual sentence cites an `[event:evt_...]` or `[hash:...]` identifier.
- **Advisory Media Forensics (from TRACE):** Extracts EXIF/device metadata and flags potential recompression/manipulation anomalies as *Advisory Only* (never auto-rejects evidence).

### 4.4 Sponsor Integrations (Natural Fit, Zero Bloat)
- **n8n:** Event-driven workflow webhook triggered on Part A submission → routes case notification to expert → archives manifest on Part B sign-off.
- **Bitsbee Ops:** MCP-native mobile decision card pushed to the forensic expert's phone for 1-tap Part B review/approval.
- **Olostep:** Legal reference grounding—fetches current BSA Section 63 statutory text and Supreme Court/High Court practice circulars for the expert reference drawer.
- **Keploy:** Automated API regression recording & replay across `/ingest`, `/handoff`, `/audit`, and `/bundle` endpoints.
- **Bitsbee Tree:** Public launch hub with QR code linking demo video, GitHub repo, live app, and `attesta-verify` CLI.

---

## 5. Non-Goals (Strict Scope Boundaries)
- **No disk imaging or mobile extraction:** Attesta ingests exported files and tool logs; it does not replace Cellebrite, Magnet AXIOM, or `ewfacquire`.
- **No autonomous AI signing:** Only a human custodian/expert signs Part A/Part B.
- **No real case data in demos/tests:** All hackathon fixtures, logs, and evidence files are strictly synthetic.

---

## 6. Measurable Evidence & Evaluation Benchmarks

To satisfy the Automation track's **Evidence** and **Reliability** criteria, Attesta will measure and report:
1. **Certificate Prep Time:** Manual Word/Excel workflow vs. Attesta end-to-end time.
2. **Byte-Level Tamper Detection:** 100 synthetic files with 1-byte flips → `%` caught by `attesta-verify` (Target: `100/100`).
3. **Chain-Break Detection:** 50 synthetic cases (deleted events, swapped timestamps, forged signatures, broken `prev_hash`) → detection rate and false-positive rate.
4. **Idempotency:** Re-ingesting identical evidence bytes returns the existing `asset_id` without duplicating custody events.
5. **Log Parse Accuracy:** Structured extraction accuracy across 5 forensic log formats.
