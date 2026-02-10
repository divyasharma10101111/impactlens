from sqlmodel import select
from app.db import get_session
from app.models import Post, Sponsor, SponsorTag
from processing.sponsor_dict import SPONSOR_PATTERNS
from processing.text_tagger import tag_sponsors_text

def ensure_sponsors_exist(session):
    existing = {s.name for s in session.exec(select(Sponsor)).all()}
    for name in SPONSOR_PATTERNS.keys():
        if name not in existing:
            session.add(Sponsor(name=name))
    session.commit()

def tag_unprocessed_posts_text(client_name: str | None = None, limit: int = 500):
    with get_session() as session:
        ensure_sponsors_exist(session)

        q = select(Post).where(Post.text_tagged == False)  # noqa: E712
        if client_name:
            from app.models import Client
            client = session.exec(select(Client).where(Client.name == client_name)).first()
            if client:
                q = q.where(Post.client_id == client.id)

        posts = session.exec(q.limit(limit)).all()
        if not posts:
            return 0

        sponsors = {s.name: s for s in session.exec(select(Sponsor)).all()}

        created = 0
        for p in posts:
            hits = tag_sponsors_text(p.caption, SPONSOR_PATTERNS)
            for sponsor_name, conf, _reason in hits:
                st = SponsorTag(
                    post_id=p.id,
                    sponsor_id=sponsors[sponsor_name].id,
                    source="text",
                    confidence=conf,
                )
                session.add(st)
                created += 1
            p.text_tagged = True
            session.add(p)

        session.commit()
        return created
