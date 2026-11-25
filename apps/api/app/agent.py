"""AI Forensic Audit Agent: deterministic log parser, custody auditor, and grounded Section 63(4) drafter."""

from __future__ import annotations

import json
import os
import re
import sqlite3
from datetime import datetime
from typing import Any

import httpx
from pydantic import BaseModel, Field

from app.custody import verify_asset_chain
from app.forensics import analyze_bytes

SHA256_RE = re.compile(r"\b[a-fA-F0-9]{64}\b")
ISO_TS_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:?\d{2})?\b")


class ParsedLog(BaseModel):
    """Structured extraction from a forensic acquisition log."""

    format_detected: str
    operator_or_examiner: str | None = None
    device_or_source: str | None = None
    declared_sha256: str | None = None
    timestamps: list[str] = Field(default_factory=list)
    timezone_notes: list[str] = Field(default_factory=list)
    software_tags: list[str] = Field(default_factory=list)
    raw_excerpt: str = ""


class AuditFlag(BaseModel):
    """Deterministic or agent-detected custody/integrity flag."""

    code: str
    severity: str  # "critical" | "warning" | "info"
    message: str
    citation: str


class AuditResult(BaseModel):
    """Structured output of the Attesta AI Forensic Audit Agent."""

    asset_id: str
    parsed_log: ParsedLog | None = None
    flags: list[AuditFlag] = Field(default_factory=list)
    part_a_draft: str
    part_b_draft: str
    drafter_mode: str  # "gemini" | "ollama" | "deterministic-grounded"
    disclaimer: str = (
        "Prepared for human expert review and sign-off under BSA Section 63(4). "
        "Attesta does not autonomously sign certificates or determine judicial admissibility."
    )


def _extract_first(pattern: str, text: str) -> str | None:
    m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
    return m.group(1).strip() if m else None


