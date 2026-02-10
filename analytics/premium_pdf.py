from __future__ import annotations
from datetime import datetime
from pathlib import Path
from typing import List

import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib import colors

from analytics.kpis import SOVRow
from analytics.alerts import Alert
from analytics.benchmarks import BenchmarkRow
from analytics.recommendations import Recommendation

class Theme:
    primary = colors.HexColor("#1F3A8A")
    muted = colors.HexColor("#6B7280")
    light = colors.HexColor("#F3F4F6")
    black = colors.HexColor("#111827")

def _make_bar_chart(values, labels, title, out_path: Path):
    fig = plt.figure(figsize=(7.2, 3.2))
    ax = fig.add_subplot(111)
    ax.bar(range(len(values)), values)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=25, ha="right")
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)

def _kpi_tile(c: canvas.Canvas, x, y, w, h, label: str, value: str, theme: Theme):
    c.setFillColor(theme.light)
    c.roundRect(x, y, w, h, 8, stroke=0, fill=1)
    c.setFillColor(theme.muted)
    c.setFont("Helvetica", 9)
    c.drawString(x + 0.4*cm, y + h - 0.8*cm, label)
    c.setFillColor(theme.black)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(x + 0.4*cm, y + 0.55*cm, value)

def generate_premium_weekly_pdf(
    out_file: str,
    client_name: str,
    week_start: datetime,
    week_end: datetime,
    sov: List[SOVRow],
    top_posts,
    alerts: List[Alert],
    benchmarks: List[BenchmarkRow],
    recs: List[Recommendation],
    brand_name: str = "ImpactLens",
):
    theme = Theme()
    out_path = Path(out_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    c = canvas.Canvas(str(out_path), pagesize=A4)
    width, height = A4

    # Cover band
    c.setFillColor(theme.primary)
    c.rect(0, height - 3.2*cm, width, 3.2*cm, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(2*cm, height - 1.9*cm, "Weekly Sponsor Performance Report")
    c.setFont("Helvetica", 11)
    c.drawString(2*cm, height - 2.7*cm, f"{client_name} • {week_start.date()} → {week_end.date()}")
    c.setFont("Helvetica", 10)
    c.drawRightString(width - 2*cm, height - 2.7*cm, brand_name)

    total_views = sum(r.total_views for r in sov) if sov else 0
    total_eng = sum(r.total_engagements for r in sov) if sov else 0
    total_posts = sum(r.sponsored_posts for r in sov) if sov else 0

    y0 = height - 6.3*cm
    tile_w = (width - 4*cm - 1*cm) / 3
    _kpi_tile(c, 2*cm, y0, tile_w, 2.0*cm, "Sponsored Posts", f"{total_posts:,}", theme)
    _kpi_tile(c, 2*cm + tile_w + 0.5*cm, y0, tile_w, 2.0*cm, "Sponsored Views", f"{total_views:,}", theme)
    _kpi_tile(c, 2*cm + 2*(tile_w + 0.5*cm), y0, tile_w, 2.0*cm, "Engagements", f"{total_eng:,}", theme)

    c.setFillColor(theme.black)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(2*cm, y0 - 1.2*cm, "Executive Summary")
    c.setFont("Helvetica", 10)

    bullets = []
    if sov:
        bullets.append(f"Top sponsor by views: {sov[0].sponsor} ({sov[0].total_views:,} views).")
    if alerts:
        bullets.append(f"{len(alerts)} under-delivery alert(s) detected (vs 4-week baseline).")
    if benchmarks:
        low = min(benchmarks, key=lambda b: b.percentile)
        high = max(benchmarks, key=lambda b: b.percentile)
        bullets.append(f"Benchmarks: lowest cohort {low.percentile*100:.0f}%, highest cohort {high.percentile*100:.0f}%.")
    if recs:
        bullets.append("Next-week recommendations included (best cohorts + best posting windows + sponsor patterns).")

    if not bullets:
        bullets.append("Add sponsor dictionary and keep weekly exports to unlock alerts/benchmarks/recs.")

    yy = y0 - 1.9*cm
    for b in bullets[:6]:
        c.drawString(2.2*cm, yy, f"• {b}")
        yy -= 0.55*cm

    c.setFillColor(theme.muted)
    c.setFont("Helvetica", 8)
    c.drawString(2*cm, 1.2*cm, "MVP note: use client-owned exports or authorized APIs. Benchmarks/recs computed from your dataset.")
    c.showPage()

    # 1) SOV
    c.setFillColor(theme.black)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(2*cm, height - 2*cm, "1) Sponsor Share of Voice")
    y = height - 3.2*cm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(2*cm, y, "Sponsor")
    c.drawString(8*cm, y, "Sponsored Posts")
    c.drawString(12*cm, y, "Views")
    c.drawString(16*cm, y, "Engagements")
    y -= 0.55*cm
    c.setFont("Helvetica", 10)
    for r in sov[:14]:
        c.drawString(2*cm, y, r.sponsor)
        c.drawRightString(11*cm, y, f"{r.sponsored_posts:,}")
        c.drawRightString(15*cm, y, f"{r.total_views:,}")
        c.drawRightString(19*cm, y, f"{r.total_engagements:,}")
        y -= 0.5*cm

    if sov:
        chart = out_path.with_suffix(".sov.png")
        _make_bar_chart([r.total_views for r in sov[:8]], [r.sponsor for r in sov[:8]], "Top sponsors by Views", chart)
        c.drawImage(str(chart), 2*cm, 4.0*cm, width=17*cm, height=7*cm, preserveAspectRatio=True)
        chart.unlink(missing_ok=True)
    c.showPage()

    # 2) Alerts
    c.setFillColor(theme.black)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(2*cm, height - 2*cm, "2) Under-delivery Alerts")
    c.setFont("Helvetica", 10)
    c.setFillColor(theme.muted)
    c.drawString(2*cm, height - 2.7*cm, "Triggered when this week is ≥20% below 4-week baseline for views/engagements.")
    y = height - 3.6*cm
    c.setFillColor(theme.black)
    c.setFont("Helvetica", 10)
    if not alerts:
        c.drawString(2*cm, y, "No under-delivery alerts detected.")
    else:
        for a in alerts[:18]:
            c.drawString(2*cm, y, f"• {a.message}")
            y -= 0.55*cm
            if y < 2.5*cm:
                c.showPage()
                y = height - 2.5*cm
    c.showPage()

    # 3) Benchmarks
    c.setFillColor(theme.black)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(2*cm, height - 2*cm, "3) Benchmarks (Cohort Percentiles)")
    c.setFont("Helvetica", 10)
    c.setFillColor(theme.muted)
    c.drawString(2*cm, height - 2.7*cm, "Cohort = platform|format|language. Percentile is vs dataset distribution (8-week lookback).")
    y = height - 3.6*cm

    c.setFillColor(theme.black)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(2*cm, y, "Cohort")
    c.drawString(11*cm, y, "Metric")
    c.drawString(14*cm, y, "You")
    c.drawString(16*cm, y, "Median")
    c.drawString(18.2*cm, y, "Pctile")
    y -= 0.45*cm
    c.setFont("Helvetica", 9)

    if not benchmarks:
        c.setFillColor(theme.black)
        c.drawString(2*cm, y, "Not enough cohort data yet (need ~10+ posts per cohort).")
    else:
        for b in benchmarks[:18]:
            c.drawString(2*cm, y, b.cohort_key[:45])
            c.drawString(11*cm, y, b.metric)
            c.drawRightString(15.2*cm, y, f"{b.client_value:,}")
            c.drawRightString(17.2*cm, y, f"{b.cohort_median:,}")
            c.drawRightString(19.2*cm, y, f"{b.percentile*100:.0f}%")
            y -= 0.45*cm
            if y < 2.5*cm:
                c.showPage()
                y = height - 2.5*cm
    c.showPage()

    # 4) Top posts
    c.setFillColor(theme.black)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(2*cm, height - 2*cm, "4) Top Sponsored Creatives")
    y = height - 3.2*cm
    c.setFont("Helvetica", 10)
    for i, p in enumerate(top_posts[:15], start=1):
        eng = int((p.likes or 0) + (p.comments or 0) + (p.shares or 0))
        c.drawString(2*cm, y, f"{i}. {p.platform.upper()} • {p.media_type} • {int(p.views or 0):,} views • {eng:,} eng")
        y -= 0.45*cm
        c.setFillColor(theme.muted)
        c.setFont("Helvetica", 9)
        c.drawString(2.2*cm, y, f"{p.url}"[:110])
        c.setFillColor(theme.black)
        c.setFont("Helvetica", 10)
        y -= 0.55*cm
        if y < 2.5*cm:
            c.showPage()
            y = height - 2.5*cm
    c.showPage()

    # 5) Recommendations
    c.setFillColor(theme.black)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(2*cm, height - 2*cm, "5) Next Week Recommendations")
    c.setFont("Helvetica", 10)
    c.setFillColor(theme.muted)
    c.drawString(2*cm, height - 2.7*cm, "Based on last 8 weeks: best cohorts + best windows + sponsor patterns.")
    y = height - 3.6*cm
    c.setFillColor(theme.black)

    if not recs:
        c.drawString(2*cm, y, "Not enough data to generate recommendations yet.")
    else:
        for r in recs[:10]:
            c.setFont("Helvetica-Bold", 10)
            c.drawString(2*cm, y, r.title)
            y -= 0.45*cm
            c.setFont("Helvetica", 10)
            c.drawString(2.2*cm, y, f"• {r.detail}"[:130])
            y -= 0.65*cm
            if y < 2.5*cm:
                c.showPage()
                y = height - 2.5*cm

    c.save()
