"""Tests for Day 2 metadata extraction, TRACE advisory flags, and 5 synthetic log fixtures."""

from __future__ import annotations

import io
import json
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from app.forensics import analyze_bytes
from app.main import create_app


def _make_jpeg_bytes(*, software: str | None = None) -> bytes:
    img = Image.new("RGB", (64, 64), color=(120, 45, 200))
    buf = io.BytesIO()
    if software:
        exif = Image.Exif()
        exif[0x0131] = software  # Software tag
        exif[0x010F] = "Apple"   # Make tag
        img.save(buf, format="JPEG", exif=exif.tobytes())
    else:
        img.save(buf, format="JPEG")
    return buf.getvalue()


def test_forensics_flags_missing_exif_as_advisory() -> None:
    report = analyze_bytes(_make_jpeg_bytes(), declared_media_type="image/jpeg")
    assert report.is_image is True
    assert report.advisory_only is True
    assert report.detected_format == "JPEG"
    assert report.width == 64 and report.height == 64
    codes = {f.code for f in report.flags}
    assert "MISSING_EXIF" in codes
    assert all(f.advisory_only is True for f in report.flags)


def test_forensics_flags_editing_software_tag() -> None:
    report = analyze_bytes(_make_jpeg_bytes(software="Adobe Photoshop 25.4"), declared_media_type="image/jpeg")
    assert report.is_image is True
    assert report.exif.get("Software") == "Adobe Photoshop 25.4"
    codes = {f.code for f in report.flags}
    assert "EDITING_SOFTWARE_TAG" in codes
    assert "MISSING_EXIF" not in codes


def test_forensics_handles_non_image_bytes_gracefully() -> None:
    report = analyze_bytes(b"not-an-image-stream", declared_media_type="video/mp4")
    assert report.is_image is False
    assert report.detected_format == "video/mp4"
    assert report.flags == []


def test_forensics_endpoint_returns_advisory_report(tmp_path: Path) -> None:
    app = create_app(db_path=tmp_path / "f.db", storage_dir=tmp_path / "store")
    client = TestClient(app)

    cid = client.post("/api/cases", json={"title": "Forensics Case"}).json()["case_id"]
    ingest = client.post(
        f"/api/cases/{cid}/ingest",
        files={"file": ("photo.jpg", _make_jpeg_bytes(software="GIMP 2.10"), "image/jpeg")},
        data={"custodian": "IO Sharma"},
    )
    asset_id = ingest.json()["asset_id"]

    resp = client.get(f"/api/assets/{asset_id}/forensics")
    assert resp.status_code == 200
    body = resp.json()
    assert body["advisory_only"] is True
    assert body["is_image"] is True
    assert any(f["code"] == "EDITING_SOFTWARE_TAG" for f in body["flags"])


def test_five_synthetic_log_fixtures_present_and_valid() -> None:
    logs_dir = Path(__file__).resolve().parents[3] / "fixtures" / "logs"
    expected = [
        "01_dd_acquisition.log",
        "02_ewfacquire.log",
        "03_autopsy_summary.txt",
        "04_exiftool_dump.json",
        "05_officer_notes.txt",
    ]
    for name in expected:
        p = logs_dir / name
        assert p.exists(), f"Missing fixture: {p}"
        assert p.read_text(encoding="utf-8").strip() != ""

    exif_json = json.loads((logs_dir / "04_exiftool_dump.json").read_text(encoding="utf-8"))
    assert isinstance(exif_json, list) and "Photoshop" in exif_json[0]["Software"]
