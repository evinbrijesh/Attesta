"""Core cryptographic, append-only ledger, tamper detection, and API tests for Attesta."""

from __future__ import annotations

import json
import sqlite3
import sys
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.crypto import (
    GENESIS_HASH,
    compute_digests,
    compute_event_hash,
    generate_keypair,
    sign_event_hash,
    verify_event_signature,
)
from app.custody import (
    create_case,
    export_bundle,
    ingest_evidence,
    record_handoff,
    verify_asset_chain,
)
from app.db import get_connection
from app.main import create_app

# Allow importing standalone verify_coc package directly in tests
VERIFY_PKG = Path(__file__).resolve().parents[3] / "packages" / "verify-coc"
if str(VERIFY_PKG) not in sys.path:
    sys.path.insert(0, str(VERIFY_PKG))

from verify_coc.verifier import verify_bundle  # noqa: E402


@pytest.fixture()
def env(tmp_path: Path):
    """Provide an isolated SQLite DB and evidence storage directory."""
    db_path = tmp_path / "attesta.db"
    storage = tmp_path / "evidence"
    conn = get_connection(db_path)
    case = create_case(conn, title="Synthetic Cyber Fraud Case", description="Test case")
    yield conn, storage, case["case_id"], tmp_path
    conn.close()


def test_01_compute_digests_deterministic() -> None:
    d1 = compute_digests(b"synthetic cctv frame")
    d2 = compute_digests(b"synthetic cctv frame")
    assert d1 == d2
    assert len(d1.sha256) == 64
    assert len(d1.blake3_hex) == 64
    assert d1.size_bytes == 20


def test_02_compute_digests_single_bit_sensitivity() -> None:
    d1 = compute_digests(b"evidence-001")
    d2 = compute_digests(b"evidence-002")
    assert d1.sha256 != d2.sha256
    assert d1.blake3_hex != d2.blake3_hex


def test_03_ed25519_sign_and_verify() -> None:
    kp = generate_keypair()
    h = compute_event_hash(GENESIS_HASH, {"a": 1})
    sig = sign_event_hash(h, kp.private_hex)
    assert verify_event_signature(h, sig, kp.public_hex) is True


def test_04_ed25519_rejects_wrong_key() -> None:
    kp1 = generate_keypair()
    kp2 = generate_keypair()
    h = compute_event_hash(GENESIS_HASH, {"a": 1})
    sig = sign_event_hash(h, kp1.private_hex)
    assert verify_event_signature(h, sig, kp2.public_hex) is False


def test_05_ed25519_rejects_tampered_hash() -> None:
    kp = generate_keypair()
    h = compute_event_hash(GENESIS_HASH, {"a": 1})
    sig = sign_event_hash(h, kp.private_hex)
    bad_h = "f" * 64
    assert verify_event_signature(bad_h, sig, kp.public_hex) is False


def test_06_ingest_creates_genesis_event(env) -> None:
    conn, storage, case_id, _ = env
    res = ingest_evidence(
        conn,
        case_id=case_id,
        filename="cctv.mp4",
        media_type="video/mp4",
        data=b"video-bytes",
        storage_dir=storage,
        custodian="SI Rajesh Kumar",
    )
    assert res.idempotent_hit is False
    v = verify_asset_chain(conn, res.asset_id)
    assert v.valid is True
    assert v.event_count == 1
    assert v.file_hash_match is True


def test_07_ingest_is_idempotent(env) -> None:
    conn, storage, case_id, _ = env
    r1 = ingest_evidence(
        conn,
        case_id=case_id,
        filename="cctv.mp4",
        media_type="video/mp4",
        data=b"same-bytes",
        storage_dir=storage,
        custodian="SI Rajesh Kumar",
    )
    r2 = ingest_evidence(
        conn,
        case_id=case_id,
        filename="cctv_copy.mp4",
        media_type="video/mp4",
        data=b"same-bytes",
        storage_dir=storage,
        custodian="SI Rajesh Kumar",
    )
    assert r1.asset_id == r2.asset_id
    assert r2.idempotent_hit is True
    count = conn.execute("SELECT COUNT(*) FROM custody_events WHERE asset_id = ?", (r1.asset_id,)).fetchone()[0]
    assert count == 1


