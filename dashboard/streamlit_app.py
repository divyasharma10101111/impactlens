import sys
from pathlib import Path

# --- Ensure project root is on sys.path (Fix Option 2) ---
ROOT = Path(__file__).resolve().parents[1]  # project root folder
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
import pandas as pd
from datetime import datetime
from sqlmodel import select

from app.db import get_session
from app.models import Client, Post
from processing.run_tagging import tag_unprocessed_posts_text
from analytics.kpis import week_range, compute_sov, top_posts
from analytics.alerts import compute_under_delivery_alerts
from analytics.benchmarks import compute_content_benchmarks
from analytics.recommendations import compute_next_week_recommendations
from reporting.premium_pdf import generate_premium_weekly_pdf
from reporting.pptx_deck import build_client_deck_pptx


st.set_page_config(page_title="ImpactLens — Sponsor Intelligence", layout="wide")

# -----------------------
# Sidebar: Logo + Controls
# -----------------------
ASSETS_DIR = ROOT / "assets"
logo_candidates = [
    ASSETS_DIR / "impactlens_logo.png",
    ASSETS_DIR / "impactlens_logo.jpg",
    ASSETS_DIR / "logo.png",
    ASSETS_DIR / "logo.jpg",
]
logo_file = next((p for p in logo_candidates if p.exists()), None)

if logo_file:
    st.sidebar.image(str(logo_file), width=180)
else:
    st.sidebar.caption("Logo not found. Put it in /assets as impactlens_logo.png or logo.png")

debug = st.sidebar.checkbox("Debug", value=False)
if debug:
    st.sidebar.write("Project ROOT:", str(ROOT))
    st.sidebar.write("Assets dir:", str(ASSETS_DIR))
    st.sidebar.write("Found logo:", str(logo_file) if logo_file else "None")

st.title("ImpactLens — Weekly Sponsor Intelligence (POC)")

# -----------------------
# Load clients
# -----------------------
with get_session() as session:
    clients = session.exec(select(Client).order_by(Client.name)).all()
client_names = [c.name for c in clients]

client = st.sidebar.selectbox("Client", client_names) if client_names else None
week_ending = st.sidebar.date_input("Week ending", value=datetime(2026, 2, 8).date())

if not client:
    st.info(
        "No clients loaded.\n\n"
        "Run these from the project root:\n"
        "1) python scripts/init_db.py\n"
        "2) python scripts/import_posts_csv.py data/demo_posts_synthetic.csv"
    )
    st.stop()

week_end_dt = datetime.combine(week_ending, datetime.max.time())
week_start_dt, week_end_dt2 = week_range(week_end_dt)

st.sidebar.markdown("---")
if st.sidebar.button("Run sponsor tagging (text)"):
    created = tag_unprocessed_posts_text(client_name=client, limit=8000)
    st.sidebar.success(f"Tagging complete. New tags: {created}")

# -----------------------
# Load posts for selected client
# -----------------------
with get_session() as session:
    c = session.exec(select(Client).where(Client.name == client)).first()
    posts = session.exec(
        select(Post).where(Post.client_id == c.id).order_by(Post.posted_at.desc())
    ).all()

df = pd.DataFrame(
    [
        {
            "posted_at": p.posted_at,
            "platform": p.platform,
            "media_type": p.media_type,
            "language": p.language,
            "views": int(p.views or 0),
            "engagements": int((p.likes or 0) + (p.comments or 0) + (p.shares or 0)),
            "url": p.url,
            "caption": (p.caption or "")[:150],
        }
        for p in posts
    ]
)

# -----------------------
# Top KPIs
# -----------------------
col1, col2, col3 = st.columns(3)
col1.metric("Posts", len(df))
col2.metric("Total views", int(df["views"].sum()) if len(df) else 0)
col3.metric("Selected week", f"{week_start_dt.date()} → {week_end_dt2.date()}")

st.subheader("Posts (all time)")
st.dataframe(df, use_container_width=True, height=300)

# -----------------------
# Weekly analytics outputs
# -----------------------
sov = compute_sov(client, week_start_dt, week_end_dt2)
tops = top_posts(client, week_start_dt, week_end_dt2, limit=15)
alerts = compute_under_delivery_alerts(client, week_end_dt, lookback_weeks=4, threshold_pct=0.20)
benchmarks = compute_content_benchmarks(client, week_end_dt, lookback_weeks=8)
recs = compute_next_week_recommendations(client, week_end_dt, lookback_weeks=8)

# -----------------------
# Under-delivery alerts
# -----------------------
st.subheader("Under-delivery alerts")
if not alerts:
    st.success("No under-delivery alerts detected.")
else:
    for a in alerts[:10]:
        st.warning(a.message)

# -----------------------
# Benchmarks
# -----------------------
st.subheader("Benchmarks (cohort percentiles)")
if not benchmarks:
    st.info("Not enough cohort data yet. Add more posts/clients over time.")
else:
    bdf = pd.DataFrame(
        [
            {
                "cohort": b.cohort_key,
                "metric": b.metric,
                "you": b.client_value,
                "median": b.cohort_median,
                "percentile": round(b.percentile * 100, 0),
            }
            for b in benchmarks[:20]
        ]
    )
    st.dataframe(bdf, use_container_width=True, height=240)

# -----------------------
# Sponsor SOV
# -----------------------
st.subheader("Sponsor Share of Voice")
sov_df = pd.DataFrame(
    [
        {
            "sponsor": r.sponsor,
            "sponsored_posts": r.sponsored_posts,
            "views": r.total_views,
            "engagements": r.total_engagements,
        }
        for r in sov
    ]
)
st.dataframe(sov_df, use_container_width=True, height=240)

# -----------------------
# Top sponsored creatives
# -----------------------
st.subheader("Top sponsored creatives")
tp_df = pd.DataFrame(
    [
        {
            "posted_at": p.posted_at,
            "platform": p.platform,
            "media_type": p.media_type,
            "views": int(p.views or 0),
            "engagements": int((p.likes or 0) + (p.comments or 0) + (p.shares or 0)),
            "url": p.url,
        }
        for p in tops
    ]
)
st.dataframe(tp_df, use_container_width=True, height=240)

# -----------------------
# Recommendations
# -----------------------
st.subheader("Next week recommendations")
if not recs:
    st.info("Not enough data to generate recommendations yet.")
else:
    for r in recs[:8]:
        st.markdown(f"**{r.title}**  \n- {r.detail}")

# -----------------------
# One-click exports
# -----------------------
st.subheader("One-click exports")
colA, colB = st.columns(2)

with colA:
    if st.button("Generate premium PDF (with recommendations)"):
        Path("reports").mkdir(exist_ok=True)
        out = f"reports/{client.replace(' ', '_')}_weekly_{week_end_dt2.date()}.pdf"
        generate_premium_weekly_pdf(
            out,
            client,
            week_start_dt,
            week_end_dt2,
            sov,
            tops,
            alerts,
            benchmarks,
            recs,
        )
        with open(out, "rb") as f:
            st.download_button(
                "Download PDF",
                f.read(),
                file_name=f"{client}_weekly_{week_end_dt2.date()}.pdf",
                mime="application/pdf",
            )

with colB:
    if st.button("Export PPTX deck (with recommendations)"):
        deck = build_client_deck_pptx(
            client,
            week_start_dt,
            week_end_dt2,
            sov,
            tops,
            alerts,
            benchmarks,
            recs,
        )
        st.download_button(
            "Download PPTX",
            deck,
            file_name=f"{client}_weekly_{week_end_dt2.date()}.pptx",
            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        )
