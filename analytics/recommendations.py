from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List

import pandas as pd
from sqlmodel import select

from app.db import get_session
from app.models import Client, Post, SponsorTag, Sponsor

@dataclass
class Recommendation:
    title: str
    detail: str
    confidence: float  # 0..1

def _load_posts(start: datetime, end: datetime) -> pd.DataFrame:
    with get_session() as session:
        posts = session.exec(select(Post).where(Post.posted_at >= start, Post.posted_at <= end)).all()
    if not posts:
        return pd.DataFrame()

    df = pd.DataFrame([{
        "client_id": p.client_id,
        "post_row_id": p.id,
        "posted_at": p.posted_at,
        "platform": p.platform,
        "media_type": p.media_type,
        "language": p.language,
        "views": int(p.views or 0),
        "likes": int(p.likes or 0),
        "comments": int(p.comments or 0),
        "shares": int(p.shares or 0),
    } for p in posts])
    df["engagements"] = df["likes"] + df["comments"] + df["shares"]
    return df

def _load_sponsor_tags(post_ids: List[int]) -> pd.DataFrame:
    if not post_ids:
        return pd.DataFrame()
    with get_session() as session:
        tags = session.exec(
            select(SponsorTag, Sponsor)
            .join(Sponsor, Sponsor.id == SponsorTag.sponsor_id)
            .where(SponsorTag.post_id.in_(post_ids))
        ).all()
    if not tags:
        return pd.DataFrame()
    return pd.DataFrame([{"post_row_id": st.post_id, "sponsor": sp.name} for st, sp in tags]).drop_duplicates()

def _add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d["dow"] = pd.to_datetime(d["posted_at"]).dt.day_name()
    d["hour"] = pd.to_datetime(d["posted_at"]).dt.hour

    def bucket(h: int) -> str:
        if 5 <= h <= 10:
            return "Morning (5-10)"
        if 11 <= h <= 15:
            return "Midday (11-15)"
        if 16 <= h <= 20:
            return "Evening (16-20)"
        return "Night (21-4)"
    d["daypart"] = d["hour"].apply(bucket)
    return d

def compute_next_week_recommendations(
    client_name: str,
    week_ending: datetime,
    lookback_weeks: int = 8,
    min_posts_per_bucket: int = 6,
) -> List[Recommendation]:
    with get_session() as session:
        client = session.exec(select(Client).where(Client.name == client_name)).first()
        if not client:
            raise ValueError(f"Client not found: {client_name}")
        client_id = client.id

    end = datetime(week_ending.year, week_ending.month, week_ending.day, 23, 59, 59)
    start = end - timedelta(days=7 * lookback_weeks - 1)

    df = _load_posts(start, end)
    if df.empty:
        return []
    df = df[df["client_id"] == client_id].copy()
    if df.empty:
        return []

    df = _add_time_features(df)
    df["cohort"] = df["platform"].astype(str) + "|" + df["media_type"].astype(str) + "|" + df["language"].astype(str)
    df["eng_per_1k_views"] = df.apply(lambda r: (r["engagements"] * 1000 / r["views"]) if r["views"] > 0 else r["engagements"], axis=1)

    recs: List[Recommendation] = []

    cohort_stats = df.groupby("cohort").agg(
        posts=("post_row_id","nunique"),
        median_views=("views","median"),
        median_eng=("engagements","median"),
        median_e1k=("eng_per_1k_views","median")
    ).reset_index()
    cohort_stats = cohort_stats[cohort_stats["posts"] >= min_posts_per_bucket]
    if not cohort_stats.empty:
        cohort_stats = cohort_stats.sort_values(["median_e1k","median_views"], ascending=False)
        for _, r in cohort_stats.head(3).iterrows():
            plat, fmt, lang = str(r["cohort"]).split("|", 2)
            recs.append(Recommendation(
                title="Best-performing content cohort to repeat",
                detail=f"Repeat {plat.upper()} {fmt} in {lang}: median {int(r['median_views']):,} views and {int(r['median_eng']):,} engagements.",
                confidence=0.75
            ))
    else:
        recs.append(Recommendation(
            title="Build stronger recommendations",
            detail="Not enough posts per cohort yet. Keep posting consistently for 2–3 weeks per platform/format/language to unlock stronger recs.",
            confidence=0.40
        ))

    time_stats = df.groupby(["dow","daypart"]).agg(
        posts=("post_row_id","nunique"),
        median_views=("views","median"),
        median_eng=("engagements","median")
    ).reset_index()
    time_stats = time_stats[time_stats["posts"] >= max(4, min_posts_per_bucket // 2)]
    if not time_stats.empty:
        time_stats["score"] = time_stats["median_eng"] * 0.7 + time_stats["median_views"] * 0.3
        for _, r in time_stats.sort_values("score", ascending=False).head(2).iterrows():
            recs.append(Recommendation(
                title="Best posting window",
                detail=f"Schedule key posts on {r['dow']} {r['daypart']} (median {int(r['median_views']):,} views; {int(r['median_eng']):,} engagements).",
                confidence=0.70
            ))

    tags = _load_sponsor_tags(df["post_row_id"].tolist())
    if not tags.empty:
        joined = tags.merge(df, on="post_row_id", how="left")
        joined["cohort"] = joined["platform"].astype(str) + "|" + joined["media_type"].astype(str) + "|" + joined["language"].astype(str)
        sponsor_stats = joined.groupby(["sponsor","cohort"]).agg(
            posts=("post_row_id","nunique"),
            median_views=("views","median"),
            median_eng=("engagements","median")
        ).reset_index()
        sponsor_stats = sponsor_stats[sponsor_stats["posts"] >= 3]
        if not sponsor_stats.empty:
            sponsor_totals = sponsor_stats.groupby("sponsor")["posts"].sum().sort_values(ascending=False)
            for sponsor in sponsor_totals.head(2).index.tolist():
                s = sponsor_stats[sponsor_stats["sponsor"] == sponsor].copy()
                s["score"] = s["median_eng"] * 0.7 + s["median_views"] * 0.3
                best = s.sort_values("score", ascending=False).head(1)
                if len(best):
                    b = best.iloc[0]
                    plat, fmt, lang = str(b["cohort"]).split("|", 2)
                    recs.append(Recommendation(
                        title="Sponsor-specific creative pattern",
                        detail=f"For {sponsor}, your best pattern is {plat.upper()} {fmt} in {lang} (median {int(b['median_views']):,} views; {int(b['median_eng']):,} engagements).",
                        confidence=0.65
                    ))

    recs.append(Recommendation(
        title="Operational next step",
        detail="Do a 10-minute weekly QA review of sponsor tags for the top 20 posts. Accuracy improves and benchmarks get stronger.",
        confidence=0.80
    ))
    return recs[:8]