def parse_acquisition_log(log_text: str) -> ParsedLog:
    """Parse 5 forensic log formats deterministically (dd, ewfacquire, autopsy, exiftool_json, officer_notes)."""
    stripped = log_text.strip()
    if not stripped:
        return ParsedLog(format_detected="empty", raw_excerpt="")

    # 1. ExifTool JSON
    if stripped.startswith("[") or stripped.startswith("{"):
        try:
            data = json.loads(stripped)
            rec = data[0] if isinstance(data, list) and data else data
            if isinstance(rec, dict) and ("ExifToolVersion" in rec or "SourceFile" in rec or "MIMEType" in rec):
                ts = [str(rec[k]) for k in ("DateTimeOriginal", "ModifyDate", "CreateDate") if k in rec]
                sw = [str(rec["Software"])] if "Software" in rec else []
                device = " ".join(str(rec[k]) for k in ("Make", "Model") if k in rec).strip() or rec.get("SourceFile")
                return ParsedLog(
                    format_detected="exiftool_json",
                    device_or_source=device,
                    timestamps=ts,
                    software_tags=sw,
                    raw_excerpt=stripped[:240],
                )
        except json.JSONDecodeError:
            pass

    # 2. ewfacquire
    if "ewfacquire" in stripped.lower():
        return ParsedLog(
            format_detected="ewfacquire",
            operator_or_examiner=_extract_first(r"Examiner Name:\s*(.+)", stripped),
            device_or_source=_extract_first(r"Media Type:\s*(.+)", stripped),
            declared_sha256=(SHA256_RE.search(stripped).group(0).lower() if SHA256_RE.search(stripped) else None),
            timestamps=ISO_TS_RE.findall(stripped),
            timezone_notes=[
                ln.strip()
                for ln in stripped.splitlines()
                if any(tok in ln.upper() for tok in ("IST", "UTC", "RTC", "TIMEZONE"))
            ],
            raw_excerpt=stripped[:240],
        )

    # 3. dd acquisition log
    if "dd " in stripped.lower() or "write_blocker" in stripped.lower():
        return ParsedLog(
            format_detected="dd",
            operator_or_examiner=_extract_first(r"OPERATOR:\s*(.+)", stripped),
            device_or_source=_extract_first(r"WRITE_BLOCKER:\s*(.+)", stripped)
            or _extract_first(r"if=(\S+)", stripped),
            declared_sha256=(SHA256_RE.search(stripped).group(0).lower() if SHA256_RE.search(stripped) else None),
            timestamps=ISO_TS_RE.findall(stripped),
            raw_excerpt=stripped[:240],
        )

    # 4. Autopsy summary
    if "autopsy" in stripped.lower() or "ingest modules" in stripped.lower():
        return ParsedLog(
            format_detected="autopsy",
            operator_or_examiner=_extract_first(r"Examiner:\s*(.+)", stripped),
            device_or_source=_extract_first(r"Data Source:\s*(.+)", stripped),
            declared_sha256=(SHA256_RE.search(stripped).group(0).lower() if SHA256_RE.search(stripped) else None),
            timestamps=ISO_TS_RE.findall(stripped),
            timezone_notes=[
                ln.strip() for ln in stripped.splitlines() if "timezone" in ln.lower()
            ],
            raw_excerpt=stripped[:240],
        )

    # 5. Free-text officer seizure notes
    return ParsedLog(
        format_detected="officer_notes",
        operator_or_examiner=_extract_first(r"(?:complainant|IO|officer|examiner)[:\s]+([A-Za-z .]+)", stripped),
        device_or_source=_extract_first(r"(?:on a|device:?)\s+([^\n.]+)", stripped),
        declared_sha256=(SHA256_RE.search(stripped).group(0).lower() if SHA256_RE.search(stripped) else None),
        timestamps=ISO_TS_RE.findall(stripped),
        timezone_notes=[
            ln.strip()
            for ln in stripped.splitlines()
            if any(tok in ln.upper() for tok in ("IST", "UTC", "GAP", "WHATSAPP"))
        ],
        raw_excerpt=stripped[:240],
    )


