"""Deterministic metadata extraction and TRACE-style advisory media forensics."""

from __future__ import annotations

import io
from dataclasses import asdict, dataclass, field
from typing import Any

from PIL import ExifTags, Image, ImageChops, ImageStat

EDITING_SOFTWARE_MARKERS = ("photoshop", "gimp", "canva", "lightroom", "snapseed", "picsart")


@dataclass(frozen=True)
class AdvisoryFlag:
    """Non-blocking advisory forensic observation (never auto-rejects evidence)."""

    code: str
    severity: str
    message: str
    advisory_only: bool = True


@dataclass(frozen=True)
class ForensicsReport:
    """Metadata and advisory-only forensics report for an evidence asset."""

    is_image: bool
    detected_format: str
    width: int | None
    height: int | None
    exif: dict[str, Any]
    ela_mean_diff: float | None
    ela_max_diff: float | None
    advisory_only: bool = True
    flags: list[AdvisoryFlag] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize report to plain dictionary."""
        return asdict(self)


def _extract_exif(img: Image.Image) -> dict[str, Any]:
    """Extract human-readable EXIF tags from a PIL Image."""
    raw_exif = img.getexif()
    if not raw_exif:
        return {}
    result: dict[str, Any] = {}
    for tag_id, value in raw_exif.items():
        tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
        if isinstance(value, bytes):
            continue
        result[str(tag_name)] = str(value)
    return result


def _compute_ela(img: Image.Image, quality: int = 90) -> tuple[float, float]:
    """Compute Error Level Analysis (ELA) mean and max pixel difference."""
    rgb = img.convert("RGB")
    buf = io.BytesIO()
    rgb.save(buf, format="JPEG", quality=quality)
    buf.seek(0)
    recompressed = Image.open(buf).convert("RGB")
    diff = ImageChops.difference(rgb, recompressed)
    stat = ImageStat.Stat(diff)
    mean_diff = round(sum(stat.mean) / 3.0, 3)
    max_diff = float(max(hi for _, hi in stat.extrema))
    return mean_diff, max_diff


def analyze_bytes(data: bytes, declared_media_type: str = "") -> ForensicsReport:
    """Inspect raw evidence bytes for metadata and TRACE-style advisory flags."""
    flags: list[AdvisoryFlag] = []

    try:
        with Image.open(io.BytesIO(data)) as img:
            img.load()
            fmt = (img.format or "UNKNOWN").upper()
            width, height = img.size
            exif = _extract_exif(img)
            mean_diff, max_diff = _compute_ela(img)
    except Exception:
        detected = declared_media_type or "application/octet-stream"
        return ForensicsReport(
            is_image=False,
            detected_format=detected,
            width=None,
            height=None,
            exif={},
            ela_mean_diff=None,
            ela_max_diff=None,
            flags=[],
        )

    if not exif:
        flags.append(
            AdvisoryFlag(
                code="MISSING_EXIF",
                severity="warning",
                message="No EXIF metadata present; file may have been stripped or re-encoded (e.g., messaging app).",
            )
        )

    software = str(exif.get("Software", "")).lower()
    if any(marker in software for marker in EDITING_SOFTWARE_MARKERS):
        flags.append(
            AdvisoryFlag(
                code="EDITING_SOFTWARE_TAG",
                severity="warning",
                message=f"EXIF Software tag indicates post-processing tool: {exif.get('Software')}",
            )
        )

    if mean_diff is not None and mean_diff > 18.0:
        flags.append(
            AdvisoryFlag(
                code="HIGH_ELA_RESIDUAL",
                severity="info",
                message=f"Elevated ELA recompression residual (mean={mean_diff}); inspect manually.",
            )
        )

    return ForensicsReport(
        is_image=True,
        detected_format=fmt,
        width=width,
        height=height,
        exif=exif,
        ela_mean_diff=mean_diff,
        ela_max_diff=max_diff,
        flags=flags,
    )
