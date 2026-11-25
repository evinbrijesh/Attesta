"""FastAPI application for Attesta."""

from __future__ import annotations

import hashlib
import os
import sqlite3
import uuid
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.agent import run_audit_agent
from app.custody import (
    create_case,
    export_bundle,
    ingest_evidence,
    record_handoff,
    utc_now_iso,
    verify_asset_chain,
)
from app.db import get_connection
from app.forensics import analyze_bytes
from app.pdf_s63 import Section63CertificateData, render_section63_pdf
from app.sponsors import fetch_bsa_section63_reference, notify_n8n


class CaseCreateRequest(BaseModel):
    """Request schema for creating a case."""

    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)


class HandoffRequest(BaseModel):
    """Request schema for recording a custody handoff."""

    actor_from: str = Field(..., min_length=1)
    actor_to: str = Field(..., min_length=1)
    purpose: str = Field(..., min_length=1)
    location: str = Field(..., min_length=1)
    event_type: str = Field(default="HANDOFF")
    notes: str = Field(default="")


class SignSection63Request(BaseModel):
    """Request schema for human expert review and BSA Section 63(4) sign-off."""

    custodian_name: str = Field(..., min_length=1)
    custodian_designation: str = Field(default="Custodian / Investigating Officer")
    expert_name: str = Field(..., min_length=1)
    expert_designation: str = Field(default="Forensic / Technical Expert")
    part_a_text: str = Field(..., min_length=10)
    part_b_text: str = Field(..., min_length=10)
    notify_n8n: bool = Field(default=False)


def _load_root_env() -> None:
    """Load key=value pairs from repo-root .env if not already in os.environ."""
    env_path = Path(__file__).resolve().parents[3] / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        os.environ.setdefault(key.strip(), val.strip())