def _parse_iso(ts: str) -> datetime | None:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def audit_custody_and_log(
    conn: sqlite3.Connection,
    *,
    asset_id: str,
    log_text: str = "",
) -> tuple[dict[str, Any], list[dict[str, Any]], ParsedLog | None, list[AuditFlag]]:
    """Run deterministic chain, hash, timestamp, and TRACE-advisory checks."""
    asset_row = conn.execute("SELECT * FROM evidence_assets WHERE asset_id = ?", (asset_id,)).fetchone()
    if asset_row is None:
        raise KeyError(f"Asset not found: {asset_id}")
    asset = dict(asset_row)
    events = [
        dict(r)
        for r in conn.execute("SELECT * FROM custody_events WHERE asset_id = ? ORDER BY seq ASC", (asset_id,)).fetchall()
    ]

    flags: list[AuditFlag] = []
    verification = verify_asset_chain(conn, asset_id)
    if not verification.valid:
        for err in verification.errors:
            flags.append(
                AuditFlag(
                    code="CHAIN_INTEGRITY_ERROR",
                    severity="critical",
                    message=err,
                    citation=f"[asset:{asset_id}]",
                )
            )

    # Check chronological monotonicity & large custody gaps (> 2 hours)
    prev_dt: datetime | None = None
    prev_ev: dict[str, Any] | None = None
    for ev in events:
        cur_dt = _parse_iso(ev["occurred_at_utc"])
        if cur_dt and prev_dt and prev_ev:
            delta_sec = (cur_dt - prev_dt).total_seconds()
            if delta_sec < 0:
                flags.append(
                    AuditFlag(
                        code="CHRONOLOGICAL_INVERSION",
                        severity="critical",
                        message=f"Event seq={ev['seq']} occurs before seq={prev_ev['seq']}",
                        citation=f"[event:{ev['event_id']}]",
                    )
                )
            elif delta_sec > 7200:
                flags.append(
                    AuditFlag(
                        code="CUSTODY_TIME_GAP",
                        severity="warning",
                        message=f"{delta_sec / 3600:.1f}h gap between seq={prev_ev['seq']} and seq={ev['seq']}",
                        citation=f"[event:{ev['event_id']}]",
                    )
                )
        prev_dt = cur_dt
        prev_ev = ev

    parsed: ParsedLog | None = None
    if log_text.strip():
        parsed = parse_acquisition_log(log_text)
        if parsed.declared_sha256 and parsed.declared_sha256 != asset["sha256"]:
            flags.append(
                AuditFlag(
                    code="LOG_HASH_MISMATCH",
                    severity="critical",
                    message=f"Log SHA-256 ({parsed.declared_sha256[:12]}...) != intake SHA-256 ({asset['sha256'][:12]}...)",
                    citation=f"[hash:{asset['sha256'][:12]}]",
                )
            )
        lower_log = log_text.lower()
        if "ist" in lower_log and "utc" in lower_log:
            flags.append(
                AuditFlag(
                    code="TIMEZONE_MIXUP_RISK",
                    severity="warning",
                    message="Acquisition log mixes IST and UTC timestamps; verify chronological alignment.",
                    citation=f"[asset:{asset_id}]",
                )
            )
        if "rtc" in lower_log and ("behind" in lower_log or "skew" in lower_log):
            flags.append(
                AuditFlag(
                    code="CLOCK_SKEW_NOTED",
                    severity="warning",
                    message="Source device RTC clock skew noted in acquisition log.",
                    citation=f"[asset:{asset_id}]",
                )
            )
        if "whatsapp" in lower_log:
            flags.append(
                AuditFlag(
                    code="REENCODING_RISK",
                    severity="warning",
                    message="Log mentions WhatsApp transfer prior to sealing; messaging apps re-encode media and alter hashes.",
                    citation=f"[asset:{asset_id}]",
                )
            )
        if "gap" in lower_log:
            flags.append(
                AuditFlag(
                    code="LOG_CUSTODY_GAP_MENTIONED",
                    severity="warning",
                    message="Acquisition notes mention an unlogged custody gap.",
                    citation=f"[asset:{asset_id}]",
                )
            )

    # Advisory TRACE forensics flags (if file exists on disk)
    from pathlib import Path

    p = Path(asset["storage_path"])
    if p.exists():
        fx = analyze_bytes(p.read_bytes(), declared_media_type=asset["media_type"])
        for f in fx.flags:
            flags.append(
                AuditFlag(
                    code=f"ADVISORY_{f.code}",
                    severity="info",
                    message=f"[Advisory Only] {f.message}",
                    citation=f"[asset:{asset_id}]",
                )
            )

    return asset, events, parsed, flags


def _deterministic_drafts(
    asset: dict[str, Any],
    events: list[dict[str, Any]],
    parsed: ParsedLog | None,
    flags: list[AuditFlag],
) -> tuple[str, str]:
    """Generate strictly citation-grounded Part A and Part B drafts without an LLM."""
    first = events[0]
    last = events[-1]
    hash_cite = f"[hash:{asset['sha256'][:12]}]"
    part_a = (
        f"I, {first['actor_from']}, declare that the electronic record '{asset['filename']}' "
        f"({asset['size_bytes']} bytes, {asset['media_type']}) was produced from lawful custody at "
        f"{first['location']} on {first['occurred_at_utc']} [event:{first['event_id']}]. "
        f"Its cryptographic SHA-256 fingerprint at intake is {asset['sha256']} {hash_cite} "
        f"(BLAKE3: {asset['blake3'][:16]}...)."
    )

    flag_summary = (
        "No integrity or custody anomalies were detected."
        if not flags
        else f"{len(flags)} observation(s) flagged for expert review: "
        + "; ".join(f"{f.code} {f.citation}" for f in flags[:4])
        + "."
    )
    log_note = (
        f" Acquisition log format '{parsed.format_detected}' parsed"
        + (f" (operator: {parsed.operator_or_examiner})" if parsed.operator_or_examiner else "")
        + "."
        if parsed
        else ""
    )
    part_b = (
        f"Technical examination confirms {len(events)} hash-chained Ed25519-signed custody event(s) "
        f"from {first['occurred_at_utc']} [event:{first['event_id']}] to {last['occurred_at_utc']} "
        f"[event:{last['event_id']}], matching intake digest {asset['sha256']} {hash_cite}.{log_note} "
        f"{flag_summary}"
    )
    return part_a, part_b