def test_08_multi_handoff_chain_validates(env) -> None:
    conn, storage, case_id, _ = env
    r = ingest_evidence(
        conn,
        case_id=case_id,
        filename="call.wav",
        media_type="audio/wav",
        data=b"audio-bytes",
        storage_dir=storage,
        custodian="Witness A",
    )
    record_handoff(conn, asset_id=r.asset_id, actor_from="Witness A", actor_to="Cyber Cell", purpose="Seizure", location="Bengaluru")
    record_handoff(conn, asset_id=r.asset_id, actor_from="Cyber Cell", actor_to="Forensic Lab", purpose="Imaging", location="FSL")
    record_handoff(conn, asset_id=r.asset_id, actor_from="Forensic Lab", actor_to="Advocate Meera", purpose="Section 63(4) Review", location="High Court")

    v = verify_asset_chain(conn, r.asset_id)
    assert v.valid is True
    assert v.event_count == 4


def test_09_db_trigger_forbids_custody_update(env) -> None:
    conn, storage, case_id, _ = env
    r = ingest_evidence(
        conn,
        case_id=case_id,
        filename="doc.pdf",
        media_type="application/pdf",
        data=b"pdf-bytes",
        storage_dir=storage,
        custodian="Officer",
    )
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        conn.execute("UPDATE custody_events SET actor_to = 'Attacker' WHERE asset_id = ?", (r.asset_id,))


def test_10_db_trigger_forbids_custody_delete(env) -> None:
    conn, storage, case_id, _ = env
    r = ingest_evidence(
        conn,
        case_id=case_id,
        filename="doc.pdf",
        media_type="application/pdf",
        data=b"pdf-bytes",
        storage_dir=storage,
        custodian="Officer",
    )
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        conn.execute("DELETE FROM custody_events WHERE asset_id = ?", (r.asset_id,))


def test_11_detects_evidence_byte_tampering_on_disk(env) -> None:
    conn, storage, case_id, _ = env
    r = ingest_evidence(
        conn,
        case_id=case_id,
        filename="img.png",
        media_type="image/png",
        data=b"original-image-bytes",
        storage_dir=storage,
        custodian="Officer",
    )
    stored = Path(conn.execute("SELECT storage_path FROM evidence_assets WHERE asset_id = ?", (r.asset_id,)).fetchone()[0])
    stored.write_bytes(b"tampered-image-bytes")

    v = verify_asset_chain(conn, r.asset_id)
    assert v.valid is False
    assert v.file_hash_match is False
    assert any("tampering" in e.lower() for e in v.errors)


def test_12_detects_missing_evidence_file(env) -> None:
    conn, storage, case_id, _ = env
    r = ingest_evidence(
        conn,
        case_id=case_id,
        filename="img.png",
        media_type="image/png",
        data=b"bytes",
        storage_dir=storage,
        custodian="Officer",
    )
    stored = Path(conn.execute("SELECT storage_path FROM evidence_assets WHERE asset_id = ?", (r.asset_id,)).fetchone()[0])
    stored.unlink()

    v = verify_asset_chain(conn, r.asset_id)
    assert v.valid is False
    assert any("missing" in e.lower() for e in v.errors)


def test_13_bundle_export_and_offline_cli_verify_passes(env) -> None:
    conn, storage, case_id, tmp_path = env
    r = ingest_evidence(
        conn,
        case_id=case_id,
        filename="chat.json",
        media_type="application/json",
        data=b'{"msg":"hello"}',
        storage_dir=storage,
        custodian="Complainant",
    )
    record_handoff(conn, asset_id=r.asset_id, actor_from="Complainant", actor_to="Lab", purpose="Audit", location="Delhi")
    bundle = export_bundle(conn, asset_id=r.asset_id, output_zip=tmp_path / "bundle.zip")

    report = verify_bundle(bundle)
    assert report.valid is True
    assert report.event_count == 2
    assert report.errors == []


