"""Core chain-of-custody ledger, verification, and tamper-evident bundle export."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.crypto import (
    GENESIS_HASH,
    KeyPair,
    compute_digests,
    compute_event_hash,
    generate_keypair,
    sign_event_hash,
    verify_event_signature,
)


def utc_now_iso() -> str:
    """Return current UTC timestamp in ISO-8601 format with Z suffix."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _build_event_payload(
    *,
    event_id: str,
    case_id: str,
    asset_id: str,
    seq: int,
    event_type: str,
    actor_from: str,
    actor_to: str,
    purpose: str,
    location: str,
    occurred_at_utc: str,
    notes: str,
) -> dict[str, Any]:
    """Build the canonical payload dictionary hashed into event_hash."""
    return {
        "event_id": event_id,
        "case_id": case_id,
        "asset_id": asset_id,
        "seq": seq,
        "event_type": event_type,
        "actor_from": actor_from,
        "actor_to": actor_to,
        "purpose": purpose,
        "location": location,
        "occurred_at_utc": occurred_at_utc,
        "notes": notes,
    }


@dataclass(frozen=True)
class IngestResult:
    """Result of idempotent evidence ingestion."""

    asset_id: str
    sha256: str
    blake3: str
    size_bytes: int
    idempotent_hit: bool
    intake_event_id: str


@dataclass(frozen=True)
class ChainVerificationResult:
    """Result of full cryptographic chain & file integrity verification."""

    valid: bool
    asset_id: str
    event_count: int
    file_hash_match: bool
    errors: list[str]


def create_case(conn: sqlite3.Connection, *, title: str, description: str = "", case_id: str | None = None) -> dict[str, Any]:
    """Create a new case record."""
    cid = case_id or f"case_{uuid.uuid4().hex[:12]}"
    now = utc_now_iso()
    conn.execute(
        "INSERT INTO cases (case_id, title, description, created_at) VALUES (?, ?, ?, ?)",
        (cid, title, description, now),
    )
    conn.commit()
    return {"case_id": cid, "title": title, "description": description, "created_at": now}


def ingest_evidence(
    conn: sqlite3.Connection,
    *,
    case_id: str,
    filename: str,
    media_type: str,
    data: bytes,
    storage_dir: Path,
    custodian: str,
    location: str = "Field Intake",
    purpose: str = "Initial evidence seizure & intake",
    keypair: KeyPair | None = None,
    occurred_at_utc: str | None = None,
) -> IngestResult:
    """Ingest an evidence file idempotently, computing SHA-256 + BLAKE3 and logging event seq=0."""
    digest = compute_digests(data)

    existing = conn.execute(
        "SELECT asset_id, sha256, blake3, size_bytes FROM evidence_assets WHERE case_id = ? AND sha256 = ? AND blake3 = ?",
        (case_id, digest.sha256, digest.blake3_hex),
    ).fetchone()

    if existing is not None:
        first_event = conn.execute(
            "SELECT event_id FROM custody_events WHERE asset_id = ? AND seq = 0",
            (existing["asset_id"],),
        ).fetchone()
        return IngestResult(
            asset_id=existing["asset_id"],
            sha256=existing["sha256"],
            blake3=existing["blake3"],
            size_bytes=existing["size_bytes"],
            idempotent_hit=True,
            intake_event_id=first_event["event_id"] if first_event else "",
        )

    asset_id = f"ast_{uuid.uuid4().hex[:12]}"
    safe_name = Path(filename).name or "evidence.bin"
    asset_dir = storage_dir / case_id / asset_id
    asset_dir.mkdir(parents=True, exist_ok=True)
    file_path = asset_dir / safe_name
    file_path.write_bytes(data)

    now = utc_now_iso()
    event_time = occurred_at_utc or now
    kp = keypair or generate_keypair()
    event_id = f"evt_{uuid.uuid4().hex[:12]}"

    payload = _build_event_payload(
        event_id=event_id,
        case_id=case_id,
        asset_id=asset_id,
        seq=0,
        event_type="INGEST",
        actor_from=custodian,
        actor_to="Attesta Vault",
        purpose=purpose,
        location=location,
        occurred_at_utc=event_time,
        notes=f"sha256={digest.sha256};blake3={digest.blake3_hex}",
    )
    event_hash = compute_event_hash(GENESIS_HASH, payload)
    signature = sign_event_hash(event_hash, kp.private_hex)

    conn.execute(
        """
        INSERT INTO evidence_assets
            (asset_id, case_id, filename, media_type, sha256, blake3, size_bytes, storage_path, ingested_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (asset_id, case_id, safe_name, media_type, digest.sha256, digest.blake3_hex, digest.size_bytes, str(file_path), now),
    )
    conn.execute(
        """
        INSERT INTO custody_events
            (event_id, case_id, asset_id, seq, event_type, actor_from, actor_to, purpose, location,
             occurred_at_utc, prev_hash, event_hash, signer_public_key, signature, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event_id,
            case_id,
            asset_id,
            0,
            "INGEST",
            custodian,
            "Attesta Vault",
            purpose,
            location,
            event_time,
            GENESIS_HASH,
            event_hash,
            kp.public_hex,
            signature,
            payload["notes"],
        ),
    )
    conn.commit()
    return IngestResult(
        asset_id=asset_id,
        sha256=digest.sha256,
        blake3=digest.blake3_hex,
        size_bytes=digest.size_bytes,
        idempotent_hit=False,
        intake_event_id=event_id,
    )