def _try_gemini_draft(prompt: str) -> tuple[str, str] | None:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.1},
    }
    try:
        with httpx.Client(timeout=12.0) as client:
            resp = client.post(url, json=body)
            if resp.status_code != 200:
                return None
            text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(text)
            if "part_a_draft" in parsed and "part_b_draft" in parsed:
                return str(parsed["part_a_draft"]), str(parsed["part_b_draft"])
    except Exception:
        return None
    return None


def _try_ollama_draft(prompt: str) -> tuple[str, str] | None:
    base = os.getenv("OLLAMA_BASE_URL", "").strip()
    model = os.getenv("OLLAMA_MODEL", "qwen2.5:7b").strip()
    if not base:
        return None
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(
                f"{base.rstrip('/')}/api/generate",
                json={"model": model, "prompt": prompt, "format": "json", "stream": False},
            )
            if resp.status_code != 200:
                return None
            parsed = json.loads(resp.json().get("response", "{}"))
            if "part_a_draft" in parsed and "part_b_draft" in parsed:
                return str(parsed["part_a_draft"]), str(parsed["part_b_draft"])
    except Exception:
        return None
    return None


def run_audit_agent(conn: sqlite3.Connection, *, asset_id: str, log_text: str = "") -> AuditResult:
    """Execute the full AI Forensic Audit Agent pipeline and return a grounded AuditResult."""
    asset, events, parsed, flags = audit_custody_and_log(conn, asset_id=asset_id, log_text=log_text)

    context = {
        "asset": {
            "asset_id": asset["asset_id"],
            "filename": asset["filename"],
            "sha256": asset["sha256"],
            "blake3": asset["blake3"],
            "size_bytes": asset["size_bytes"],
        },
        "events": [
            {
                "event_id": e["event_id"],
                "seq": e["seq"],
                "actor_from": e["actor_from"],
                "actor_to": e["actor_to"],
                "location": e["location"],
                "occurred_at_utc": e["occurred_at_utc"],
            }
            for e in events
        ],
        "flags": [f.model_dump() for f in flags],
    }
    prompt = (
        "You are a forensic documentation assistant preparing a BSA Section 63(4) certificate draft.\n"
        "RULES: (1) Cite verified [event:<id>] and [hash:<first12>] tokens in every factual sentence. "
        "(2) Do NOT invent facts. (3) Never claim the evidence is 'court-admissible'.\n"
        f"Return JSON with keys 'part_a_draft' and 'part_b_draft'.\nDATA:\n{json.dumps(context)}"
    )

    drafter_mode = "deterministic-grounded"
    drafts = _try_gemini_draft(prompt)
    if drafts:
        drafter_mode = "gemini"
    else:
        drafts = _try_ollama_draft(prompt)
        if drafts:
            drafter_mode = "ollama"
        else:
            drafts = _deterministic_drafts(asset, events, parsed, flags)

    return AuditResult(
        asset_id=asset_id,
        parsed_log=parsed,
        flags=flags,
        part_a_draft=drafts[0],
        part_b_draft=drafts[1],
        drafter_mode=drafter_mode,
    )
