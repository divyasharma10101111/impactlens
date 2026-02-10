from __future__ import annotations
from datetime import datetime
from pathlib import Path
from typing import List

import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm

from analytics.kpis import SOVRow

def _make_bar_chart(values, labels, title, out_path: Path):
    fig = plt.figure(figsize=(7, 3))
    ax = fig.add_subplot(111)
    ax.bar(range(len(values)), values)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=25, ha="right")
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(out_path, dpi=160)
    plt.close(fig)

def generate_weekly_pdf(
    out_file: str,
    client_name: str,
    week_start: datetime,
    week_end: datetime,
    sov: List[SOVRow],
    top_posts,
):
    out_path = Path(out_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    c = canvas.Canvas(str(out_path), pagesize=A4)
    width, height = A4

    # Header
    c.setFont("Helvetica-Bold", 16)
    c.drawString(2*cm, height - 2*cm, f"{client_name} — Weekly Sponsor Report")
    c.setFont("Helvetica", 10)
    c.drawString(2*cm, height - 2.7*cm, f"Week: {week_start.date()} to {week_end.date()}")

    # SOV table
    y = height - 4*cm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(2*cm, y, "1) Sponsor Share of Voice (Social)")
    y -= 0.7*cm

    c.setFont("Helvetica-Bold", 10)
    c.drawString(2*cm, y, "Sponsor")
    c.drawString(8*cm, y, "Sponsored Posts")
    c.drawString(12*cm, y, "Views")
    c.drawString(16*cm, y, "Engagements")
    y -= 0.4*cm
    c.setFont("Helvetica", 10)

    for r in sov[:12]:
        c.drawString(2*cm, y, r.sponsor)
        c.drawRightString(11*cm, y, str(r.sponsored_posts))
        c.drawRightString(15*cm, y, str(r.total_views))
        c.drawRightString(19*cm, y, str(r.total_engagements))
        y -= 0.45*cm
        if y < 4*cm:
            c.showPage()
            y = height - 3*cm

    # Charts
    if sov:
        chart1 = out_path.with_suffix(".views.png")
        chart2 = out_path.with_suffix(".eng.png")
        _make_bar_chart([r.total_views for r in sov[:8]], [r.sponsor for r in sov[:8]], "Top sponsors by Views", chart1)
        _make_bar_chart([r.total_engagements for r in sov[:8]], [r.sponsor for r in sov[:8]], "Top sponsors by Engagements", chart2)

        c.showPage()
        c.setFont("Helvetica-Bold", 12)
        c.drawString(2*cm, height - 2*cm, "2) Highlights")
        c.drawImage(str(chart1), 2*cm, height - 10*cm, width=17*cm, height=7*cm, preserveAspectRatio=True)
        c.drawImage(str(chart2), 2*cm, height - 18*cm, width=17*cm, height=7*cm, preserveAspectRatio=True)

        # Clean up chart files after embedding
        chart1.unlink(missing_ok=True)
        chart2.unlink(missing_ok=True)

    # Top posts
    c.showPage()
    c.setFont("Helvetica-Bold", 12)
    c.drawString(2*cm, height - 2*cm, "3) Top Sponsored Posts (by Views)")
    y = height - 3.2*cm
    c.setFont("Helvetica", 10)
    for i, p in enumerate(top_posts, start=1):
        line = f"{i}. {p.platform.upper()} • {p.media_type} • {p.views} views • {p.url}"
        c.drawString(2*cm, y, line[:120])
        y -= 0.55*cm
        if y < 2.5*cm:
            c.showPage()
            y = height - 2.5*cm

    c.save()
