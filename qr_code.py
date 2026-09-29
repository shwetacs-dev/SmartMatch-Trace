"""
qr_code.py
-----------
Generates QR codes and printable A5 storage-tag PDFs for found items.

The QR code URL is built from the actual page URL so it works on any
network (localhost, LAN, deployed server) — not hardcoded.

Public API
----------
get_base_url()                         -> str  (call from Streamlit context)
generate_qr_png(item_id, base_url)     -> bytes  (PNG)
generate_storage_tag_pdf(item, base_url) -> bytes  (A5 PDF)
"""

import io
import qrcode

from reportlab.lib.pagesizes import A5
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    Table, TableStyle, HRFlowable, Image as RLImage,
)

# ── Colours (match app theme) ─────────────────────────────────────────────
PURPLE       = colors.HexColor("#6a11cb")
LIGHT_PURPLE = colors.HexColor("#ede7f6")
PINK         = colors.HexColor("#ff6a88")
GREY_DARK    = colors.HexColor("#424242")
GREY_LIGHT   = colors.HexColor("#f5f5f5")
WHITE        = colors.white


# ---------------------------------------------------------------------------
# URL HELPERS
# ---------------------------------------------------------------------------

def get_base_url() -> str:
    """
    Return the base URL of the running Streamlit app.

    Uses st.context.url (available since Streamlit 1.37) so the QR code
    always encodes the real address — works on localhost, LAN IPs, and
    deployed servers alike.

    Falls back to http://localhost:8501 if called outside a Streamlit run.
    """
    try:
        import streamlit as st
        full_url: str = st.context.url          # e.g. "http://192.168.1.5:8501/?foo=bar"
        # Strip any existing query string / fragment so we get just the base
        from urllib.parse import urlparse, urlunparse
        parsed = urlparse(full_url)
        base = urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))
        return base.rstrip("/")
    except Exception:
        return "http://localhost:8501"


def _item_url(item_id: int, base_url: str) -> str:
    """Deep-link URL for a given item."""
    return f"{base_url.rstrip('/')}/?item_id={item_id}"


# ---------------------------------------------------------------------------
# QR PNG
# ---------------------------------------------------------------------------

def generate_qr_png(item_id: int, base_url: str) -> bytes:
    """
    Return a PNG QR code (bytes) that encodes the item's deep-link URL.
    Requires qrcode[pil] (Pillow backend).
    """
    url = _item_url(item_id, base_url)
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=3,
    )
    qr.add_data(url)
    qr.make(fit=True)
    pil_img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()


# ---------------------------------------------------------------------------
# STORAGE TAG PDF  (A5, single-column, clean layout)
# ---------------------------------------------------------------------------

def generate_storage_tag_pdf(item, base_url: str) -> bytes:
    """
    Return a printable A5 PDF storage tag (bytes).

    Layout (top → bottom):
      ┌─────────────────────────────┐
      │   Header banner (purple)    │
      │   QR code  (centred)        │
      │   "Scan to view details"    │
      │   ─────────────────────     │
      │   Item fields table         │
      │   ─────────────────────     │
      │   Footer instruction        │
      └─────────────────────────────┘
    """
    if hasattr(item, "keys"):
        item = dict(item)

    item_id  = item.get("item_id", "?")
    base_url = base_url.rstrip("/")

    # ── Build QR PNG → ReportLab Image ───────────────────────────────────
    qr_png = generate_qr_png(item_id, base_url)
    qr_img = RLImage(io.BytesIO(qr_png), width=5.5 * cm, height=5.5 * cm)

    # ── Document ──────────────────────────────────────────────────────────
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A5,
        leftMargin=1.4 * cm,
        rightMargin=1.4 * cm,
        topMargin=1.2 * cm,
        bottomMargin=1.2 * cm,
    )
    W = A5[0] - 2.8 * cm      # usable width

    # ── Styles ────────────────────────────────────────────────────────────
    def ps(name, **kw):
        base = ParagraphStyle(name, **kw)
        return base

    title_s = ps("T", fontName="Helvetica-Bold", fontSize=12,
                 textColor=WHITE, alignment=1, leading=16)
    sub_s   = ps("S", fontName="Helvetica", fontSize=8,
                 textColor=WHITE, alignment=1, leading=11)
    scan_s  = ps("SC", fontName="Helvetica-Oblique", fontSize=8,
                 textColor=colors.HexColor("#757575"), alignment=1, spaceAfter=4)
    lbl_s   = ps("L", fontName="Helvetica", fontSize=8,
                 textColor=colors.HexColor("#757575"), spaceAfter=1)
    val_s   = ps("V", fontName="Helvetica-Bold", fontSize=10,
                 textColor=GREY_DARK, spaceAfter=2, leading=13)
    foot_s  = ps("F", fontName="Helvetica-Oblique", fontSize=7,
                 textColor=colors.grey, alignment=1, leading=10)

    story = []

    # 1 ── Header banner ───────────────────────────────────────────────────
    hdr = Table(
        [[Paragraph("🔎  Lost &amp; Found Management System", title_s)],
         [Paragraph("Storage Tag", sub_s)]],
        colWidths=[W],
    )
    hdr.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), PURPLE),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
    ]))
    story.append(hdr)
    story.append(Spacer(1, 10))

    # 2 ── QR code centred ─────────────────────────────────────────────────
    qr_tbl = Table([[qr_img]], colWidths=[W])
    qr_tbl.setStyle(TableStyle([
        ("ALIGN",  (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(qr_tbl)
    story.append(Spacer(1, 4))
    story.append(Paragraph("Scan QR code to view full item details", scan_s))
    story.append(Spacer(1, 8))

    # 3 ── Item fields ─────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.8, color=PURPLE, spaceAfter=8))

    def field_row(label, value):
        return [
            [Paragraph(label, lbl_s)],
            [Paragraph(str(value) if value else "—", val_s)],
        ]

    fields = [
        ("Item ID",          f"#{item_id}"),
        ("Item Name",        item.get("item_name", "—")),
        ("Category",         item.get("category", "—")),
        ("Type",             (item.get("type") or "found").title()),
        ("Storage Location", item.get("storage_location") or "Admin Office"),
        ("Status",           item.get("status", "—")),
    ]

    # Build as a two-column grid: Label | Value
    rows = []
    for label, value in fields:
        rows.append([Paragraph(label, lbl_s), Paragraph(str(value) if value else "—", val_s)])

    field_tbl = Table(rows, colWidths=[W * 0.38, W * 0.62])
    field_tbl.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, GREY_LIGHT]),
        ("TOPPADDING",     (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 5),
        ("LEFTPADDING",    (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",   (0, 0), (-1, -1), 6),
        ("GRID",           (0, 0), (-1, -1), 0.3, colors.HexColor("#e0e0e0")),
        ("VALIGN",         (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(field_tbl)
    story.append(Spacer(1, 10))

    # 4 ── Footer ──────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey, spaceAfter=6))
    story.append(Paragraph(
        "Attach this tag to the item or its storage bag.  "
        "Staff: scan QR or enter the Item ID in the system to view details.",
        foot_s,
    ))

    doc.build(story)
    buf.seek(0)
    return buf.read()
