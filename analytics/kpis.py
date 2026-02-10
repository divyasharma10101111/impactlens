from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

import pandas as pd
from sqlmodel import select

from app.db import get_session
from app.models import Client, Post, Sponsor, SponsorTag

@dataclass
class SOVRow:
    sponsor: str
    sponsored_posts: int
    total_views: int
    total_engagements: int

def week_range(week_ending: datetime) -> tuple[datetime, datetime]:
    end = datetime(week_ending.year, week_ending.month, week_ending.day, 23, 59, 59)
    start = end - timedelta(days=6)
    return start, end

def compute_sov(client_name: str, start: datetime, end: datetime) -> List[SOVRow]:
    with get_session() as session:
        client = session.exec(select(Client).where(Client.name == client_name)).first()
        if not client:
            raise ValueError(f"Client not found: {client_name}")

        posts = session.exec(
            select(Post).where(
                Post.client_id == client.id,
                Post.posted_at >= start,
                Post.posted_at <= end,
            )
        ).all()
        if not posts:
            return []

        post_df = pd.DataFrame([{
            "post_row_id": p.id,
            "views": p.views,
            "likes": p.likes,
            "comments": p.comments,
            "shares": p.shares,
        } for p in posts])

        tags = session.exec(
            select(SponsorTag, Sponsor)
            .join(Sponsor, Sponsor.id == SponsorTag.sponsor_id)
            .where(SponsorTag.post_id.in_([p.id for p in posts]))
        ).all()

        if not tags:
            return []

        tag_df = pd.DataFrame([{
            "post_row_id": st.post_id,
            "sponsor": sp.name,
        } for st, sp in tags]).drop_duplicates()

        df = tag_df.merge(post_df, on="post_row_id", how="left").fillna(0)
        df["engagements"] = df["likes"] + df["comments"] + df["shares"]

        out = []
        for sponsor, g in df.groupby("sponsor"):
            out.append(SOVRow(
                sponsor=sponsor,
                sponsored_posts=int(g["post_row_id"].nunique()),
                total_views=int(g["views"].sum()),
                total_engagements=int(g["engagements"].sum()),
            ))
        out.sort(key=lambda r: (r.total_views, r.total_engagements), reverse=True)
        return out

def top_posts(client_name: str, start: datetime, end: datetime, limit: int = 10):
    with get_session() as session:
        client = session.exec(select(Client).where(Client.name == client_name)).first()
        if not client:
            return []

        posts = session.exec(
            select(Post).where(
                Post.client_id == client.id,
                Post.posted_at >= start,
                Post.posted_at <= end,
            )
        ).all()
        if not posts:
            return []

        # Only sponsored (has any SponsorTag)
        tagged_ids = set(session.exec(select(SponsorTag.post_id)).all())
        sp = [p for p in posts if p.id in tagged_ids]
        sp.sort(key=lambda p: (p.views, p.likes + p.comments + p.shares), reverse=True)
        return sp[:limit]
