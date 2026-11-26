# Attesta — Quantitative Evidence & Reliability Benchmarks

All metrics below were measured directly on synthetic test corpora via [`apps/api/scripts/run_benchmarks.py`](../apps/api/scripts/run_benchmarks.py) and asserted in [`apps/api/tests/test_benchmarks.py`](../apps/api/tests/test_benchmarks.py).

## Summary Results

| Benchmark | Measured Result | Notes |
|---|---|---|
| **1. Single-Byte-Flip Tamper Detection** | **100 / 100 caught (100.0%)** | Flipped 1 bit in archived evidence across 100 exported `.zip` bundles; verified offline by `attesta-verify`. |
| **2. Synthetic Chain-Break Detection** | **50 / 50 caught (100.0%)** | 10 cases each across 5 break modes: broken `prev_hash`, deleted middle event, forged `Ed25519` signature, payload tamper, sequence gap. |
| **3. Clean-Chain False-Flag Rate** | **0 / 50 false flags (0.0%)** | 50 multi-handoff valid bundles verified cleanly offline. |
| **4. Ingest Idempotency** | **20 / 20 idempotent hits (100.0%)** | Repeated ingestion of identical bytes returns existing `asset_id` with zero duplicate `custody_events`. |
| **5. Forensic Log Parse Accuracy** | **5 / 5 formats (100.0%)** | `dd`, `ewfacquire`, `autopsy`, `exiftool_json`, and free-text `officer_notes` in `fixtures/logs/`. |
| **6. End-to-End Pipeline Latency** | **88.81 ms** | Deterministic path (`ingest` -> `handoff` -> `audit` -> `Section 63(4) PDF` -> `.zip` export -> `attesta-verify`). *(Excluding optional network LLM latency.)* |

## Reproducing Locally

```bash
cd apps/api
uv run python scripts/run_benchmarks.py
uv run pytest -v   # 31/31 passing
```
