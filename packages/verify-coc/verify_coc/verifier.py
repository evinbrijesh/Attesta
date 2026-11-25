"""Pure offline zero-trust bundle verification logic (no CLI dependencies)."""

from __future__ import annotations

import hashlib
import json
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from blake3 import blake3
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

GENESIS_HASH = "0" * 64


@dataclass(frozen=True)
class BundleVerificationReport:
    """Structured offline verification result for an exported Attesta bundle."""

    valid: bool
    case_id: str
    asset_id: str
    event_count: int
    errors: list[str]


def _canonical_json(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _compute_event_hash(prev_hash: str, payload: dict[str, Any]) -> str:
    h = hashlib.sha256()
    h.update(prev_hash.encode("ascii"))
    h.update(b":")
    h.update(_canonical_json(payload))
    return h.hexdigest()


def _verify_sig(event_hash: str, signature_hex: str, public_hex: str) -> bool:
    try:
        pub = Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_hex))
        pub.verify(bytes.fromhex(signature_hex), event_hash.encode("ascii"))
        return True
    except (InvalidSignature, ValueError):
        return False


def verify_bundle(bundle_path: Path) -> BundleVerificationReport:
    """Verify an Attesta .zip bundle completely offline without server trust."""
    errors: list[str] = []
    if not bundle_path.exists():
        return BundleVerificationReport(False, "", "", 0, [f"Bundle not found: {bundle_path}"])

    with zipfile.ZipFile(bundle_path, "r") as zf:
        names = set(zf.namelist())
        required = {"manifest.json", "custody_log.jsonl", "sha256sums.txt"}
        missing = required - names
        if missing:
            return BundleVerificationReport(False, "", "", 0, [f"Missing required files: {sorted(missing)}"])

        manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
        case_id = manifest.get("case", {}).get("case_id", "")
        asset = manifest.get("asset", {})
        asset_id = asset.get("asset_id", "")
        evidence_rel = asset.get("bundle_path", "")

        if evidence_rel not in names:
            errors.append(f"Missing evidence payload in bundle: {evidence_rel}")
        else:
            raw = zf.read(evidence_rel)
            if hashlib.sha256(raw).hexdigest() != asset.get("sha256"):
                errors.append("Evidence SHA-256 mismatch")
            if blake3(raw).hexdigest() != asset.get("blake3"):
                errors.append("Evidence BLAKE3 mismatch")

        sums_raw = zf.read("sha256sums.txt").decode("utf-8").strip().splitlines()
        for line in sums_raw:
            expected_sum, arcname = line.split("  ", 1)
            if arcname not in names:
                errors.append(f"sha256sums.txt references missing entry: {arcname}")
            elif hashlib.sha256(zf.read(arcname)).hexdigest() != expected_sum:
                errors.append(f"Bundle file checksum mismatch: {arcname}")

        lines = [ln for ln in zf.read("custody_log.jsonl").decode("utf-8").splitlines() if ln.strip()]
        events = [json.loads(ln) for ln in lines]

        expected_prev = GENESIS_HASH
        for expected_seq, ev in enumerate(events):
            if ev.get("seq") != expected_seq:
                errors.append(f"Sequence gap: expected {expected_seq}, got {ev.get('seq')}")
            if ev.get("prev_hash") != expected_prev:
                errors.append(f"Chain break at seq={ev.get('seq')}: prev_hash mismatch")

            payload = {
                "event_id": ev["event_id"],
                "case_id": ev["case_id"],
                "asset_id": ev["asset_id"],
                "seq": ev["seq"],
                "event_type": ev["event_type"],
                "actor_from": ev["actor_from"],
                "actor_to": ev["actor_to"],
                "purpose": ev["purpose"],
                "location": ev["location"],
                "occurred_at_utc": ev["occurred_at_utc"],
                "notes": ev.get("notes", ""),
            }
            recomputed = _compute_event_hash(ev["prev_hash"], payload)
            if recomputed != ev.get("event_hash"):
                errors.append(f"Event payload tampered at seq={ev.get('seq')} ({ev.get('event_id')})")
            if not _verify_sig(ev.get("event_hash", ""), ev.get("signature", ""), ev.get("signer_public_key", "")):
                errors.append(f"Invalid Ed25519 signature at seq={ev.get('seq')} ({ev.get('event_id')})")
            expected_prev = ev.get("event_hash", "")

        if events and events[-1].get("event_hash") != manifest.get("head_event_hash"):
            errors.append("Manifest head_event_hash does not match custody_log.jsonl tail")

        return BundleVerificationReport(
            valid=len(errors) == 0,
            case_id=case_id,
            asset_id=asset_id,
            event_count=len(events),
            errors=errors,
        )
