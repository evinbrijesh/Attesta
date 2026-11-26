"""Day 8 quantitative benchmark suite for Attesta (tamper, chain-break, idempotency, log parsing, latency)."""

from __future__ import annotations

import json
import sys
import tempfile
import time
import zipfile
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = API_DIR.parents[1]
VERIFY_PKG = REPO_ROOT / "packages" / "verify-coc"

for p in (str(API_DIR), str(VERIFY_PKG)):
    if p not in sys.path:
        sys.path.insert(0, p)

from app.agent import parse_acquisition_log, run_audit_agent  # noqa: E402
from app.custody import create_case, export_bundle, ingest_evidence, record_handoff  # noqa: E402
from app.db import get_connection  # noqa: E402
from app.pdf_s63 import Section63CertificateData, render_section63_pdf  # noqa: E402
from verify_coc.verifier import verify_bundle  # noqa: E402


def run_all_benchmarks() -> dict[str, object]:
    """Execute all 5 Attesta benchmarks and return exact measured results."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        conn = get_connection(tmp_path / "bench.db")
        storage = tmp_path / "store"
        case = create_case(conn, title="Benchmark Suite")
        cid = case["case_id"]

        # 1. 100 single-byte-flip tamper tests
        tamper_caught = 0
        for i in range(100):
            data = f"benchmark-evidence-payload-{i:03d}-data".encode("utf-8")
            res = ingest_evidence(
                conn,
                case_id=cid,
                filename=f"ev_{i}.bin",
                media_type="application/octet-stream",
                data=data,
                storage_dir=storage,
                custodian="Benchmark Officer",
            )
            orig_zip = export_bundle(conn, asset_id=res.asset_id, output_zip=tmp_path / f"orig_{i}.zip")
            bad_zip = tmp_path / f"bad_{i}.zip"
            with zipfile.ZipFile(orig_zip, "r") as zin, zipfile.ZipFile(bad_zip, "w") as zout:
                for item in zin.infolist():
                    raw = zin.read(item.filename)
                    if item.filename.startswith("evidence/"):
                        ba = bytearray(raw)
                        ba[i % len(ba)] ^= 0x01
                        raw = bytes(ba)
                    zout.writestr(item, raw)
            if not verify_bundle(bad_zip).valid:
                tamper_caught += 1

        # 2. 50 broken chains + 50 clean chains
        broken_caught = 0
        clean_false_flags = 0
        for i in range(50):
            res = ingest_evidence(
                conn,
                case_id=cid,
                filename=f"chain_{i}.bin",
                media_type="application/octet-stream",
                data=f"chain-data-{i:03d}".encode("utf-8"),
                storage_dir=storage,
                custodian="Officer A",
            )
            record_handoff(conn, asset_id=res.asset_id, actor_from="Officer A", actor_to="Lab B", purpose="Audit", location="BLR")
            record_handoff(conn, asset_id=res.asset_id, actor_from="Lab B", actor_to="Advocate C", purpose="S63", location="Court")
            clean_zip = export_bundle(conn, asset_id=res.asset_id, output_zip=tmp_path / f"clean_{i}.zip")
            if not verify_bundle(clean_zip).valid:
                clean_false_flags += 1

            # Inject 5 distinct chain-break modes across 50 cases
            mode = i % 5
            broken_zip = tmp_path / f"broken_{i}.zip"
            with zipfile.ZipFile(clean_zip, "r") as zin, zipfile.ZipFile(broken_zip, "w") as zout:
                for item in zin.infolist():
                    raw = zin.read(item.filename)
                    if item.filename == "custody_log.jsonl":
                        lines = raw.decode("utf-8").splitlines()
                        if mode == 0:  # Broken prev_hash
                            ev = json.loads(lines[1])
                            ev["prev_hash"] = "f" * 64
                            lines[1] = json.dumps(ev, sort_keys=True)
                        elif mode == 1:  # Deleted middle event
                            lines = [lines[0], lines[2]]
                        elif mode == 2:  # Forged Ed25519 signature
                            ev = json.loads(lines[2])
                            ev["signature"] = "00" * 64
                            lines[2] = json.dumps(ev, sort_keys=True)
                        elif mode == 3:  # Payload tamper without re-hashing
                            ev = json.loads(lines[1])
                            ev["actor_to"] = "Unauthorized Actor"
                            lines[1] = json.dumps(ev, sort_keys=True)
                        else:  # Sequence gap
                            ev = json.loads(lines[2])
                            ev["seq"] = 99
                            lines[2] = json.dumps(ev, sort_keys=True)
                        raw = ("\n".join(lines) + "\n").encode("utf-8")
                    zout.writestr(item, raw)
            if not verify_bundle(broken_zip).valid:
                broken_caught += 1

        # 3. Idempotency (20 repeated ingests)
        idem_hits = 0
        first_res = ingest_evidence(
            conn,
            case_id=cid,
            filename="idem.bin",
            media_type="application/octet-stream",
            data=b"idempotent-payload",
            storage_dir=storage,
            custodian="Officer",
        )
        for _ in range(20):
            again = ingest_evidence(
                conn,
                case_id=cid,
                filename="idem_dup.bin",
                media_type="application/octet-stream",
                data=b"idempotent-payload",
                storage_dir=storage,
                custodian="Officer",
            )
            if again.idempotent_hit and again.asset_id == first_res.asset_id:
                idem_hits += 1

        # 4. 5 forensic log format parse accuracy
        logs_dir = REPO_ROOT / "fixtures" / "logs"
        expected_formats = {
            "01_dd_acquisition.log": "dd",
            "02_ewfacquire.log": "ewfacquire",
            "03_autopsy_summary.txt": "autopsy",
            "04_exiftool_dump.json": "exiftool_json",
            "05_officer_notes.txt": "officer_notes",
        }
        parsed_ok = 0
        for fname, expected_fmt in expected_formats.items():
            parsed = parse_acquisition_log((logs_dir / fname).read_text(encoding="utf-8"))
            if parsed.format_detected == expected_fmt:
                parsed_ok += 1

        # 5. End-to-end pipeline timing (ingest -> handoff -> audit -> S.63 PDF -> export -> offline verify)
        t0 = time.perf_counter()
        r_e2e = ingest_evidence(
            conn,
            case_id=cid,
            filename="e2e.mp4",
            media_type="video/mp4",
            data=b"e2e-synthetic-cctv-stream",
            storage_dir=storage,
            custodian="IO Officer",
        )
        record_handoff(conn, asset_id=r_e2e.asset_id, actor_from="IO Officer", actor_to="FSL Expert", purpose="S63", location="BLR")
        audit = run_audit_agent(conn, asset_id=r_e2e.asset_id, log_text="")
        render_section63_pdf(
            Section63CertificateData(
                cert_id="s63_bench",
                case_id=cid,
                case_title="Benchmark",
                asset_id=r_e2e.asset_id,
                filename="e2e.mp4",
                media_type="video/mp4",
                size_bytes=r_e2e.size_bytes,
                sha256=r_e2e.sha256,
                blake3=r_e2e.blake3,
                head_event_hash="0" * 64,
                event_count=2,
                custodian_name="IO Officer",
                custodian_designation="IO",
                expert_name="FSL Expert",
                expert_designation="Examiner",
                part_a_text=audit.part_a_draft,
                part_b_text=audit.part_b_draft,
                signed_at_utc="2026-11-26T00:00:00Z",
            ),
            tmp_path / "e2e.pdf",
        )
        e2e_zip = export_bundle(conn, asset_id=r_e2e.asset_id, output_zip=tmp_path / "e2e.zip")
        e2e_ok = verify_bundle(e2e_zip).valid
        e2e_ms = round((time.perf_counter() - t0) * 1000.0, 2)

        conn.close()
        return {
            "byte_flip_tamper_caught": tamper_caught,
            "byte_flip_total": 100,
            "chain_break_caught": broken_caught,
            "chain_break_total": 50,
            "clean_chain_false_flags": clean_false_flags,
            "clean_chain_total": 50,
            "idempotent_hits": idem_hits,
            "idempotent_total": 20,
            "log_formats_parsed": parsed_ok,
            "log_formats_total": 5,
            "e2e_pipeline_valid": e2e_ok,
            "e2e_pipeline_ms": e2e_ms,
        }


if __name__ == "__main__":
    print(json.dumps(run_all_benchmarks(), indent=2))
