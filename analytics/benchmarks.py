from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List

import pandas as pd
from sqlmodel import select

from app.db import get_session
from app.models import Client, Post

@dataclass
class BenchmarkRow:
    cohort_key: str
    metric: str
    client_value: int
    cohort_median: int
    percentile: float

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

def _percentile_rank(values: pd.Series, x: float) -> float:
    if values.empty:
        return 0.0
    return float((values <= x).mean())

def compute_content_benchmarks(
    client_name: str,
    week_ending: datetime,
    lookback_weeks: int = 8,
    min_posts_per_cohort: int = 10,
) -> List[BenchmarkRow]:
    """Cohort benchmarks where cohort = platform|format|language."""
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

    df["cohort"] = df["platform"].astype(str) + "|" + df["media_type"].astype(str) + "|" + df["language"].astype(str)

    client_df = df[df["client_id"] == client_id].copy()
    if client_df.empty:
        return []

    client_stats = client_df.groupby("cohort").agg(
        posts=("post_row_id","nunique"),
        views=("views","median"),
        engagements=("engagements","median")
    ).reset_index()

    out: List[BenchmarkRow] = []
    for _, r in client_stats.iterrows():
        if int(r["posts"]) < min_posts_per_cohort:
            continue
        cohort = str(r["cohort"])
        cohort_posts = df[df["cohort"] == cohort]
        if cohort_posts.empty:
            continue

        views_pct = _percentile_rank(cohort_posts["views"], float(r["views"]))
        out.append(BenchmarkRow(
            cohort_key=cohort,
            metric="views",
            client_value=int(r["views"]),
            cohort_median=int(cohort_posts["views"].median()),
            percentile=views_pct
        ))

        eng_pct = _percentile_rank(cohort_posts["engagements"], float(r["engagements"]))
        out.append(BenchmarkRow(
            cohort_key=cohort,
            metric="engagements",
            client_value=int(r["engagements"]),
            cohort_median=int(cohort_posts["engagements"].median()),
            percentile=eng_pct
        ))

    out.sort(key=lambda b: abs(b.percentile - 0.5), reverse=True)
    return out[:24]