def test_14_offline_verifier_catches_100_single_byte_flips(env) -> None:
    conn, storage, case_id, tmp_path = env
    caught = 0
    for i in range(100):
        payload = f"synthetic-evidence-file-{i:03d}-payload".encode("utf-8")
        r = ingest_evidence(
            conn,
            case_id=case_id,
            filename=f"file_{i}.bin",
            media_type="application/octet-stream",
            data=payload,
            storage_dir=storage,
            custodian="Inspector",
        )
        bundle_path = export_bundle(conn, asset_id=r.asset_id, output_zip=tmp_path / f"b_{i}.zip")

        # Flip 1 byte in the archived evidence file inside a tampered zip copy
        tampered_zip = tmp_path / f"b_{i}_tampered.zip"
        with zipfile.ZipFile(bundle_path, "r") as zin, zipfile.ZipFile(tampered_zip, "w") as zout:
            for item in zin.infolist():
                content = zin.read(item.filename)
                if item.filename.startswith("evidence/"):
                    ba = bytearray(content)
                    ba[i % len(ba)] ^= 0x01
                    content = bytes(ba)
                zout.writestr(item, content)

        if not verify_bundle(tampered_zip).valid:
            caught += 1

    assert caught == 100


def test_15_offline_verifier_catches_chain_break_in_bundle(env) -> None:
    conn, storage, case_id, tmp_path = env
    r = ingest_evidence(
        conn,
        case_id=case_id,
        filename="log.txt",
        media_type="text/plain",
        data=b"log-data",
        storage_dir=storage,
        custodian="Custodian",
    )
    record_handoff(conn, asset_id=r.asset_id, actor_from="Custodian", actor_to="Lab", purpose="Review", location="Pune")
    bundle = export_bundle(conn, asset_id=r.asset_id, output_zip=tmp_path / "orig.zip")

    tampered = tmp_path / "chain_break.zip"
    with zipfile.ZipFile(bundle, "r") as zin, zipfile.ZipFile(tampered, "w") as zout:
        for item in zin.infolist():
            content = zin.read(item.filename)
            if item.filename == "custody_log.jsonl":
                lines = content.decode("utf-8").splitlines()
                ev1 = json.loads(lines[1])
                ev1["prev_hash"] = "a" * 64
                lines[1] = json.dumps(ev1, sort_keys=True)
                content = ("\n".join(lines) + "\n").encode("utf-8")
            zout.writestr(item, content)

    report = verify_bundle(tampered)
    assert report.valid is False
    assert any("chain break" in e.lower() for e in report.errors)


def test_16_offline_verifier_catches_deleted_middle_event(env) -> None:
    conn, storage, case_id, tmp_path = env
    r = ingest_evidence(conn, case_id=case_id, filename="a.bin", media_type="application/octet-stream", data=b"abc", storage_dir=storage, custodian="A")
    record_handoff(conn, asset_id=r.asset_id, actor_from="A", actor_to="B", purpose="Step1", location="BLR")
    record_handoff(conn, asset_id=r.asset_id, actor_from="B", actor_to="C", purpose="Step2", location="BLR")
    bundle = export_bundle(conn, asset_id=r.asset_id, output_zip=tmp_path / "orig3.zip")

    tampered = tmp_path / "deleted_mid.zip"
    with zipfile.ZipFile(bundle, "r") as zin, zipfile.ZipFile(tampered, "w") as zout:
        for item in zin.infolist():
            content = zin.read(item.filename)
            if item.filename == "custody_log.jsonl":
                lines = content.decode("utf-8").splitlines()
                content = (lines[0] + "\n" + lines[2] + "\n").encode("utf-8")
            zout.writestr(item, content)

    report = verify_bundle(tampered)
    assert report.valid is False
    assert any("sequence gap" in e.lower() for e in report.errors)