def create_app(db_path: Path | None = None, storage_dir: Path | None = None) -> FastAPI:
    """Create and configure the FastAPI application instance."""
    _load_root_env()
    resolved_db = db_path or Path(os.getenv("ATTESTA_DB_PATH", "./data/attesta.db"))
    resolved_storage = storage_dir or Path(os.getenv("ATTESTA_STORAGE_DIR", "./data/evidence"))
    resolved_bundles = resolved_storage.parent / "bundles"

    app = FastAPI(title="Attesta API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    conn = get_connection(resolved_db)

    def get_db() -> sqlite3.Connection:
        return conn

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "attesta-api"}

    @app.get("/api/cases")
    def api_list_cases(db: sqlite3.Connection = Depends(get_db)) -> list[dict[str, object]]:
        rows = db.execute("SELECT case_id, title, description, created_at FROM cases ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]

    @app.post("/api/cases", status_code=201)
    def api_create_case(body: CaseCreateRequest, db: sqlite3.Connection = Depends(get_db)) -> dict[str, str]:
        return create_case(db, title=body.title, description=body.description)

    @app.get("/api/cases/{case_id}/assets")
    def api_list_assets(case_id: str, db: sqlite3.Connection = Depends(get_db)) -> list[dict[str, object]]:
        rows = db.execute(
            "SELECT asset_id, case_id, filename, media_type, sha256, blake3, size_bytes, ingested_at FROM evidence_assets WHERE case_id = ? ORDER BY ingested_at DESC",
            (case_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    @app.get("/api/assets/{asset_id}/events")
    def api_list_events(asset_id: str, db: sqlite3.Connection = Depends(get_db)) -> list[dict[str, object]]:
        rows = db.execute(
            "SELECT event_id, case_id, asset_id, seq, event_type, actor_from, actor_to, purpose, location, occurred_at_utc, prev_hash, event_hash, signer_public_key, signature, notes FROM custody_events WHERE asset_id = ? ORDER BY seq ASC",
            (asset_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    @app.post("/api/cases/{case_id}/ingest")
    async def api_ingest(
        case_id: str,
        file: UploadFile = File(...),
        custodian: str = Form(...),
        location: str = Form("Field Intake"),
        purpose: str = Form("Initial evidence seizure & intake"),
        db: sqlite3.Connection = Depends(get_db),
    ) -> dict[str, object]:
        case_row = db.execute("SELECT case_id FROM cases WHERE case_id = ?", (case_id,)).fetchone()
        if case_row is None:
            raise HTTPException(status_code=404, detail="Case not found")

        raw = await file.read()
        res = ingest_evidence(
            db,
            case_id=case_id,
            filename=file.filename or "evidence.bin",
            media_type=file.content_type or "application/octet-stream",
            data=raw,
            storage_dir=resolved_storage,
            custodian=custodian,
            location=location,
            purpose=purpose,
        )
        return {
            "asset_id": res.asset_id,
            "sha256": res.sha256,
            "blake3": res.blake3,
            "size_bytes": res.size_bytes,
            "idempotent_hit": res.idempotent_hit,
            "intake_event_id": res.intake_event_id,
        }

    @app.post("/api/assets/{asset_id}/handoff", status_code=201)
    def api_handoff(
        asset_id: str,
        body: HandoffRequest,
        db: sqlite3.Connection = Depends(get_db),
    ) -> dict[str, object]:
        try:
            return record_handoff(
                db,
                asset_id=asset_id,
                actor_from=body.actor_from,
                actor_to=body.actor_to,
                purpose=body.purpose,
                location=body.location,
                event_type=body.event_type,
                notes=body.notes,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/assets/{asset_id}/verify")
    def api_verify(asset_id: str, db: sqlite3.Connection = Depends(get_db)) -> dict[str, object]:
        res = verify_asset_chain(db, asset_id)
        return {
            "valid": res.valid,
            "asset_id": res.asset_id,
            "event_count": res.event_count,
            "file_hash_match": res.file_hash_match,
            "errors": res.errors,
        }

    @app.get("/api/assets/{asset_id}/bundle")
    def api_bundle(asset_id: str, db: sqlite3.Connection = Depends(get_db)) -> FileResponse:
        out_zip = resolved_bundles / f"{asset_id}_bundle.zip"
        try:
            export_bundle(db, asset_id=asset_id, output_zip=out_zip)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return FileResponse(path=str(out_zip), media_type="application/zip", filename=f"{asset_id}_bundle.zip")

    @app.get("/api/assets/{asset_id}/forensics")
    def api_forensics(asset_id: str, db: sqlite3.Connection = Depends(get_db)) -> dict[str, object]:
        row = db.execute("SELECT storage_path, media_type FROM evidence_assets WHERE asset_id = ?", (asset_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Asset not found")
        file_path = Path(row["storage_path"])
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Evidence file missing on disk")
        report = analyze_bytes(file_path.read_bytes(), declared_media_type=row["media_type"])
        return {"asset_id": asset_id, **report.to_dict()}

    @app.post("/api/assets/{asset_id}/audit")
    def api_audit(
        asset_id: str,
        body: dict[str, object] | None = None,
        db: sqlite3.Connection = Depends(get_db),
    ) -> dict[str, object]:
        payload = body or {}
        log_text = str(payload.get("log_text", ""))
        send_n8n = bool(payload.get("notify_n8n", False))
        try:
            result = run_audit_agent(db, asset_id=asset_id, log_text=log_text)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        n8n_status = None
        if send_n8n:
            asset = db.execute("SELECT case_id, sha256 FROM evidence_assets WHERE asset_id = ?", (asset_id,)).fetchone()
            n8n_status = notify_n8n(
                "PART_A_SUBMITTED",
                {
                    "case_id": asset["case_id"] if asset else "",
                    "asset_id": asset_id,
                    "sha256": asset["sha256"] if asset else "",
                    "flag_count": len(result.flags),
                },
            )
        return {**result.model_dump(), "n8n_notification": n8n_status}

    @app.get("/api/legal/section63")
    def api_legal_section63(refresh: bool = False) -> dict[str, object]:
        return fetch_bsa_section63_reference(refresh_with_olostep=refresh)

    @app.post("/api/assets/{asset_id}/sign-s63", status_code=201)
    def api_sign_section63(
        asset_id: str,
        body: SignSection63Request,
        db: sqlite3.Connection = Depends(get_db),
    ) -> dict[str, object]:
        ver = verify_asset_chain(db, asset_id)
        if not ver.valid:
            raise HTTPException(status_code=409, detail=f"Cannot sign tampered/invalid chain: {'; '.join(ver.errors)}")

        asset = dict(db.execute("SELECT * FROM evidence_assets WHERE asset_id = ?", (asset_id,)).fetchone())
        case = dict(db.execute("SELECT * FROM cases WHERE case_id = ?", (asset["case_id"],)).fetchone())

        sign_event = record_handoff(
            db,
            asset_id=asset_id,
            actor_from=body.custodian_name,
            actor_to=body.expert_name,
            purpose="Human Expert Sign-Off under BSA Section 63(4) Part B",
            location="Expert Review Desk",
            event_type="PART_B_SIGN_OFF",
            notes=f"expert={body.expert_name}",
        )
        signed_at = utc_now_iso()
        cert_id = f"s63_{uuid.uuid4().hex[:12]}"
        pdf_path = resolved_storage.parent / "certificates" / f"{asset_id}_{cert_id}.pdf"
        render_section63_pdf(
            Section63CertificateData(
                cert_id=cert_id,
                case_id=case["case_id"],
                case_title=case["title"],
                asset_id=asset_id,
                filename=asset["filename"],
                media_type=asset["media_type"],
                size_bytes=asset["size_bytes"],
                sha256=asset["sha256"],
                blake3=asset["blake3"],
                head_event_hash=sign_event["event_hash"],
                event_count=ver.event_count + 1,
                custodian_name=body.custodian_name,
                custodian_designation=body.custodian_designation,
                expert_name=body.expert_name,
                expert_designation=body.expert_designation,
                part_a_text=body.part_a_text,
                part_b_text=body.part_b_text,
                signed_at_utc=signed_at,
            ),
            pdf_path,
        )
        pdf_sha256 = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
        db.execute(
            """
            INSERT INTO section63_certificates
                (cert_id, asset_id, case_id, custodian_name, custodian_designation,
                 expert_name, expert_designation, part_a_text, part_b_text,
                 sha256, blake3, head_event_hash, signed_at_utc, pdf_path, pdf_sha256)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                cert_id,
                asset_id,
                case["case_id"],
                body.custodian_name,
                body.custodian_designation,
                body.expert_name,
                body.expert_designation,
                body.part_a_text,
                body.part_b_text,
                asset["sha256"],
                asset["blake3"],
                sign_event["event_hash"],
                signed_at,
                str(pdf_path),
                pdf_sha256,
            ),
        )
        db.commit()

        n8n_status = None
        if body.notify_n8n:
            n8n_status = notify_n8n(
                "PART_B_SIGNED",
                {
                    "case_id": case["case_id"],
                    "asset_id": asset_id,
                    "cert_id": cert_id,
                    "head_event_hash": sign_event["event_hash"],
                },
            )

        return {
            "cert_id": cert_id,
            "asset_id": asset_id,
            "signed_at_utc": signed_at,
            "pdf_sha256": pdf_sha256,
            "head_event_hash": sign_event["event_hash"],
            "n8n_notification": n8n_status,
        }

    @app.get("/api/assets/{asset_id}/certificate.pdf")
    def api_get_certificate_pdf(asset_id: str, db: sqlite3.Connection = Depends(get_db)) -> FileResponse:
        row = db.execute(
            "SELECT pdf_path, cert_id FROM section63_certificates WHERE asset_id = ? ORDER BY signed_at_utc DESC LIMIT 1",
            (asset_id,),
        ).fetchone()
        if row is None or not Path(row["pdf_path"]).exists():
            raise HTTPException(status_code=404, detail="Signed Section 63(4) certificate not found")
        return FileResponse(path=row["pdf_path"], media_type="application/pdf", filename=f"{asset_id}_{row['cert_id']}.pdf")

    return app


app = create_app()
