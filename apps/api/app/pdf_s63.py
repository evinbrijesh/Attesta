"""Pure-Python BSA Section 63(4) Part A & Part B Certificate PDF generator."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


@dataclass(frozen=True)
class Section63CertificateData:
    """Data required to render a BSA Section 63(4) Part A & Part B PDF."""

    cert_id: str
    case_id: str
    case_title: str
    asset_id: str
    filename: str
    media_type: str
    size_bytes: int
    sha256: str
    blake3: str
    head_event_hash: str
    event_count: int
    custodian_name: str
    custodian_designation: str
    expert_name: str
    expert_designation: str
    part_a_text: str
    part_b_text: str
    signed_at_utc: str


def render_section63_pdf(data: Section63CertificateData, output_path: Path) -> Path:
    """Render a structured BSA Section 63(4) Part A + Part B PDF to output_path."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "AttestaTitle",
        parent=styles["Heading1"],
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "AttestaSubtitle",
        parent=styles["Normal"],
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#475569"),
        spaceAfter=10,
    )
    section_style = ParagraphStyle(
        "AttestaSection",
        parent=styles["Heading2"],
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#065f46"),
        spaceBefore=10,
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "AttestaBody",
        parent=styles["Normal"],
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor("#1e293b"),
    )
    mono_style = ParagraphStyle(
        "AttestaMono",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#0f172a"),
    )
    disclaimer_style = ParagraphStyle(
        "AttestaDisclaimer",
        parent=styles["Normal"],
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#64748b"),
    )

    story = [
        Paragraph("CERTIFICATE UNDER SECTION 63(4) OF THE BHARATIYA SAKSHYA ADHINIYAM, 2023", title_style),
        Paragraph(
            f"Certificate ID: <b>{data.cert_id}</b> &nbsp;|&nbsp; Case: <b>{data.case_title}</b> ({data.case_id}) "
            f"&nbsp;|&nbsp; Signed UTC: <b>{data.signed_at_utc}</b>",
            subtitle_style,
        ),
    ]

    meta_table = Table(
        [
            ["Evidence Asset ID", Paragraph(data.asset_id, mono_style)],
            ["Original Filename", Paragraph(f"{data.filename} ({data.size_bytes} bytes, {data.media_type})", body_style)],
            ["SHA-256 Digest (Mandatory)", Paragraph(data.sha256, mono_style)],
            ["BLAKE3 Digest", Paragraph(data.blake3, mono_style)],
            ["Custody Chain Head Hash", Paragraph(data.head_event_hash, mono_style)],
            ["Verified Custody Events", Paragraph(f"{data.event_count} Ed25519-signed event(s)", body_style)],
        ],
        colWidths=[48 * mm, 126 * mm],
    )
    meta_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f1f5f9")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTSIZE", (0, 0), (0, -1), 8.5),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(meta_table)
    story.append(Spacer(1, 8))

    story.append(Paragraph("PART A — DECLARATION BY CUSTODIAN / PERSON IN LAWFUL CONTROL", section_style))
    story.append(Paragraph(data.part_a_text, body_style))
    story.append(Spacer(1, 6))
    story.append(
        Paragraph(
            f"<b>Custodian:</b> {data.custodian_name} ({data.custodian_designation})",
            body_style,
        )
    )
    story.append(Spacer(1, 8))

    story.append(Paragraph("PART B — CERTIFICATION BY TECHNICAL / FORENSIC EXPERT", section_style))
    story.append(Paragraph(data.part_b_text, body_style))
    story.append(Spacer(1, 6))
    story.append(
        Paragraph(
            f"<b>Certifying Expert:</b> {data.expert_name} ({data.expert_designation}) &nbsp;|&nbsp; "
            f"<b>Human Sign-Off Timestamp:</b> {data.signed_at_utc}",
            body_style,
        )
    )
    story.append(Spacer(1, 14))
    story.append(
        Paragraph(
            "Prepared by Attesta (Attested. Verified. Sealed.) for human expert review and sign-off under BSA Section 63(4). "
            "Integrity of this bundle can be verified offline without server trust using `attesta-verify`. "
            "Judicial admissibility remains subject to court determination.",
            disclaimer_style,
        )
    )

    doc.build(story)
    return output_path
