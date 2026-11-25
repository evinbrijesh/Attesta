"""Tests for Day 5-6 AI Forensic Audit Agent, 5-format log parser, and sponsor helpers."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.agent import parse_acquisition_log, run_audit_agent
from app.custody import create_case, ingest_evidence, record_handoff
from app.db import get_connection
from app.main import create_app


def test_parse_all_five_synthetic_log_formats() -> None:
    logs_dir = Path(__file__).resolve().parents[3] / "fixtures" / "logs"
    expectations = [
        ("01_dd_acquisition.log", "dd", "SI Rajesh Kumar"),
        ("02_ewfacquire.log", "ewfacquire", "Dr. Ananya Rao"),
        ("03_autopsy_summary.txt", "autopsy", "Meera Nair"),
        ("04_exiftool_dump.json", "exiftool_json", None),
        ("05_officer_notes.txt", "officer_notes", None),
    ]
    for filename, expected_fmt, expected_operator in expectations:
        text = (logs_dir / filename).read_text(encoding="utf-8")
        parsed = parse_acquisition_log(text)
        assert parsed.format_detected == expected_fmt
        if expected_operator:
            assert expected_operator in (parsed.operator_or_examiner or "")


def test_audit_detects_custody_gap_chronological_inversion_and_log_risks(tmp_path: Path) -> None:
    conn = get_connection(tmp_path / "audit.db")
    case = create_case(conn, title="Audit Test Case")
    r = ingest_evidence(
        conn,
        case_id=case["case_id"],
        filename="gate.mp4",
        media_type="video/mp4",
        data=b"video-stream-01",
        storage_dir=tmp_path / "store",
        custodian="Complainant",
        occurred_at_utc="2026-11-24T06:00:00Z",
    )
    # 5-hour custody gap
    record_handoff(
        conn,
        asset_id=r.asset_id,
        actor_from="Complainant",
        actor_to="FSL",
        purpose="Lab transfer",
        location="Bengaluru",
        occurred_at_utc="2026-11-24T11:00:00Z",
    )
    # Chronological inversion
    record_handoff(
        conn,
        asset_id=r.asset_id,
        actor_from="FSL",
        actor_to="Advocate",
        purpose="Review",
        location="Court",
        occurred_at_utc="2026-11-24T09:00:00Z",
    )

    logs_dir = Path(__file__).resolve().parents[3] / "fixtures" / "logs"
    notes = (logs_dir / "05_officer_notes.txt").read_text(encoding="utf-8")

    result = run_audit_agent(conn, asset_id=r.asset_id, log_text=notes)
    codes = {f.code for f in result.flags}
    assert "CUSTODY_TIME_GAP" in codes
    assert "CHRONOLOGICAL_INVERSION" in codes
    assert "REENCODING_RISK" in codes
    assert "LOG_CUSTODY_GAP_MENTIONED" in codes
    assert "[event:" in result.part_a_draft
    assert "[hash:" in result.part_a_draft
    assert "[event:" in result.part_b_draft
    assert "court-admissible" not in result.part_b_draft.lower()
    conn.close()


def test_audit_and_legal_endpoints(tmp_path: Path) -> None:
    app = create_app(db_path=tmp_path / "api_audit.db", storage_dir=tmp_path / "store")
    client = TestClient(app)

    cid = client.post("/api/cases", json={"title": "API Audit"}).json()["case_id"]
    asset_id = client.post(
        f"/api/cases/{cid}/ingest",
        files={"file": ("clip.mp4", b"clip-bytes", "video/mp4")},
        data={"custodian": "IO Sharma"},
    ).json()["asset_id"]

    audit_resp = client.post(
        f"/api/assets/{asset_id}/audit",
        json={"log_text": "ewfacquire 20230405\nExaminer Name: Dr. Rao\nIST vs UTC note", "notify_n8n": False},
    )
    assert audit_resp.status_code == 200
    body = audit_resp.json()
    assert body["parsed_log"]["format_detected"] == "ewfacquire"
    assert any(f["code"] == "TIMEZONE_MIXUP_RISK" for f in body["flags"])

    legal_resp = client.get("/api/legal/section63")
    assert legal_resp.status_code == 200
    assert "Section 63(4)" in legal_resp.json()["statute"]
