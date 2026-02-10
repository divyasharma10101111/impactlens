from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List

import pandas as pd
from sqlmodel import select

from app.db import get_session
from app.models import Client, Post, SponsorTag, Sponsor

@dataclass
class Alert:
    sponsor: str
    metric: str
    current: int
    baseline: int
    delta_pct: float
    message: str

def _week_bounds(week_ending: datetime) -> tuple[datetime, datetime]:
    end = datetime(week_ending.year, week_ending.month, week_ending.day, 23, 59, 59)
    start = end - timedelta(days=6)
    return start, end

def _load_tagged_posts(client_id: int, start: datetime, end: datetime) -> pd.DataFrame:
    with get_session() as session:
        posts = session.exec(
            select(Post).where(
                Post.client_id == client_id,
                Post.posted_at >= start,
                Post.posted_at <= end,
            )
        ).all()
        if not posts:
            return pd.DataFrame()

        post_df = pd.DataFrame([{
            "post_row_id": p.id,
            "views": int(p.views or 0),
            "likes": int(p.likes or 0),
            "comments": int(p.comments or 0),
            "shares": int(p.shares or 0),
        } for p in posts])
        post_df["engagements"] = post_df["likes"] + post_df["comments"] + post_df["shares"]

        tags = session.exec(
            select(SponsorTag, Sponsor)
            .join(Sponsor, Sponsor.id == SponsorTag.sponsor_id)
            .where(SponsorTag.post_id.in_([p.id for p in posts]))
        ).all()

        if not tags:
            return pd.DataFrame()

        tag_df = pd.DataFrame([{
            "post_row_id": st.post_id,
            "sponsor": sp.name,
        } for st, sp in tags]).drop_duplicates()

    df = tag_df.merge(post_df, on="post_row_id", how="left").fillna(0)
    return df

def _sponsor_totals(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    return df.groupby("sponsor").agg(
        views=("views","sum"),
        engagements=("engagements","sum"),
        posts=("post_row_id","nunique")
    ).reset_index()

def compute_under_delivery_alerts(
    client_name: str,
    week_ending: datetime,
    lookback_weeks: int = 4,
    threshold_pct: float = 0.20,
) -> List[Alert]:
    """Alert when sponsor is down >= threshold_pct vs baseline average of previous weeks."""
    with get_session() as session:
        client = session.exec(select(Client).where(Client.name == client_name)).first()
        if not client:
            raise ValueError(f"Client not found: {client_name}")
        client_id = client.id

    cur_start, cur_end = _week_bounds(week_ending)
    cur_df = _load_tagged_posts(client_id, cur_start, cur_end)
    cur = _sponsor_totals(cur_df)

    baseline_frames = []
    for i in range(1, lookback_weeks + 1):
        ws = cur_start - timedelta(days=7*i)
        we = cur_end - timedelta(days=7*i)
        wdf = _load_tagged_posts(client_id, ws, we)
        if not wdf.empty:
            baseline_frames.append(_sponsor_totals(wdf))

    if not baseline_frames or cur.empty:
        return []

    base = pd.concat(baseline_frames, ignore_index=True)
    base = base.groupby("sponsor").agg(
        views=("views","mean"),
        engagements=("engagements","mean"),
        posts=("posts","mean")
    ).reset_index()

    joined = cur.merge(base, on="sponsor", how="left", suffixes=("_cur","_base")).fillna(0)

    alerts: List[Alert] = []
    for _, r in joined.iterrows():
        sponsor = str(r["sponsor"])
        for metric in ["views", "engagements"]:
            cur_v = int(r.get(f"{metric}_cur", 0) or 0)
            base_v = int(r.get(f"{metric}_base", 0) or 0)
            if base_v <= 0:
                continue
            delta_pct = (cur_v - base_v) / base_v
            if delta_pct <= -threshold_pct:
                msg = (
                    f"{sponsor}: {metric} under-delivered by {abs(delta_pct)*100:.0f}% "
                    f"(this week {cur_v:,} vs baseline {base_v:,})."
                )
                alerts.append(Alert(
                    sponsor=sponsor,
                    metric=metric,
                    current=cur_v,
                    baseline=base_v,
                    delta_pct=float(delta_pct),
                    message=msg
                ))

    alerts.sort(key=lambda a: a.delta_pct)  # biggest drops first
    return alerts