def record_handoff(
    conn: sqlite3.Connection,
    *,
    asset_id: str,
    actor_from: str,
    actor_to: str,
    purpose: str,
    location: str,
    event_type: str = "HANDOFF",
    notes: str = "",
    keypair: KeyPair | None = None,
    occurred_at_utc: str | None = None,
) -> dict[str, Any]:
    """Append a new hash-chained, Ed25519-signed custody event for an asset."""
    asset = conn.execute("SELECT case_id FROM evidence_assets WHERE asset_id = ?", (asset_id,)).fetchone()
    if asset is None:
        raise KeyError(f"Asset not found: {asset_id}")

    last = conn.execute(
        "SELECT seq, event_hash FROM custody_events WHERE asset_id = ? ORDER BY seq DESC LIMIT 1",
        (asset_id,),
    ).fetchone()
    if last is None:
        raise RuntimeError(f"Asset {asset_id} has no genesis INGEST event")

    seq = last["seq"] + 1
    prev_hash = last["event_hash"]
    event_id = f"evt_{uuid.uuid4().hex[:12]}"
    event_time = occurred_at_utc or utc_now_iso()
    kp = keypair or generate_keypair()

    payload = _build_event_payload(
        event_id=event_id,
        case_id=asset["case_id"],
        asset_id=asset_id,
        seq=seq,
        event_type=event_type,
        actor_from=actor_from,
        actor_to=actor_to,
        purpose=purpose,
        location=location,
        occurred_at_utc=event_time,
        notes=notes,
    )
    event_hash = compute_event_hash(prev_hash, payload)
    signature = sign_event_hash(event_hash, kp.private_hex)

    conn.execute(
        """
        INSERT INTO custody_events
            (event_id, case_id, asset_id, seq, event_type, actor_from, actor_to, purpose, location,
             occurred_at_utc, prev_hash, event_hash, signer_public_key, signature, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event_id,
            asset["case_id"],
            asset_id,
            seq,
            event_type,
            actor_from,
            actor_to,
            purpose,
            location,
            event_time,
            prev_hash,
            event_hash,
            kp.public_hex,
            signature,
            notes,
        ),
    )
    conn.commit()
    return {**payload, "prev_hash": prev_hash, "event_hash": event_hash, "signer_public_key": kp.public_hex, "signature": signature}


def verify_asset_chain(conn: sqlite3.Connection, asset_id: str) -> ChainVerificationResult:
    """Verify stored evidence digests, hash chain links, sequence numbers, and Ed25519 signatures."""
    errors: list[str] = []
    asset = conn.execute("SELECT * FROM evidence_assets WHERE asset_id = ?", (asset_id,)).fetchone()
    if asset is None:
        return ChainVerificationResult(valid=False, asset_id=asset_id, event_count=0, file_hash_match=False, errors=["Asset not found"])

    file_path = Path(asset["storage_path"])
    file_hash_match = False
    if not file_path.exists():
        errors.append(f"Evidence file missing on disk: {file_path}")
    else:
        actual = compute_digests(file_path.read_bytes())
        if actual.sha256 != asset["sha256"] or actual.blake3_hex != asset["blake3"]:
            errors.append("Evidence file digest mismatch (possible byte tampering)")
        else:
            file_hash_match = True

    rows = conn.execute(
        "SELECT * FROM custody_events WHERE asset_id = ? ORDER BY seq ASC",
        (asset_id,),
    ).fetchall()

    if not rows:
        errors.append("No custody events recorded")
        return ChainVerificationResult(valid=False, asset_id=asset_id, event_count=0, file_hash_match=file_hash_match, errors=errors)

    expected_prev = GENESIS_HASH
    for expected_seq, row in enumerate(rows):
        if row["seq"] != expected_seq:
            errors.append(f"Sequence gap at event {row['event_id']}: expected seq={expected_seq}, got {row['seq']}")
        if row["prev_hash"] != expected_prev:
            errors.append(f"Chain break at seq={row['seq']} ({row['event_id']}): prev_hash mismatch")

        payload = _build_event_payload(
            event_id=row["event_id"],
            case_id=row["case_id"],
            asset_id=row["asset_id"],
            seq=row["seq"],
            event_type=row["event_type"],
            actor_from=row["actor_from"],
            actor_to=row["actor_to"],
            purpose=row["purpose"],
            location=row["location"],
            occurred_at_utc=row["occurred_at_utc"],
            notes=row["notes"],
        )
        recomputed_hash = compute_event_hash(row["prev_hash"], payload)
        if recomputed_hash != row["event_hash"]:
            errors.append(f"Payload tamper at seq={row['seq']} ({row['event_id']}): event_hash mismatch")

        if not verify_event_signature(row["event_hash"], row["signature"], row["signer_public_key"]):
            errors.append(f"Invalid Ed25519 signature at seq={row['seq']} ({row['event_id']})")

        expected_prev = row["event_hash"]

    return ChainVerificationResult(
        valid=len(errors) == 0,
        asset_id=asset_id,
        event_count=len(rows),
        file_hash_match=file_hash_match,
        errors=errors,
    )


def export_bundle(conn: sqlite3.Connection, *, asset_id: str, output_zip: Path) -> Path:
    """Export a self-contained, offline-verifiable evidence bundle (.zip)."""
    verification = verify_asset_chain(conn, asset_id)
    if not verification.valid:
        raise ValueError(f"Refusing to export tampered/invalid chain: {'; '.join(verification.errors)}")

    asset = dict(conn.execute("SELECT * FROM evidence_assets WHERE asset_id = ?", (asset_id,)).fetchone())
    case = dict(conn.execute("SELECT * FROM cases WHERE case_id = ?", (asset["case_id"],)).fetchone())
    events = [dict(r) for r in conn.execute("SELECT * FROM custody_events WHERE asset_id = ? ORDER BY seq ASC", (asset_id,)).fetchall()]

    evidence_bytes = Path(asset["storage_path"]).read_bytes()
    evidence_arcname = f"evidence/{asset['filename']}"

    custody_jsonl = "\n".join(json.dumps(ev, sort_keys=True) for ev in events) + "\n"
    manifest = {
        "schema_version": "attesta-bundle-v1",
        "exported_at_utc": utc_now_iso(),
        "case": case,
        "asset": {
            "asset_id": asset["asset_id"],
            "filename": asset["filename"],
            "media_type": asset["media_type"],
            "sha256": asset["sha256"],
            "blake3": asset["blake3"],
            "size_bytes": asset["size_bytes"],
            "ingested_at": asset["ingested_at"],
            "bundle_path": evidence_arcname,
        },
        "event_count": len(events),
        "head_event_hash": events[-1]["event_hash"],
    }
    manifest_bytes = json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8")
    custody_bytes = custody_jsonl.encode("utf-8")

    entries = {
        evidence_arcname: evidence_bytes,
        "custody_log.jsonl": custody_bytes,
        "manifest.json": manifest_bytes,
    }
    sums_lines = [f"{hashlib.sha256(content).hexdigest()}  {name}" for name, content in sorted(entries.items())]
    sums_bytes = ("\n".join(sums_lines) + "\n").encode("utf-8")

    output_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, content in entries.items():
            zf.writestr(name, content)
        zf.writestr("sha256sums.txt", sums_bytes)

    return output_zip
