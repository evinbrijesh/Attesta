"""Homingo sponsor integrations: n8n workflow webhooks and Olostep BSA Section 63 legal reference."""

from __future__ import annotations

import os
from typing import Any

import httpx

VERIFIED_BSA_S63_SUMMARY = {
    "statute": "Bharatiya Sakshya Adhiniyam, 2023 (BSA) — Section 63(4)",
    "effective_date": "2024-07-01",
    "landmark_ruling": "Pune Bar Association v. Union of India (Supreme Court of India, May 2026) — upheld S.63(4) & mandatory hash disclosure",
    "requirements": [
        "Part A: Declaration by custodian in lawful control of the device/record, disclosing origin and cryptographic hash value (e.g. SHA-256).",
        "Part B: Technical certification by a forensic/technical expert verifying extraction integrity and hash continuity.",
    ],
    "sources": [
        "https://lawsikho.com/blog/?p=7126",
        "https://www.livelaw.in/top-stories/supreme-court-rejects-challenge-to-s634-bsa-mandating-hash-value-disclosure-for-electronic-evidence-535950",
        "https://www.scconline.com/blog/post/2026/07/08/sc-upholds-admissibility-of-electronic-evidence-under-section-63-4-bsa/",
    ],
}


def notify_n8n(event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Fire a non-blocking webhook event to n8n Cloud if N8N_WEBHOOK_URL is configured."""
    webhook_url = os.getenv("N8N_WEBHOOK_URL", "").strip()
    if not webhook_url:
        return {"delivered": False, "reason": "N8N_WEBHOOK_URL not configured"}

    body = {"event_type": event_type, **payload}
    try:
        with httpx.Client(timeout=6.0) as client:
            resp = client.post(webhook_url, json=body)
            return {"delivered": resp.status_code < 300, "status_code": resp.status_code}
    except Exception as exc:
        return {"delivered": False, "reason": str(exc)}


def fetch_bsa_section63_reference(refresh_with_olostep: bool = False) -> dict[str, Any]:
    """Return BSA Section 63(4) legal guidance, optionally enriched live via Olostep API."""
    api_key = os.getenv("OLOSTEP_API_KEY", "").strip()
    if not refresh_with_olostep or not api_key:
        return {
            "provider": "verified-local-cache",
            **VERIFIED_BSA_S63_SUMMARY,
        }

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(
                "https://api.olostep.com/v1/scrapes",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "url_to_scrape": "https://www.scconline.com/blog/post/2026/07/08/sc-upholds-admissibility-of-electronic-evidence-under-section-63-4-bsa/",
                    "formats": ["markdown"],
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                markdown = data.get("result", {}).get("markdown_content", "")
                return {
                    "provider": "olostep-live",
                    "excerpt": markdown[:600] if markdown else "",
                    **VERIFIED_BSA_S63_SUMMARY,
                }
    except Exception:
        pass

    return {
        "provider": "verified-local-cache",
        **VERIFIED_BSA_S63_SUMMARY,
    }
