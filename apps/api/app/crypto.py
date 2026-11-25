"""Deterministic cryptographic primitives for Attesta (hashing, canonical JSON, Ed25519)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from blake3 import blake3
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

GENESIS_HASH = "0" * 64


@dataclass(frozen=True)
class FileDigest:
    """Dual cryptographic digest and byte size for an evidence file."""

    sha256: str
    blake3_hex: str
    size_bytes: int


def compute_digests(data: bytes) -> FileDigest:
    """Compute SHA-256 and BLAKE3 digests over raw bytes."""
    return FileDigest(
        sha256=hashlib.sha256(data).hexdigest(),
        blake3_hex=blake3(data).hexdigest(),
        size_bytes=len(data),
    )


def canonical_json(payload: dict[str, Any]) -> bytes:
    """Serialize a dictionary deterministically for hashing and signing."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def compute_event_hash(prev_hash: str, payload: dict[str, Any]) -> str:
    """Compute SHA-256 link hash binding previous event hash to canonical event payload."""
    h = hashlib.sha256()
    h.update(prev_hash.encode("ascii"))
    h.update(b":")
    h.update(canonical_json(payload))
    return h.hexdigest()


@dataclass(frozen=True)
class KeyPair:
    """Ed25519 signing keypair encoded as hex strings."""

    private_hex: str
    public_hex: str


def generate_keypair() -> KeyPair:
    """Generate a fresh Ed25519 keypair."""
    priv = Ed25519PrivateKey.generate()
    pub = priv.public_key()
    priv_bytes = priv.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_bytes = pub.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return KeyPair(private_hex=priv_bytes.hex(), public_hex=pub_bytes.hex())


def sign_event_hash(event_hash: str, private_hex: str) -> str:
    """Sign a hex event hash using an Ed25519 private key."""
    priv = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(private_hex))
    sig = priv.sign(event_hash.encode("ascii"))
    return sig.hex()


def verify_event_signature(event_hash: str, signature_hex: str, public_hex: str) -> bool:
    """Verify an Ed25519 signature over a hex event hash."""
    try:
        pub = Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_hex))
        pub.verify(bytes.fromhex(signature_hex), event_hash.encode("ascii"))
        return True
    except (InvalidSignature, ValueError):
        return False
