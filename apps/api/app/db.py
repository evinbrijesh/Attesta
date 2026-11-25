"""SQLite WAL-mode persistence with database-enforced append-only custody triggers."""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS cases (
    case_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS evidence_assets (
    asset_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES cases(case_id),
    filename TEXT NOT NULL,
    media_type TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    blake3 TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    storage_path TEXT NOT NULL,
    ingested_at TEXT NOT NULL,
    UNIQUE(case_id, sha256, blake3)
);

CREATE TABLE IF NOT EXISTS custody_events (
    event_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES cases(case_id),
    asset_id TEXT NOT NULL REFERENCES evidence_assets(asset_id),
    seq INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    actor_from TEXT NOT NULL,
    actor_to TEXT NOT NULL,
    purpose TEXT NOT NULL,
    location TEXT NOT NULL,
    occurred_at_utc TEXT NOT NULL,
    prev_hash TEXT NOT NULL,
    event_hash TEXT NOT NULL,
    signer_public_key TEXT NOT NULL,
    signature TEXT NOT NULL,
    notes TEXT NOT NULL DEFAULT '',
    UNIQUE(asset_id, seq)
);

CREATE TRIGGER IF NOT EXISTS prevent_custody_update
BEFORE UPDATE ON custody_events
BEGIN
    SELECT RAISE(ABORT, 'custody_events is append-only: UPDATE forbidden');
END;

CREATE TRIGGER IF NOT EXISTS prevent_custody_delete
BEFORE DELETE ON custody_events
BEGIN
    SELECT RAISE(ABORT, 'custody_events is append-only: DELETE forbidden');
END;

CREATE TABLE IF NOT EXISTS section63_certificates (
    cert_id TEXT PRIMARY KEY,
    asset_id TEXT NOT NULL REFERENCES evidence_assets(asset_id),
    case_id TEXT NOT NULL REFERENCES cases(case_id),
    custodian_name TEXT NOT NULL,
    custodian_designation TEXT NOT NULL,
    expert_name TEXT NOT NULL,
    expert_designation TEXT NOT NULL,
    part_a_text TEXT NOT NULL,
    part_b_text TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    blake3 TEXT NOT NULL,
    head_event_hash TEXT NOT NULL,
    signed_at_utc TEXT NOT NULL,
    pdf_path TEXT NOT NULL,
    pdf_sha256 TEXT NOT NULL
);
"""


def get_connection(db_path: Path) -> sqlite3.Connection:
    """Open a SQLite connection configured with WAL mode and Row factory."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_SQL)
    return conn
