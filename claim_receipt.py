"""
claim_receipt.py
-----------------
Generates a print-friendly single-page PDF claim receipt that a student
can show at the admin desk to collect their item.

Usage (called from app.py):
    from claim_receipt import generate_claim_receipt_pdf
    pdf_bytes = generate_claim_receipt_pdf(claim, item)
    st.download_button("Download Receipt", data=pdf_bytes, file_name="claim_receipt.pdf", mime="application/pdf")
"""

import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)


# Colour palette — matches the app's purple/pink gradient feel
PURPLE      = colors.HexColor("#6a11cb")
LIGHT_PURPLE= colors.HexColor("#ede7f6")
PINK        = colors.HexColor("#ff6a88")
GREY_DARK   = colors.HexColor("#424242")
GREY_LIGHT  = colors.HexColor("#f5f5f5")
WHITE       = colors.white


def _build_styles():
    base = getSampleStyleSheet()

    title = ParagraphStyle(
        "ReceiptTitle",
        parent=base["Title"],
        fontSize=22,
        textColor=PURPLE,
        spaceAfter=4,
    )
    subtitle = ParagraphStyle(
        "ReceiptSubtitle",
        parent=base["Normal"],
        fontSize=10,
        textColor=GREY_DARK,
        spaceAfter=2,
    )
    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=base["Heading3"],
        fontSize=11,
        textColor=PURPLE,
        spaceBefore=12,
        spaceAfter=4,
        fontName="Helvetica-Bold",
    )
    field_label = ParagraphStyle(
        "FieldLabel",
        parent=base["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#757575"),
        spaceAfter=1,
    )
    field_value = ParagraphStyle(
        "FieldValue",
        parent=base["Normal"],
        fontSize=10,
        textColor=GREY_DARK,
        fontName="Helvetica-Bold",
        spaceAfter=6,
    )
    footer = ParagraphStyle(
        "Footer",
        parent=base["Normal"],
        fontSize=8,
        textColor=colors.grey,
        alignment=1,  # centred
    )
    watermark = ParagraphStyle(
        "Watermark",
        parent=base["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#43a047"),
        fontName="Helvetica-Bold",
        alignment=1,
    )
    return {
        "title": title,
        "subtitle": subtitle,
        "section_heading": section_heading,
        "field_label": field_label,
        "field_value": field_value,
        "footer": footer,
        "watermark": watermark,
    }


def _row(label, value, styles):
    """Return a two-element list [label para, value para] for a detail row."""
    return [
        Paragraph(label, styles["field_label"]),
        Paragraph(str(value) if value else "—", styles["field_value"]),
    ]


