from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship

class Client(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)

class Account(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    client_id: int = Field(foreign_key="client.id", index=True)
    name: str = Field(index=True)
    platform: str = Field(index=True)  # youtube/instagram/x etc

class Post(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    client_id: int = Field(foreign_key="client.id", index=True)
    account_id: int = Field(foreign_key="account.id", index=True)

    platform: str = Field(index=True)
    post_id: str = Field(index=True)
    url: str

    posted_at: datetime = Field(index=True)
    caption: str = ""
    media_type: str = "post"     # post/reel/short/video
    language: str = "unknown"

    # latest metrics snapshot
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0

    # processing state
    text_tagged: bool = Field(default=False, index=True)
    vision_tagged: bool = Field(default=False, index=True)

class Sponsor(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)

class SponsorTag(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    post_id: int = Field(foreign_key="post.id", index=True)
    sponsor_id: int = Field(foreign_key="sponsor.id", index=True)

    source: str = Field(index=True)  # text / vision / manual
    confidence: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)

class QAOverride(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    post_id: int = Field(foreign_key="post.id", index=True)
    sponsor_id: int = Field(foreign_key="sponsor.id", index=True)
    action: str = Field(index=True)  # add/remove
    note: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
