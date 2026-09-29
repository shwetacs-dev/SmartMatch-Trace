"""
export_db_to_pdf.py
--------------------
Reads lost_and_found.db and produces a human-readable PDF showing
everything stored inside it: all items, all claims, and summary stats.

Run with:
    python export_db_to_pdf.py
"""

import sqlite3
import pandas as pd
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                 TableStyle, PageBreak)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

DB_PATH = "lost_and_found.db"
OUTPUT_PATH = "Lost_and_Found_Database_Contents.pdf"


def fetch_data():
    conn = sqlite3.connect(DB_PATH)
    items_df = pd.read_sql_query("SELECT * FROM items ORDER BY item_id", conn)
    claims_df = pd.read_sql_query("""
        SELECT claims.claim_id, items.item_name, items.category,
               claims.claimant_name, claims.claim_date, claims.verified,
               claims.verification_notes
        FROM claims JOIN items ON claims.item_id = items.item_id
        ORDER BY claims.claim_id
    """, conn)
    conn.close()
    return items_df, claims_df


def df_to_table(df, col_widths=None):
    """Convert a pandas DataFrame into a reportlab Table with header styling."""
    # fillna BEFORE astype(str) -- otherwise empty/None cells (e.g. a lost
    # item's storage_location, which is always empty) print as the literal
    # text "nan" instead of staying blank.
    data = [list(df.columns)] + df.fillna("").astype(str).values.tolist()
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4C72B0")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F0F0F0")]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return table


def build_pdf():
    items_df, claims_df = fetch_data()

    doc = SimpleDocTemplate(
        OUTPUT_PATH, pagesize=landscape(A4),
        leftMargin=1.2 * cm, rightMargin=1.2 * cm,
        topMargin=1.2 * cm, bottomMargin=1.2 * cm
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TitleStyle", parent=styles["Title"], fontSize=18)
    heading_style = ParagraphStyle("HeadingStyle", parent=styles["Heading2"], spaceBefore=10)
    normal_style = styles["Normal"]

    story = []

    # ---- Cover / summary page ----
    story.append(Paragraph("Lost &amp; Found Management System", title_style))
    story.append(Paragraph("Database Contents Report", styles["Heading2"]))
    story.append(Spacer(1, 14))

    total_items = len(items_df)
    lost_count = int((items_df["type"] == "lost").sum())
    found_count = int((items_df["type"] == "found").sum())
    claimed_count = int((items_df["status"] == "Claimed").sum())
    unclaimed_count = int((items_df["status"] == "Unclaimed").sum())
    total_claims = len(claims_df)
    verified_claims = int((claims_df["verified"] == "Verified").sum()) if not claims_df.empty else 0

    summary_data = [
        ["Metric", "Value"],
        ["Total items in database", str(total_items)],
        ["Lost reports", str(lost_count)],
        ["Found reports", str(found_count)],
        ["Claimed items", str(claimed_count)],
        ["Unclaimed items", str(unclaimed_count)],
        ["Total claims filed", str(total_claims)],
        ["Verified claims", str(verified_claims)],
    ]
    summary_table = Table(summary_data, colWidths=[8 * cm, 5 * cm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4C72B0")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F0F0F0")]),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(summary_table)
    story.append(PageBreak())

    # ---- Items table ----
    story.append(Paragraph("Items Table (all lost &amp; found reports)", heading_style))
    story.append(Spacer(1, 8))

    display_cols = ["item_id", "item_name", "type", "category", "status",
                     "date_lost_found", "location", "storage_location", "reporter_name"]
    items_display = items_df[display_cols].copy()
    col_widths = [1.3, 3.2, 1.5, 2.8, 2.4, 2.4, 3.0, 3.2, 3.0]
    col_widths = [w * cm for w in col_widths]

    story.append(df_to_table(items_display, col_widths=col_widths))
    story.append(PageBreak())

    # ---- Claims table ----
    story.append(Paragraph("Claims Table", heading_style))
    story.append(Spacer(1, 8))

    if claims_df.empty:
        story.append(Paragraph("No claims have been filed yet.", normal_style))
    else:
        claim_col_widths = [1.5, 4.0, 3.0, 3.5, 2.5, 2.5, 6.0]
        claim_col_widths = [w * cm for w in claim_col_widths]
        story.append(df_to_table(claims_df, col_widths=claim_col_widths))

    doc.build(story)
    print(f"PDF created: {OUTPUT_PATH}")
    print(f"Items: {total_items} | Claims: {total_claims}")


if __name__ == "__main__":
    build_pdf()