def generate_claim_receipt_pdf(claim: dict, item: dict) -> bytes:
    """
    Build and return a PDF receipt as raw bytes.

    Parameters
    ----------
    claim : dict-like  (sqlite3.Row or plain dict)
        claim_id, claimant_name, claim_date, verified, verification_notes, user_id
    item : dict-like  (sqlite3.Row or plain dict)
        item_id, item_name, category, type, description, location,
        storage_location, date_lost_found, reporter_name

    Returns
    -------
    bytes  — ready to pass to st.download_button
    """
    # Normalise to plain dicts so both sqlite3.Row and dicts work
    if hasattr(claim, "keys"):
        claim = dict(claim)
    if hasattr(item, "keys"):
        item = dict(item)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
    )

    styles = _build_styles()
    story = []

    # ── Header banner ────────────────────────────────────────────────────────
    banner_data = [[
        Paragraph("🔎 Lost &amp; Found Management System", styles["title"]),
    ]]
    banner_table = Table(banner_data, colWidths=[doc.width])
    banner_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_PURPLE),
        ("TOPPADDING",    (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING",   (0, 0), (-1, -1), 12),
        ("ROUNDEDCORNERS", [8]),
    ]))
    story.append(banner_table)
    story.append(Spacer(1, 6))
    story.append(Paragraph("Claim Collection Receipt", styles["subtitle"]))
    story.append(Paragraph(
        f"Generated on {datetime.now().strftime('%d %B %Y, %I:%M %p')}",
        styles["subtitle"]
    ))
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1.5, color=PURPLE, spaceAfter=10))

    # ── Claim status badge ────────────────────────────────────────────────────
    verified = claim.get("verified", "Pending")
    badge_colour = {
        "Verified": colors.HexColor("#43a047"),
        "Pending":  colors.HexColor("#f9a825"),
        "Rejected": colors.HexColor("#e53935"),
    }.get(verified, colors.grey)

    status_data = [[
        Paragraph(f"Claim Status:  {verified}", ParagraphStyle(
            "BadgeText", fontSize=13, fontName="Helvetica-Bold",
            textColor=WHITE,
        )),
    ]]
    status_table = Table(status_data, colWidths=[doc.width])
    status_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), badge_colour),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING",   (0, 0), (-1, -1), 16),
        ("ROUNDEDCORNERS", [6]),
    ]))
    story.append(status_table)
    story.append(Spacer(1, 14))

    # ── Claim details ─────────────────────────────────────────────────────────
    story.append(Paragraph("Claim Details", styles["section_heading"]))

    col_w = [doc.width * 0.35, doc.width * 0.65]
    claim_rows = [
        _row("Claim Reference ID",  f"#{claim.get('claim_id', '—')}", styles),
        _row("Claimant Name",       claim.get("claimant_name", "—"), styles),
        _row("Date Filed",          claim.get("claim_date", "—"), styles),
        _row("Verification Status", verified, styles),
    ]
    if claim.get("verification_notes"):
        claim_rows.append(_row("Admin Notes", claim["verification_notes"], styles))

    claim_table = Table(claim_rows, colWidths=col_w)
    claim_table.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, GREY_LIGHT]),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("GRID",          (0, 0), (-1, -1), 0.3, colors.HexColor("#e0e0e0")),
    ]))
    story.append(KeepTogether(claim_table))
    story.append(Spacer(1, 14))

    # ── Item details ──────────────────────────────────────────────────────────
    story.append(Paragraph("Item Details", styles["section_heading"]))

    item_rows = [
        _row("Item ID",          f"#{item.get('item_id', '—')}", styles),
        _row("Item Name",        item.get("item_name", "—"), styles),
        _row("Category",         item.get("category", "—"), styles),
        _row("Type",             (item.get("type") or "—").title(), styles),
        _row("Description",      item.get("description", "—"), styles),
        _row("Date Lost/Found",  item.get("date_lost_found", "—"), styles),
        _row("Location",         item.get("location", "—"), styles),
        _row("Storage Location", item.get("storage_location") or "Contact admin office", styles),
    ]

    item_table = Table(item_rows, colWidths=col_w)
    item_table.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, GREY_LIGHT]),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("GRID",          (0, 0), (-1, -1), 0.3, colors.HexColor("#e0e0e0")),
    ]))
    story.append(KeepTogether(item_table))
    story.append(Spacer(1, 18))

    # ── Instructions box ──────────────────────────────────────────────────────
    if verified == "Verified":
        instructions = (
            "✅  Your claim has been <b>approved</b>. Please bring this receipt "
            "and a valid student ID to the <b>Admin Office</b> to collect your item. "
            "The item will only be released to the named claimant above."
        )
        box_colour = colors.HexColor("#e8f5e9")
        border_colour = colors.HexColor("#43a047")
    elif verified == "Pending":
        instructions = (
            "🕐  Your claim is <b>pending verification</b>. An admin will review your "
            "ownership details and update the status. You will be notified once a "
            "decision is made. You may present this receipt at the Admin Office to "
            "check the progress of your claim."
        )
        box_colour = colors.HexColor("#fff8e1")
        border_colour = colors.HexColor("#f9a825")
    else:
        instructions = (
            "❌  Your claim was <b>not approved</b>. Please visit the Admin Office "
            "with additional proof of ownership or contact staff for further assistance."
        )
        box_colour = colors.HexColor("#ffebee")
        border_colour = colors.HexColor("#e53935")

    instr_style = ParagraphStyle(
        "InstrBox", fontSize=10, textColor=GREY_DARK,
        leading=15, leftIndent=8, rightIndent=8,
    )
    instr_data = [[Paragraph(instructions, instr_style)]]
    instr_table = Table(instr_data, colWidths=[doc.width])
    instr_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), box_colour),
        ("LINEAFTER",     (0, 0), (0, -1),  3, border_colour),
        ("TOPPADDING",    (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("LEFTPADDING",   (0, 0), (-1, -1), 12),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 12),
    ]))
    story.append(instr_table)
    story.append(Spacer(1, 20))

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.8, color=colors.grey, spaceAfter=8))
    story.append(Paragraph(
        "College Lost &amp; Found Management System  ·  "
        "This is a system-generated receipt. No signature required.",
        styles["footer"]
    ))

    doc.build(story)
    buf.seek(0)
    return buf.read()
