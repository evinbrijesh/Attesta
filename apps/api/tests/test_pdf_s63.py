"""Tests for Day 7 BSA Section 63(4) PDF generation, human sign-off, and bundle embedding."""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app

VERIFY_PKG = Path(__file__).resolve().parents[3] / "packages" / "verify-coc"
if str(VERIFY_PKG) not in sys.path:
    sys.path.insert(0, str(VERIFY_PKG))

from verify_coc.verifier import verify_bundle  # noqa: E402


def test_sign_s63_generates_pdf_and_embeds_in_verified_bundle(tmp_path: Path) -> None:
    app = create_app(db_path=tmp_path / "s63.db", storage_dir=tmp_path / "store")
    client = TestClient(app)

    cid = client.post("/api/cases", json={"title": "Section 63 Case"}).json()["case_id"]
    asset_id = client.post(
        f"/api/cases/{cid}/ingest",
        files={"file": ("cctv.mp4", b"synthetic-cctv-bytes", "video/mp4")},
        data={"custodian": "SI Rajesh Kumar"},
    ).json()["asset_id"]

    sign_resp = client.post(
        f"/api/assets/{asset_id}/sign-s63",
        json={
            "custodian_name": "SI Rajesh Kumar",
            "custodian_designation": "Investigating Officer, Cyber PS",
            "expert_name": "Dr. Ananya Rao",
            "expert_designation": "Senior Forensic Examiner, FSL",
            "part_a_text": "Electronic record cctv.mp4 produced from lawful custody with SHA-256 disclosed.",
            "part_b_text": "Cryptographic hash chain and Ed25519 signatures verified intact across all handoffs.",
            "notify_n8n": False,
        },
    )
    assert sign_resp.status_code == 201
    assert sign_resp.json()["cert_id"].startswith("s63_")

    pdf_resp = client.get(f"/api/assets/{asset_id}/certificate.pdf")
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"] == "application/pdf"
    assert pdf_resp.content.startswith(b"%PDF-")

    bundle_resp = client.get(f"/api/assets/{asset_id}/bundle")
    assert bundle_resp.status_code == 200
    bundle_zip = tmp_path / "signed_bundle.zip"
    bundle_zip.write_bytes(bundle_resp.content)

    with zipfile.ZipFile(bundle_zip, "r") as zf:
        assert "certificate_s63.pdf" in zf.namelist()

    report = verify_bundle(bundle_zip)
    assert report.valid is True
    assert report.event_count == 2  # INGEST + PART_B_SIGN_OFF


def test_sign_s63_refuses_tampered_chain(tmp_path: Path) -> None:
    storage = tmp_path / "store"
    app = create_app(db_path=tmp_path / "s63_bad.db", storage_dir=storage)
    client = TestClient(app)

    cid = client.post("/api/cases", json={"title": "Tamper Case"}).json()["case_id"]
    asset_id = client.post(
        f"/api/cases/{cid}/ingest",
        files={"file": ("doc.pdf", b"clean-bytes", "application/pdf")},
        data={"custodian": "Officer"},
    ).json()["asset_id"]

    stored = storage / cid / asset_id / "doc.pdf"
    stored.write_bytes(b"tampered-bytes")

    sign_resp = client.post(
        f"/api/assets/{asset_id}/sign-s63",
        json={
            "custodian_name": "Officer",
            "expert_name": "Expert",
            "part_a_text": "Part A declaration text for testing.",
            "part_b_text": "Part B certification text for testing.",
            "notify_n8n": False,
        },
    )
    assert sign_resp.status_code == 409