def test_17_offline_verifier_catches_forged_signature(env) -> None:
    conn, storage, case_id, tmp_path = env
    r = ingest_evidence(conn, case_id=case_id, filename="a.bin", media_type="application/octet-stream", data=b"abc", storage_dir=storage, custodian="A")
    bundle = export_bundle(conn, asset_id=r.asset_id, output_zip=tmp_path / "sig.zip")

    tampered = tmp_path / "bad_sig.zip"
    with zipfile.ZipFile(bundle, "r") as zin, zipfile.ZipFile(tampered, "w") as zout:
        for item in zin.infolist():
            content = zin.read(item.filename)
            if item.filename == "custody_log.jsonl":
                ev = json.loads(content.decode("utf-8").splitlines()[0])
                ev["signature"] = "00" * 64
                content = (json.dumps(ev, sort_keys=True) + "\n").encode("utf-8")
            zout.writestr(item, content)

    report = verify_bundle(tampered)
    assert report.valid is False
    assert any("signature" in e.lower() for e in report.errors)


def test_18_refuses_export_when_chain_tampered(env) -> None:
    conn, storage, case_id, tmp_path = env
    r = ingest_evidence(conn, case_id=case_id, filename="a.bin", media_type="application/octet-stream", data=b"abc", storage_dir=storage, custodian="A")
    stored = Path(conn.execute("SELECT storage_path FROM evidence_assets WHERE asset_id = ?", (r.asset_id,)).fetchone()[0])
    stored.write_bytes(b"corrupted")

    with pytest.raises(ValueError, match="Refusing to export"):
        export_bundle(conn, asset_id=r.asset_id, output_zip=tmp_path / "fail.zip")


def test_19_fastapi_end_to_end_flow(tmp_path: Path) -> None:
    app = create_app(db_path=tmp_path / "api.db", storage_dir=tmp_path / "store")
    client = TestClient(app)

    assert client.get("/api/health").status_code == 200

    case_resp = client.post("/api/cases", json={"title": "Case 2026-01", "description": "Mobile video"})
    assert case_resp.status_code == 201
    case_id = case_resp.json()["case_id"]

    ingest_resp = client.post(
        f"/api/cases/{case_id}/ingest",
        files={"file": ("evidence.mp4", b"synthetic-mp4-stream", "video/mp4")},
        data={"custodian": "Inspector Verma", "location": "Cyber PS", "purpose": "Intake"},
    )
    assert ingest_resp.status_code == 200
    asset_id = ingest_resp.json()["asset_id"]
    assert ingest_resp.json()["idempotent_hit"] is False

    # Re-ingest same bytes -> idempotent
    ingest_again = client.post(
        f"/api/cases/{case_id}/ingest",
        files={"file": ("evidence.mp4", b"synthetic-mp4-stream", "video/mp4")},
        data={"custodian": "Inspector Verma"},
    )
    assert ingest_again.status_code == 200
    assert ingest_again.json()["idempotent_hit"] is True
    assert ingest_again.json()["asset_id"] == asset_id

    handoff_resp = client.post(
        f"/api/assets/{asset_id}/handoff",
        json={"actor_from": "Inspector Verma", "actor_to": "FSL Expert", "purpose": "Section 63(4) Part B", "location": "FSL Lab"},
    )
    assert handoff_resp.status_code == 201

    verify_resp = client.get(f"/api/assets/{asset_id}/verify")
    assert verify_resp.status_code == 200
    assert verify_resp.json()["valid"] is True
    assert verify_resp.json()["event_count"] == 2

    bundle_resp = client.get(f"/api/assets/{asset_id}/bundle")
    assert bundle_resp.status_code == 200
    out_zip = tmp_path / "downloaded.zip"
    out_zip.write_bytes(bundle_resp.content)
    assert verify_bundle(out_zip).valid is True


def test_20_fastapi_returns_404_for_missing_case_and_asset(tmp_path: Path) -> None:
    app = create_app(db_path=tmp_path / "api404.db", storage_dir=tmp_path / "store404")
    client = TestClient(app)

    r1 = client.post(
        "/api/cases/nonexistent/ingest",
        files={"file": ("a.txt", b"hi", "text/plain")},
        data={"custodian": "X"},
    )
    assert r1.status_code == 404

    r2 = client.post(
        "/api/assets/nonexistent/handoff",
        json={"actor_from": "A", "actor_to": "B", "purpose": "P", "location": "L"},
    )
    assert r2.status_code == 404
