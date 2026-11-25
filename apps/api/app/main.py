"""FastAPI application for Attesta."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.custody import (
    create_case,
    export_bundle,
    ingest_evidence,
    record_handoff,
    verify_asset_chain,
)
from app.db import get_connection
from app.forensics import analyze_bytes


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


def create_app(db_path: Path | None = None, storage_dir: Path | None = None) -> FastAPI:
    """Create and configure the FastAPI application instance."""
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

    return app


app = create_app()
