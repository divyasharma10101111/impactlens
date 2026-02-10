from sqlmodel import SQLModel, create_engine, Session
from app.settings import DATABASE_URL

engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    return Session(engine)
