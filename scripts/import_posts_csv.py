import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


import argparse
import pandas as pd
from dateutil import parser as dtparser
from sqlmodel import select

from app.db import get_session, create_db_and_tables
from app.models import Client, Account, Post

def get_or_create_client(session, name: str) -> Client:
    c = session.exec(select(Client).where(Client.name == name)).first()
    if not c:
        c = Client(name=name)
        session.add(c)
        session.commit()
        session.refresh(c)
    return c

def get_or_create_account(session, client_id: int, account_name: str, platform: str) -> Account:
    a = session.exec(select(Account).where(
        Account.client_id == client_id,
        Account.name == account_name,
        Account.platform == platform
    )).first()
    if not a:
        a = Account(client_id=client_id, name=account_name, platform=platform)
        session.add(a)
        session.commit()
        session.refresh(a)
    return a

def main(csv_path: str):
    create_db_and_tables()
    df = pd.read_csv(csv_path)
    required = ["client","account","platform","post_id","url","posted_at","caption","media_type","language","views","likes","comments","shares"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise SystemExit(f"Missing required columns: {missing}")

    with get_session() as session:
        for _, r in df.iterrows():
            client = get_or_create_client(session, str(r["client"]))
            acct = get_or_create_account(session, client.id, str(r["account"]), str(r["platform"]))

            posted_at = dtparser.parse(str(r["posted_at"]))
            # upsert (by client+platform+post_id)
            existing = session.exec(select(Post).where(
                Post.client_id == client.id,
                Post.platform == str(r["platform"]),
                Post.post_id == str(r["post_id"]),
            )).first()

            payload = dict(
                client_id=client.id,
                account_id=acct.id,
                platform=str(r["platform"]),
                post_id=str(r["post_id"]),
                url=str(r["url"]),
                posted_at=posted_at,
                caption=str(r.get("caption","") or ""),
                media_type=str(r.get("media_type","post") or "post"),
                language=str(r.get("language","unknown") or "unknown"),
                views=int(r.get("views",0) or 0),
                likes=int(r.get("likes",0) or 0),
                comments=int(r.get("comments",0) or 0),
                shares=int(r.get("shares",0) or 0),
            )
            if existing:
                for k,v in payload.items():
                    setattr(existing, k, v)
                session.add(existing)
            else:
                session.add(Post(**payload))
        session.commit()
    print("Imported posts from CSV.")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_path")
    args = ap.parse_args()
    main(args.csv_path)
